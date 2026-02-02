# -*- coding: utf-8 -*-
"""
JKR/JPK compression for Monster Hunter Frontier stage files.

Ported from ReFrontier (C#) by Houmgaor.

Supports 4 compression types:
- Type 0 (RW): Raw, no compression
- Type 2 (HFIRW): Huffman encoding only
- Type 3 (LZ): LZ77 compression
- Type 4 (HFI): Huffman + LZ77 compression (most common)
"""

import struct
from dataclasses import dataclass
from io import BytesIO
from typing import List, Optional, Tuple

from .jkr_decompress import CompressionType, JKR_MAGIC


@dataclass
class JKRHeaderBuilder:
    """Builder for JKR file header."""

    version: int = 0x108
    compression_type: int = CompressionType.HFI
    data_offset: int = 16
    decompressed_size: int = 0

    def to_bytes(self) -> bytes:
        """
        Serialize JKR header to bytes.

        :return: 16 bytes of header data.
        """
        return struct.pack(
            "<IHHII",
            JKR_MAGIC,
            self.version,
            self.compression_type,
            self.data_offset,
            self.decompressed_size,
        )


class BitWriter:
    """Helper class for writing individual bits to a byte stream."""

    def __init__(self):
        self._buffer = bytearray()
        self._current_byte = 0
        self._bit_position = 7  # Start from MSB

    def write_bit(self, bit: bool) -> None:
        """Write a single bit."""
        if bit:
            self._current_byte |= 1 << self._bit_position

        self._bit_position -= 1
        if self._bit_position < 0:
            self._buffer.append(self._current_byte)
            self._current_byte = 0
            self._bit_position = 7

    def write_bits(self, value: int, num_bits: int) -> None:
        """Write multiple bits (MSB first)."""
        for i in range(num_bits - 1, -1, -1):
            self.write_bit(bool((value >> i) & 1))

    def write_byte(self, value: int) -> None:
        """Write a full byte."""
        self.write_bits(value, 8)

    def flush(self) -> bytes:
        """Flush remaining bits and return the buffer."""
        if self._bit_position < 7:
            self._buffer.append(self._current_byte)
        return bytes(self._buffer)

    def get_bytes(self) -> bytes:
        """Get current buffer without flushing."""
        result = bytearray(self._buffer)
        if self._bit_position < 7:
            result.append(self._current_byte)
        return bytes(result)


class LZEncoder:
    """
    LZ77 compression encoder for JPK files.

    Ported from ReFrontier JPKEncodeLz.cs

    Back-reference encoding cases (matching decoder):
    - Case 0: length 3-6, offset <= 255 (1 byte)
    - Case 1: length 2-9, offset <= 8191 (2 bytes)
    - Case 2: length 10-25 (4-bit length encoding)
    - Case 3: length >= 26 (1-byte length)
    - Case 4: Raw byte run (escape sequence)
    """

    # Sliding window size
    WINDOW_SIZE = 8192  # 8KB window for back-references
    MIN_MATCH = 2
    MAX_MATCH_SHORT = 9  # Case 1 max
    MAX_MATCH_MED = 25  # Case 2 max
    MAX_MATCH_LONG = 255 + 0x1A  # Case 3 max

    def __init__(self):
        self._writer = BitWriter()

    def _find_match(
        self,
        data: bytes,
        pos: int,
    ) -> Tuple[int, int]:
        """
        Find the longest match in the sliding window.

        :param data: Full input data.
        :param pos: Current position in data.
        :return: (offset, length) tuple. offset is 0 if no match found.
        """
        if pos < 1:
            return 0, 0

        best_offset = 0
        best_length = 0
        max_offset = min(pos, self.WINDOW_SIZE)
        remaining = len(data) - pos
        max_length = min(remaining, self.MAX_MATCH_LONG)

        # Search backwards through the window
        for offset in range(1, max_offset + 1):
            match_pos = pos - offset
            length = 0

            # Count matching bytes
            while length < max_length and pos + length < len(data):
                if data[match_pos + (length % offset)] == data[pos + length]:
                    length += 1
                else:
                    break

            # Keep track of best match (prefer longer matches, then shorter offsets)
            if length >= self.MIN_MATCH and length > best_length:
                best_offset = offset
                best_length = length

        return best_offset, best_length

    def _encode_literal(self, byte_value: int) -> None:
        """
        Encode a literal byte (no back-reference found).

        Format: 0-bit followed by the byte
        """
        self._writer.write_bit(False)
        self._writer.write_byte(byte_value)

    def _encode_backref(self, offset: int, length: int) -> None:
        """
        Encode a back-reference.

        Chooses the most efficient encoding based on offset and length.
        """
        # Convert offset to 0-based for encoding (decoder uses offset-1)
        offset_enc = offset - 1

        # Case 0: length 3-6, offset <= 255
        if 3 <= length <= 6 and offset_enc <= 255:
            self._writer.write_bit(True)  # 1
            self._writer.write_bit(False)  # 0
            # 2-bit length encoding: 00=3, 01=4, 10=5, 11=6
            length_enc = length - 3
            self._writer.write_bit(bool(length_enc & 2))
            self._writer.write_bit(bool(length_enc & 1))
            self._writer.write_byte(offset_enc)
            return

        # Case 1: length 2-9, offset <= 8191
        if 2 <= length <= 9 and offset_enc <= 8191:
            self._writer.write_bit(True)  # 1
            self._writer.write_bit(True)  # 1
            # 2-byte encoding: hi byte = (length-2)<<5 | (offset>>8), lo byte = offset&0xFF
            length_enc = length - 2
            hi = (length_enc << 5) | ((offset_enc >> 8) & 0x1F)
            lo = offset_enc & 0xFF
            self._writer.write_byte(hi)
            self._writer.write_byte(lo)
            return

        # Case 2: length 10-25
        if 10 <= length <= 25 and offset_enc <= 8191:
            self._writer.write_bit(True)  # 1
            self._writer.write_bit(True)  # 1
            # hi = (0<<5) | (offset>>8), meaning length field is 0
            hi = (offset_enc >> 8) & 0x1F
            lo = offset_enc & 0xFF
            self._writer.write_byte(hi)
            self._writer.write_byte(lo)
            # Then 0-bit followed by 4-bit length
            self._writer.write_bit(False)
            length_enc = length - 10  # 0-15 range
            self._writer.write_bits(length_enc, 4)
            return

        # Case 3: length >= 26 (or fallback for case 2 overflow)
        if length >= 26 and offset_enc <= 8191:
            self._writer.write_bit(True)  # 1
            self._writer.write_bit(True)  # 1
            # hi = (0<<5) | (offset>>8), meaning length field is 0
            hi = (offset_enc >> 8) & 0x1F
            lo = offset_enc & 0xFF
            self._writer.write_byte(hi)
            self._writer.write_byte(lo)
            # Then 1-bit followed by length byte
            self._writer.write_bit(True)
            length_enc = min(length - 0x1A, 255)  # Cap at 255
            self._writer.write_byte(length_enc)
            return

        # Fallback to case 1 with truncated length
        if offset_enc <= 8191:
            length = min(length, 9)
            self._writer.write_bit(True)
            self._writer.write_bit(True)
            length_enc = length - 2
            hi = (length_enc << 5) | ((offset_enc >> 8) & 0x1F)
            lo = offset_enc & 0xFF
            self._writer.write_byte(hi)
            self._writer.write_byte(lo)
            return

        # Last resort: emit as literals
        # This shouldn't happen with WINDOW_SIZE = 8192
        raise ValueError(f"Cannot encode back-reference: offset={offset}, length={length}")

    def encode(self, data: bytes) -> bytes:
        """
        Compress data using LZ77.

        :param data: Uncompressed data.
        :return: LZ77 compressed data.
        """
        self._writer = BitWriter()
        pos = 0

        while pos < len(data):
            offset, length = self._find_match(data, pos)

            if length >= self.MIN_MATCH:
                self._encode_backref(offset, length)
                pos += length
            else:
                self._encode_literal(data[pos])
                pos += 1

        return self._writer.flush()


class HuffmanEncoder:
    """
    Huffman encoding for JPK files.

    Builds a Huffman tree from byte frequencies and encodes the data.
    The tree is stored in a format compatible with the decoder.
    """

    def __init__(self):
        self._codes: dict = {}
        self._code_lengths: dict = {}

    def _build_tree(self, data: bytes) -> List[int]:
        """
        Build Huffman tree from data and return the table.

        The table format matches the decoder's expectations:
        - Table length at the start
        - Node entries: left child, right child for internal nodes
        - Leaf nodes contain byte values (< 0x100)

        :param data: Input data to analyze.
        :return: Huffman table as list of int16 values.
        """
        # Count frequencies
        freq = [0] * 256
        for byte in data:
            freq[byte] += 1

        # Handle empty or single-byte data
        non_zero_count = sum(1 for f in freq if f > 0)
        if non_zero_count == 0:
            # Empty data - create minimal tree
            self._codes = {0: (0, 1)}  # 0 -> bit 0, length 1
            return [0x100, 0, 0]  # Minimal tree pointing to byte 0

        if non_zero_count == 1:
            # Single byte value - create minimal tree
            byte_val = next(i for i, f in enumerate(freq) if f > 0)
            self._codes = {byte_val: (0, 1)}
            return [0x100, byte_val, byte_val]

        # Build priority queue (min-heap simulation with sorted list)
        # Each entry is (frequency, node_id, left, right)
        # Leaf nodes have left=right=byte_value
        nodes = []
        node_id = 0
        for byte, count in enumerate(freq):
            if count > 0:
                nodes.append((count, node_id, byte, byte))  # Leaf node
                node_id += 1

        nodes.sort()

        # Build tree by combining lowest frequency nodes
        tree_nodes = []  # List of (left, right) for internal nodes
        leaf_to_code = {}  # byte -> node position in tree

        while len(nodes) > 1:
            # Pop two smallest
            freq1, id1, left1, right1 = nodes.pop(0)
            freq2, id2, left2, right2 = nodes.pop(0)

            # Create internal node
            internal_id = 0x100 + len(tree_nodes)
            tree_nodes.append((id1 if id1 >= 0x100 else left1, id2 if id2 >= 0x100 else left2))

            # Insert combined node (keep sorted)
            combined = (freq1 + freq2, internal_id, -1, -1)
            inserted = False
            for i, n in enumerate(nodes):
                if combined[0] <= n[0]:
                    nodes.insert(i, combined)
                    inserted = True
                    break
            if not inserted:
                nodes.append(combined)

            # Track leaf assignments
            if id1 < 0x100:
                leaf_to_code[left1] = (internal_id, 0)
            if id2 < 0x100:
                leaf_to_code[left2] = (internal_id, 1)

        # Build the table for decoder
        # Format: table_len (int16), then pairs of int16 for each internal node
        table = []

        # Root node index
        if nodes:
            root_id = nodes[0][1]
            table.append(root_id)  # Table length / root pointer
        else:
            table.append(0x100)

        # Add node data (format expected by decoder)
        # Decoder navigates: data[node*2 - 0x200 + bit]
        # We need to build table so decoder can traverse
        for i, (left, right) in enumerate(tree_nodes):
            table.append(left if left >= 0x100 else left)  # Left child (0 bit)
            table.append(right if right >= 0x100 else right)  # Right child (1 bit)

        # Generate bit codes by traversing tree
        self._generate_codes(tree_nodes, len(tree_nodes) - 1 + 0x100 if tree_nodes else 0)

        return table

    def _generate_codes(self, tree_nodes: List[Tuple[int, int]], root: int) -> None:
        """
        Generate Huffman codes by traversing the tree.

        :param tree_nodes: List of internal nodes (left, right).
        :param root: Root node index.
        """
        self._codes = {}

        if not tree_nodes:
            return

        def traverse(node_id: int, code: int, length: int) -> None:
            if node_id < 0x100:
                # Leaf node - this is a byte value
                self._codes[node_id] = (code, length)
                return

            # Internal node
            idx = node_id - 0x100
            if 0 <= idx < len(tree_nodes):
                left, right = tree_nodes[idx]
                traverse(left, code << 1, length + 1)
                traverse(right, (code << 1) | 1, length + 1)

        traverse(root, 0, 0)

        # Ensure we have at least one code
        if not self._codes:
            self._codes = {0: (0, 1)}

    def encode(self, data: bytes) -> Tuple[bytes, bytes]:
        """
        Encode data using Huffman coding.

        :param data: Input data.
        :return: (table_bytes, encoded_data_bytes) tuple.
        """
        table = self._build_tree(data)

        # Serialize table
        table_bytes = b"".join(struct.pack("<h", v) for v in table)

        # Encode data
        writer = BitWriter()
        for byte in data:
            if byte in self._codes:
                code, length = self._codes[byte]
                writer.write_bits(code, length)
            else:
                # Fallback for bytes not in tree (shouldn't happen)
                writer.write_bits(byte, 8)

        encoded = writer.flush()

        return table_bytes, encoded


class HFIEncoder:
    """
    Combined Huffman + LZ77 encoder (Type 4).

    Applies LZ77 first, then Huffman encodes the result.
    """

    def __init__(self):
        self._lz_encoder = LZEncoder()
        self._huffman_encoder = HuffmanEncoder()

    def encode(self, data: bytes) -> bytes:
        """
        Encode data using LZ77 followed by Huffman coding.

        :param data: Uncompressed data.
        :return: Compressed data with Huffman table prefix.
        """
        # LZ77 pass
        lz_compressed = self._lz_encoder.encode(data)

        # Huffman pass on LZ output
        table_bytes, huffman_data = self._huffman_encoder.encode(lz_compressed)

        # Combine: table_len (int16) + table + huffman data
        table_len = len(table_bytes) // 2  # Number of int16 entries
        return struct.pack("<h", table_len) + table_bytes[2:] + huffman_data


class HFIRWEncoder:
    """
    Huffman-only encoder (Type 2, no LZ77).
    """

    def __init__(self):
        self._huffman_encoder = HuffmanEncoder()

    def encode(self, data: bytes) -> bytes:
        """
        Encode data using Huffman coding only.

        :param data: Uncompressed data.
        :return: Compressed data with Huffman table prefix.
        """
        table_bytes, huffman_data = self._huffman_encoder.encode(data)

        # Combine: table_len (int16) + table + huffman data
        table_len = len(table_bytes) // 2
        return struct.pack("<h", table_len) + table_bytes[2:] + huffman_data


def compress_jkr(
    data: bytes,
    compression_type: int = CompressionType.HFI,
) -> bytes:
    """
    Compress data to JKR/JPK format.

    :param data: Uncompressed data.
    :param compression_type: Compression type (RW, HFIRW, LZ, or HFI).
    :return: Complete JKR file data including header.
    """
    header = JKRHeaderBuilder(
        compression_type=compression_type,
        decompressed_size=len(data),
    )

    if compression_type == CompressionType.RW or compression_type == CompressionType.NONE:
        # Raw - no compression
        compressed = data
    elif compression_type == CompressionType.HFIRW:
        # Huffman only
        encoder = HFIRWEncoder()
        compressed = encoder.encode(data)
    elif compression_type == CompressionType.LZ:
        # LZ77 only
        encoder = LZEncoder()
        compressed = encoder.encode(data)
    elif compression_type == CompressionType.HFI:
        # Huffman + LZ77
        encoder = HFIEncoder()
        compressed = encoder.encode(data)
    else:
        raise ValueError(f"Unknown compression type: {compression_type}")

    return header.to_bytes() + compressed


def compress_jkr_hfi(data: bytes) -> bytes:
    """
    Compress data using HFI (Huffman + LZ77) compression.

    This is the most commonly used compression for stage files.

    :param data: Uncompressed data.
    :return: Complete JKR file data.
    """
    return compress_jkr(data, CompressionType.HFI)


def compress_jkr_raw(data: bytes) -> bytes:
    """
    Wrap data in JKR container without compression.

    :param data: Raw data.
    :return: JKR file data with RW compression type.
    """
    return compress_jkr(data, CompressionType.RW)
