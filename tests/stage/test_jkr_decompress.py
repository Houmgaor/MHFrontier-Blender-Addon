"""Unit tests for jkr_decompress module."""

import struct
import unittest
from io import BytesIO

from mhfrontier.stage.jkr_decompress import (
    JKR_MAGIC,
    JKRHeader,
    CompressionType,
    LZDecoder,
    RWDecoder,
    decompress_jkr,
    is_jkr_file,
)


class TestIsJkrFile(unittest.TestCase):
    """Test is_jkr_file detection."""

    def test_valid_jkr_magic(self):
        """Test detection with valid JKR magic bytes."""
        data = struct.pack("<I", JKR_MAGIC) + b"\x00" * 12
        self.assertTrue(is_jkr_file(data))

    def test_invalid_magic(self):
        """Test detection with invalid magic bytes."""
        data = b"NOTJ" + b"\x00" * 12
        self.assertFalse(is_jkr_file(data))

    def test_too_short(self):
        """Test detection with data too short."""
        data = b"JKR"  # Only 3 bytes
        self.assertFalse(is_jkr_file(data))

    def test_empty_data(self):
        """Test detection with empty data."""
        self.assertFalse(is_jkr_file(b""))


class TestJKRHeader(unittest.TestCase):
    """Test JKRHeader parsing."""

    def test_parse_valid_header(self):
        """Test parsing a valid JKR header."""
        header_data = struct.pack(
            "<IHHII",
            JKR_MAGIC,       # magic
            0x108,           # version
            CompressionType.RW,  # compression type
            16,              # data offset
            100,             # decompressed size
        )
        header = JKRHeader.from_bytes(header_data)

        self.assertIsNotNone(header)
        self.assertEqual(header.magic, JKR_MAGIC)
        self.assertEqual(header.version, 0x108)
        self.assertEqual(header.compression_type, CompressionType.RW)
        self.assertEqual(header.data_offset, 16)
        self.assertEqual(header.decompressed_size, 100)

    def test_parse_invalid_magic(self):
        """Test parsing with invalid magic returns None."""
        header_data = struct.pack("<IHHII", 0x12345678, 0, 0, 0, 0)
        header = JKRHeader.from_bytes(header_data)
        self.assertIsNone(header)

    def test_parse_too_short(self):
        """Test parsing with insufficient data returns None."""
        header = JKRHeader.from_bytes(b"\x00" * 10)
        self.assertIsNone(header)


class TestRWDecoder(unittest.TestCase):
    """Test RWDecoder (raw/no compression)."""

    def test_decode_raw(self):
        """Test decoding raw data."""
        decoder = RWDecoder()
        test_data = b"Hello, World!"
        stream = BytesIO(test_data)
        result = decoder.decode(stream, len(test_data))
        self.assertEqual(result, test_data)

    def test_decode_partial(self):
        """Test decoding partial data."""
        decoder = RWDecoder()
        test_data = b"Hello, World!"
        stream = BytesIO(test_data)
        result = decoder.decode(stream, 5)
        self.assertEqual(result, b"Hello")


class TestLZDecoder(unittest.TestCase):
    """Test LZDecoder basics."""

    def test_jpk_copy_lz(self):
        """Test the LZ copy operation."""
        buffer = bytearray(b"ABCD\x00\x00\x00\x00")
        LZDecoder._jpk_copy_lz(buffer, 3, 4, 4)  # Copy 4 bytes from offset -4
        self.assertEqual(buffer, bytearray(b"ABCDABCD"))

    def test_jpk_copy_lz_overlap(self):
        """Test LZ copy with overlapping source/dest (run-length style)."""
        buffer = bytearray(b"A\x00\x00\x00\x00")
        LZDecoder._jpk_copy_lz(buffer, 0, 4, 1)  # Copy with overlap
        self.assertEqual(buffer, bytearray(b"AAAAA"))


class TestDecompressJkr(unittest.TestCase):
    """Test the main decompress_jkr function."""

    def test_decompress_raw(self):
        """Test decompressing RW (raw) type."""
        test_payload = b"Test payload data"
        header = struct.pack(
            "<IHHII",
            JKR_MAGIC,
            0x108,
            CompressionType.RW,
            16,  # data starts at offset 16
            len(test_payload),
        )
        data = header + test_payload

        result = decompress_jkr(data)
        self.assertEqual(result, test_payload)

    def test_decompress_invalid_magic(self):
        """Test decompressing non-JKR data returns None."""
        data = b"Not a JKR file" + b"\x00" * 100
        result = decompress_jkr(data)
        self.assertIsNone(result)

    def test_decompress_type_none(self):
        """Test decompressing NONE type (same as RW)."""
        test_payload = b"Another test"
        header = struct.pack(
            "<IHHII",
            JKR_MAGIC,
            0x108,
            CompressionType.NONE,
            16,
            len(test_payload),
        )
        data = header + test_payload

        result = decompress_jkr(data)
        self.assertEqual(result, test_payload)


class TestCompressionType(unittest.TestCase):
    """Test CompressionType enum."""

    def test_compression_values(self):
        """Test compression type values match expected."""
        self.assertEqual(CompressionType.RW, 0)
        self.assertEqual(CompressionType.NONE, 1)
        self.assertEqual(CompressionType.HFIRW, 2)
        self.assertEqual(CompressionType.LZ, 3)
        self.assertEqual(CompressionType.HFI, 4)


if __name__ == "__main__":
    unittest.main()
