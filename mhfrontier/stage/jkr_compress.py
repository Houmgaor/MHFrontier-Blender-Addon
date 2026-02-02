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


class LZInterleavedWriter:
    """
    Writer for LZ77 interleaved format.

    The JPK LZ format interleaves flag bytes with data bytes:
    - Flag byte contains 8 control bits
    - Data bytes follow the flag byte in the order they're consumed
    - When all 8 bits are consumed, next flag byte is read

    The key insight: data bytes are associated with the flag byte that's
    active when they're read. When bits span flag boundaries, data bytes
    written BEFORE the boundary go with the old flag, and data bytes
    written AFTER go with the new flag.

    This matches the decoder's _jpk_bit_lz behavior.
    """

    def __init__(self):
        self._output = bytearray()
        self._flag_bits = []  # Bits for current flag (max 8)
        self._flag_data = []  # Data bytes for current flag

    def _emit_flag(self) -> None:
        """Emit current flag byte and its data bytes."""
        if not self._flag_bits:
            return

        # Pad to 8 bits
        while len(self._flag_bits) < 8:
            self._flag_bits.append(False)

        # Build flag byte (MSB first)
        flag = 0
        for i, bit in enumerate(self._flag_bits):
            if bit:
                flag |= 1 << (7 - i)

        self._output.append(flag)
        self._output.extend(self._flag_data)
        self._flag_bits = []
        self._flag_data = []

    def write_bit(self, bit: bool) -> None:
        """
        Write a control bit.

        If the current flag is full (8 bits), emit it BEFORE adding
        the new bit. This ensures data bytes are correctly associated
        with the flag that's active when they're read.
        """
        if len(self._flag_bits) >= 8:
            self._emit_flag()
        self._flag_bits.append(bit)

    def write_data_byte(self, value: int) -> None:
        """Write a data byte for the current flag."""
        self._flag_data.append(value & 0xFF)

    def end_operation(self) -> None:
        """Mark end of a complete operation. No-op in new design."""
        # No action needed - flags are emitted automatically when full
        pass

    def finish(self) -> bytes:
        """Finish and return the encoded data."""
        self._emit_flag()
        return bytes(self._output)


class LZEncoder:
    """
    LZ77 compression encoder for JPK files.

    Ported from ReFrontier JPKEncodeLz.cs

    Back-reference encoding cases (matching decoder):
    - Case 0: length 3-6, offset <= 255 (1 byte offset)
    - Case 1: length 2-9, offset <= 8191 (2 bytes: hi/lo)
    - Case 2: length 10-25 (4-bit length after case 1 header)
    - Case 3: length >= 26 (1-byte length after case 1 header)
    - Case 4: Raw byte run (escape sequence for very long runs)
    """

    # Sliding window size
    WINDOW_SIZE = 8192  # 8KB window for back-references
    # Minimum match length is 3 because:
    # - Case 0: 3-6 bytes
    # - Case 1: 3-9 bytes (length=2 would encode as 0, triggering Case 2/3)
    # - Case 2: 10-25 bytes
    # - Case 3: 26+ bytes
    MIN_MATCH = 3
    MAX_MATCH_SHORT = 9  # Case 1 max
    MAX_MATCH_MED = 25  # Case 2 max
    MAX_MATCH_LONG = 255 + 0x1A  # Case 3 max

    def __init__(self):
        self._writer = None

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

        Format: 0-bit followed by the byte as data
        """
        self._writer.write_bit(False)
        self._writer.write_data_byte(byte_value)
        self._writer.end_operation()

    def _encode_backref(self, offset: int, length: int) -> None:
        """
        Encode a back-reference.

        Chooses the most efficient encoding based on offset and length.
        The offset stored is offset-1 (0-based).
        """
        # Convert offset to 0-based for encoding (decoder uses offset directly then subtracts 1 more)
        offset_enc = offset - 1

        # Case 0: length 3-6, offset <= 255
        if 3 <= length <= 6 and offset_enc <= 255:
            self._writer.write_bit(True)   # 1
            self._writer.write_bit(False)  # 0
            # 2-bit length encoding: 00=3, 01=4, 10=5, 11=6
            length_enc = length - 3
            self._writer.write_bit(bool(length_enc & 2))
            self._writer.write_bit(bool(length_enc & 1))
            self._writer.write_data_byte(offset_enc)
            self._writer.end_operation()
            return

        # Case 1: length 3-9, offset <= 8191
        # Note: length=2 would encode as length_field=0, which triggers Case 2/3 in decoder
        # So Case 1 only supports lengths 3-9 (length_field 1-7)
        if 3 <= length <= 9 and offset_enc <= 8191:
            self._writer.write_bit(True)  # 1
            self._writer.write_bit(True)  # 1
            # 2-byte encoding: hi byte = (length-2)<<5 | (offset>>8), lo byte = offset&0xFF
            length_enc = length - 2
            hi = (length_enc << 5) | ((offset_enc >> 8) & 0x1F)
            lo = offset_enc & 0xFF
            self._writer.write_data_byte(hi)
            self._writer.write_data_byte(lo)
            self._writer.end_operation()
            return

        # Case 2: length 10-25, offset <= 8191
        # Format: bits 1,1 + hi,lo (with length_field=0) + bit 0 + 4 bits for length
        # Length = (4-bit value) + 10, so 4-bit value = length - 10
        if 10 <= length <= 25 and offset_enc <= 8191:
            self._writer.write_bit(True)   # 1 - backref
            self._writer.write_bit(True)   # 1 - not case 0
            # hi has length_field=0 to trigger Case 2/3 branch
            hi = (offset_enc >> 8) & 0x1F
            lo = offset_enc & 0xFF
            self._writer.write_data_byte(hi)
            self._writer.write_data_byte(lo)
            self._writer.write_bit(False)  # 0 - case 2 (not case 3)
            # Write 4 bits for length (MSB first)
            length_enc = length - 10  # 0-15
            self._writer.write_bit(bool(length_enc & 8))
            self._writer.write_bit(bool(length_enc & 4))
            self._writer.write_bit(bool(length_enc & 2))
            self._writer.write_bit(bool(length_enc & 1))
            self._writer.end_operation()
            return

        # Case 3: length 26-280, offset <= 8191
        # Format: bits 1,1 + hi,lo (with length_field=0) + bit 1 + length byte
        # Note: length_enc = 0xFF (255) triggers literal run mode in decoder, so cap at 254
        # This gives max length of 0x1A + 254 = 280
        if length >= 26 and offset_enc <= 8191:
            # Cap length to avoid 0xFF which triggers literal run
            actual_length = min(length, 0x1A + 254)  # Max 280

            self._writer.write_bit(True)  # 1
            self._writer.write_bit(True)  # 1
            # hi = (0<<5) | (offset>>8), meaning length field is 0
            hi = (offset_enc >> 8) & 0x1F
            lo = offset_enc & 0xFF
            self._writer.write_data_byte(hi)
            self._writer.write_data_byte(lo)
            # Then 1-bit followed by length byte
            self._writer.write_bit(True)
            length_enc = actual_length - 0x1A
            self._writer.write_data_byte(length_enc)
            self._writer.end_operation()
            return

        # Fallback to case 1 with truncated length
        if offset_enc <= 8191:
            length = min(length, 9)
            self._writer.write_bit(True)
            self._writer.write_bit(True)
            length_enc = length - 2
            hi = (length_enc << 5) | ((offset_enc >> 8) & 0x1F)
            lo = offset_enc & 0xFF
            self._writer.write_data_byte(hi)
            self._writer.write_data_byte(lo)
            self._writer.end_operation()
            return

        # Last resort: emit as literals (shouldn't happen with WINDOW_SIZE = 8192)
        raise ValueError(f"Cannot encode back-reference: offset={offset}, length={length}")

    def encode(self, data: bytes) -> bytes:
        """
        Compress data using LZ77.

        :param data: Uncompressed data.
        :return: LZ77 compressed data.
        """
        self._writer = LZInterleavedWriter()
        pos = 0

        while pos < len(data):
            offset, length = self._find_match(data, pos)

            if length >= self.MIN_MATCH:
                # Encode in chunks if match is very long (max 280 per chunk)
                while length >= self.MIN_MATCH:
                    chunk = min(length, 280)
                    self._encode_backref(offset, chunk)
                    pos += chunk
                    length -= chunk
                    # For subsequent chunks, offset stays same (relative to NEW position)
                    # Actually we need to re-find match for correct offset
                    if length >= self.MIN_MATCH:
                        offset, length = self._find_match(data, pos)
            else:
                self._encode_literal(data[pos])
                pos += 1

        return self._writer.finish()


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

        # Combine: table (starting with root node ID) + huffman data
        # The decoder expects: [root_id, node_data...] + encoded_data
        # table_bytes already has this format from _build_tree
        return table_bytes + huffman_data


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

        # Combine: table (starting with root node ID) + huffman data
        return table_bytes + huffman_data


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
