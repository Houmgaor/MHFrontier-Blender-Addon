# -*- coding: utf-8 -*-
"""
JKR/JPK decompression for Monster Hunter Frontier stage files.

Ported from ReFrontier (C#) by Houmgaor.

Supports 4 compression types:
- Type 0 (RW): Raw, no compression
- Type 1 (HFIRW): Huffman encoding only
- Type 2 (LZ): LZ77 compression
- Type 3 (HFI): Huffman + LZ77 compression
"""

import struct
from dataclasses import dataclass
from enum import IntEnum
from io import BytesIO
from typing import Optional


class CompressionType(IntEnum):
    """JKR compression types."""
    RW = 0      # Raw (no compression)
    NONE = 1    # Special type for "no compression"
    HFIRW = 2   # Huffman only
    LZ = 3      # LZ77
    HFI = 4     # Huffman + LZ77


# JKR magic bytes: "JKR\x1A" (little endian: 0x1A524B4A)
JKR_MAGIC = 0x1A524B4A


@dataclass
class JKRHeader:
    """JKR file header structure."""
    magic: int              # 4 bytes: 0x1A524B4A ("JKR\x1A")
    version: int            # 2 bytes: usually 0x108
    compression_type: int   # 2 bytes: compression type enum
    data_offset: int        # 4 bytes: offset to compressed data
    decompressed_size: int  # 4 bytes: size after decompression

    @classmethod
    def from_bytes(cls, data: bytes) -> Optional["JKRHeader"]:
        """
        Parse JKR header from bytes.

        :param data: At least 16 bytes of header data.
        :return: Parsed header or None if invalid magic.
        """
        if len(data) < 16:
            return None

        magic, version, compression_type, data_offset, decompressed_size = struct.unpack(
            "<IHHII", data[:16]
        )

        if magic != JKR_MAGIC:
            return None

        return cls(
            magic=magic,
            version=version,
            compression_type=compression_type,
            data_offset=data_offset,
            decompressed_size=decompressed_size,
        )


class LZDecoder:
    """
    LZ77 decompression for JPK files.

    Ported from ReFrontier JPKDecodeLz.cs
    """

    def __init__(self):
        self._shift_index = 0
        self._flag = 0

    def _read_byte(self, stream: BytesIO) -> int:
        """Read a single byte from stream."""
        byte = stream.read(1)
        if not byte:
            raise EOFError("Reached end of file too early!")
        return byte[0]

    def _jpk_bit_lz(self, stream: BytesIO) -> bool:
        """Return the value of the next bit from stream."""
        if self._shift_index <= 0:
            self._shift_index = 7
            self._flag = self._read_byte(stream)
        else:
            self._shift_index -= 1
        return ((self._flag >> self._shift_index) & 1) == 1

    @staticmethod
    def _jpk_copy_lz(buffer: bytearray, offset: int, length: int, index: int) -> int:
        """
        Copy length bytes to buffer at position index.
        Bytes are copied from position index - offset - 1.
        """
        for i in range(length):
            buffer[index + i] = buffer[index + i - offset - 1]
        return length

    def decode(self, in_stream: BytesIO, out_size: int) -> bytes:
        """
        Decompress LZ77 data.

        :param in_stream: Input stream positioned at compressed data.
        :param out_size: Expected output size.
        :return: Decompressed data.
        """
        out_buffer = bytearray(out_size)
        out_index = 0

        while out_index < out_size:
            try:
                if not self._jpk_bit_lz(in_stream):
                    out_buffer[out_index] = self._read_byte(in_stream)
                    out_index += 1
                    continue

                if not self._jpk_bit_lz(in_stream):
                    # Case 0: short back-reference
                    length = (2 if self._jpk_bit_lz(in_stream) else 0) + (1 if self._jpk_bit_lz(in_stream) else 0)
                    offset = self._read_byte(in_stream)
                    out_index += self._jpk_copy_lz(out_buffer, offset, length + 3, out_index)
                    continue

                hi = self._read_byte(in_stream)
                lo = self._read_byte(in_stream)
                length = (hi & 0xE0) >> 5
                offset = ((hi & 0x1F) << 8) | lo

                if length != 0:
                    # Case 1: use length directly
                    out_index += self._jpk_copy_lz(out_buffer, offset, length + 2, out_index)
                    continue

                if not self._jpk_bit_lz(in_stream):
                    # Case 2: compute bytes to copy length
                    length = 0
                    for i in range(3, -1, -1):
                        if self._jpk_bit_lz(in_stream):
                            length += 1 << i
                    out_index += self._jpk_copy_lz(out_buffer, offset, length + 2 + 8, out_index)
                    continue

                temp = self._read_byte(in_stream)
                if temp == 0xFF:
                    # Case 3: literal run
                    for _ in range(offset + 0x1B):
                        out_buffer[out_index] = self._read_byte(in_stream)
                        out_index += 1
                    continue

                # Case 4: long back-reference
                out_index += self._jpk_copy_lz(out_buffer, offset, temp + 0x1A, out_index)

            except EOFError:
                break

        return bytes(out_buffer)


class HFIDecoder(LZDecoder):
    """
    Huffman + LZ77 decompression.

    Ported from ReFrontier JPKDecodeHFI.cs
    Uses Huffman decoding for byte reading on top of LZ77.
    """

    def __init__(self):
        super().__init__()
        self._flag_hf = 0
        self._flag_shift = 0
        self._hf_table_offset = 0
        self._hf_data_offset = 0
        self._hf_table_len = 0
        self._stream = None
        self._use_huffman = False

    def _read_byte(self, stream: BytesIO) -> int:
        """
        Read a byte - uses Huffman decoding after initialization.

        Overrides LZDecoder._read_byte to use Huffman table lookup.
        """
        if not self._use_huffman:
            return super()._read_byte(stream)

        # JpkGetHf implementation
        data = self._hf_table_len

        while data >= 0x100:
            self._flag_shift -= 1
            if self._flag_shift < 0:
                self._flag_shift = 7
                stream.seek(self._hf_data_offset)
                self._hf_data_offset += 1
                byte_read = stream.read(1)
                if not byte_read:
                    raise EOFError("Reached end of file too early in Huffman decode!")
                self._flag_hf = byte_read[0]

            bit = (self._flag_hf >> self._flag_shift) & 0x1
            stream.seek((data * 2 - 0x200 + bit) * 2 + self._hf_table_offset)
            data = struct.unpack("<h", stream.read(2))[0]

        return data & 0xFF

    def decode(self, in_stream: BytesIO, out_size: int) -> bytes:
        """
        Decompress Huffman + LZ77 data.

        :param in_stream: Input stream positioned at compressed data.
        :param out_size: Expected output size.
        :return: Decompressed data.
        """
        # Read Huffman table length
        self._hf_table_len = struct.unpack("<h", in_stream.read(2))[0]
        self._hf_table_offset = in_stream.tell()
        self._hf_data_offset = self._hf_table_offset + self._hf_table_len * 4 - 0x3FC
        self._stream = in_stream

        # Enable Huffman byte reading
        self._use_huffman = True

        try:
            return super().decode(in_stream, out_size)
        finally:
            self._use_huffman = False


class RWDecoder:
    """Raw decoder - no compression."""

    def decode(self, in_stream: BytesIO, out_size: int) -> bytes:
        """Read raw bytes."""
        return in_stream.read(out_size)


class HFIRWDecoder:
    """
    Huffman-only decoder (no LZ77).

    Ported from ReFrontier JPKDecodeHFIRW.cs
    """

    def __init__(self):
        self._flag_hf = 0
        self._flag_shift = 0
        self._hf_table_offset = 0
        self._hf_data_offset = 0
        self._hf_table_len = 0

    def _read_byte_hf(self, stream: BytesIO) -> int:
        """Read a byte using Huffman decoding."""
        data = self._hf_table_len

        while data >= 0x100:
            self._flag_shift -= 1
            if self._flag_shift < 0:
                self._flag_shift = 7
                stream.seek(self._hf_data_offset)
                self._hf_data_offset += 1
                self._flag_hf = stream.read(1)[0]

            bit = (self._flag_hf >> self._flag_shift) & 0x1
            stream.seek((data * 2 - 0x200 + bit) * 2 + self._hf_table_offset)
            data = struct.unpack("<h", stream.read(2))[0]

        return data & 0xFF

    def decode(self, in_stream: BytesIO, out_size: int) -> bytes:
        """Decompress using Huffman only."""
        # Read Huffman table length
        self._hf_table_len = struct.unpack("<h", in_stream.read(2))[0]
        self._hf_table_offset = in_stream.tell()
        self._hf_data_offset = self._hf_table_offset + self._hf_table_len * 4 - 0x3FC

        out_buffer = bytearray(out_size)
        for i in range(out_size):
            out_buffer[i] = self._read_byte_hf(in_stream)

        return bytes(out_buffer)


def decompress_jkr(data: bytes) -> Optional[bytes]:
    """
    Decompress JKR/JPK compressed data.

    :param data: Raw JKR file data.
    :return: Decompressed data, or None if not a valid JKR file.
    """
    header = JKRHeader.from_bytes(data)
    if header is None:
        return None

    stream = BytesIO(data)
    stream.seek(header.data_offset)

    compression_type = CompressionType(header.compression_type)

    if compression_type == CompressionType.RW:
        decoder = RWDecoder()
    elif compression_type == CompressionType.NONE:
        decoder = RWDecoder()  # Same as RW
    elif compression_type == CompressionType.HFIRW:
        decoder = HFIRWDecoder()
    elif compression_type == CompressionType.LZ:
        decoder = LZDecoder()
    elif compression_type == CompressionType.HFI:
        decoder = HFIDecoder()
    else:
        raise NotImplementedError(f"JPK compression type {header.compression_type} not supported")

    return decoder.decode(stream, header.decompressed_size)


def is_jkr_file(data: bytes) -> bool:
    """
    Check if data starts with JKR magic bytes.

    :param data: Raw file data.
    :return: True if this is a JKR file.
    """
    if len(data) < 4:
        return False
    magic = struct.unpack("<I", data[:4])[0]
    return magic == JKR_MAGIC
