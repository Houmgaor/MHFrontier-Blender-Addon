"""Unit tests for jkr_compress module."""

import struct
import unittest
from io import BytesIO

from mhfrontier.stage.jkr_compress import (
    BitWriter,
    JKRHeaderBuilder,
    LZEncoder,
    HuffmanEncoder,
    HFIEncoder,
    HFIRWEncoder,
    compress_jkr,
    compress_jkr_hfi,
    compress_jkr_raw,
)
from mhfrontier.stage.jkr_decompress import (
    JKR_MAGIC,
    JKRHeader,
    CompressionType,
    decompress_jkr,
    is_jkr_file,
)


class TestJKRHeaderBuilder(unittest.TestCase):
    """Test JKRHeaderBuilder serialization."""

    def test_to_bytes_default(self):
        """Test default header serialization."""
        header = JKRHeaderBuilder(decompressed_size=100)
        data = header.to_bytes()

        self.assertEqual(len(data), 16)

        # Parse back
        parsed = JKRHeader.from_bytes(data)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.magic, JKR_MAGIC)
        self.assertEqual(parsed.version, 0x108)
        self.assertEqual(parsed.compression_type, CompressionType.HFI)
        self.assertEqual(parsed.data_offset, 16)
        self.assertEqual(parsed.decompressed_size, 100)

    def test_to_bytes_raw(self):
        """Test RW compression type header."""
        header = JKRHeaderBuilder(
            compression_type=CompressionType.RW,
            decompressed_size=50,
        )
        data = header.to_bytes()

        parsed = JKRHeader.from_bytes(data)
        self.assertEqual(parsed.compression_type, CompressionType.RW)
        self.assertEqual(parsed.decompressed_size, 50)


class TestBitWriter(unittest.TestCase):
    """Test BitWriter helper class."""

    def test_write_bits(self):
        """Test writing individual bits."""
        writer = BitWriter()
        writer.write_bit(True)
        writer.write_bit(False)
        writer.write_bit(True)
        writer.write_bit(False)
        writer.write_bit(True)
        writer.write_bit(False)
        writer.write_bit(True)
        writer.write_bit(False)

        result = writer.flush()
        self.assertEqual(result, bytes([0b10101010]))

    def test_write_byte(self):
        """Test writing a full byte."""
        writer = BitWriter()
        writer.write_byte(0xAB)

        result = writer.flush()
        self.assertEqual(result, bytes([0xAB]))

    def test_write_multiple_bits_value(self):
        """Test writing multiple bits as a value."""
        writer = BitWriter()
        writer.write_bits(0b101, 3)  # Write 101 in 3 bits
        writer.write_bits(0b11, 2)   # Write 11 in 2 bits
        writer.write_bits(0b000, 3)  # Write 000 in 3 bits

        result = writer.flush()
        # Should be: 101 11 000 = 0b10111000 = 0xB8
        self.assertEqual(result, bytes([0xB8]))

    def test_flush_partial_byte(self):
        """Test flushing with partial byte."""
        writer = BitWriter()
        writer.write_bit(True)
        writer.write_bit(True)
        writer.write_bit(True)

        result = writer.flush()
        # 111 + 5 zeros = 11100000 = 0xE0
        self.assertEqual(result, bytes([0xE0]))


class TestLZEncoder(unittest.TestCase):
    """Test LZEncoder compression."""

    def test_find_match_no_history(self):
        """Test no match found at start of data."""
        encoder = LZEncoder()
        data = b"ABCDEFGH"
        offset, length = encoder._find_match(data, 0)
        self.assertEqual(offset, 0)
        self.assertEqual(length, 0)

    def test_find_match_simple_repeat(self):
        """Test finding a simple repeated sequence."""
        encoder = LZEncoder()
        data = b"ABCDABCD"
        offset, length = encoder._find_match(data, 4)
        self.assertEqual(offset, 4)
        self.assertEqual(length, 4)

    def test_find_match_partial_repeat(self):
        """Test finding partial match."""
        encoder = LZEncoder()
        data = b"ABCDEFABCXYZ"
        offset, length = encoder._find_match(data, 6)
        # Should find ABC at position 0
        self.assertGreater(length, 0)

    def test_encode_short_data(self):
        """Test encoding very short data."""
        encoder = LZEncoder()
        data = b"AB"
        result = encoder.encode(data)
        # Very short data should encode as literals
        self.assertIsInstance(result, bytes)
        self.assertGreater(len(result), 0)

    def test_encode_repetitive_data(self):
        """Test encoding highly repetitive data."""
        encoder = LZEncoder()
        data = b"A" * 100
        result = encoder.encode(data)
        # Repetitive data should compress well
        self.assertLess(len(result), len(data))


class TestHuffmanEncoder(unittest.TestCase):
    """Test HuffmanEncoder compression."""

    def test_encode_single_byte_type(self):
        """Test encoding data with single byte value."""
        encoder = HuffmanEncoder()
        data = b"AAAA"
        table, encoded = encoder.encode(data)
        self.assertIsInstance(table, bytes)
        self.assertIsInstance(encoded, bytes)

    def test_encode_two_byte_types(self):
        """Test encoding data with two byte values."""
        encoder = HuffmanEncoder()
        data = b"ABABAB"
        table, encoded = encoder.encode(data)
        self.assertIsInstance(table, bytes)
        self.assertIsInstance(encoded, bytes)

    def test_encode_varied_data(self):
        """Test encoding data with varied byte values."""
        encoder = HuffmanEncoder()
        data = b"Hello, World!"
        table, encoded = encoder.encode(data)
        self.assertIsInstance(table, bytes)
        self.assertIsInstance(encoded, bytes)


class TestCompressJkr(unittest.TestCase):
    """Test the main compress_jkr function."""

    def test_compress_raw(self):
        """Test RW (raw) compression."""
        test_data = b"Test payload data"
        result = compress_jkr(test_data, CompressionType.RW)

        # Should have header + original data
        self.assertTrue(is_jkr_file(result))
        self.assertEqual(len(result), 16 + len(test_data))

        # Should decompress back to original
        decompressed = decompress_jkr(result)
        self.assertEqual(decompressed, test_data)

    def test_compress_raw_shortcut(self):
        """Test compress_jkr_raw shortcut function."""
        test_data = b"Another test"
        result = compress_jkr_raw(test_data)

        self.assertTrue(is_jkr_file(result))
        decompressed = decompress_jkr(result)
        self.assertEqual(decompressed, test_data)


class TestRoundTrip(unittest.TestCase):
    """Test round-trip compression and decompression."""

    def test_roundtrip_raw(self):
        """Test RW round-trip."""
        test_data = b"Hello, World! This is a test."
        compressed = compress_jkr(test_data, CompressionType.RW)
        decompressed = decompress_jkr(compressed)
        self.assertEqual(decompressed, test_data)

    def test_roundtrip_empty_data(self):
        """Test round-trip with empty data."""
        test_data = b""
        compressed = compress_jkr(test_data, CompressionType.RW)
        decompressed = decompress_jkr(compressed)
        self.assertEqual(decompressed, test_data)

    def test_roundtrip_single_byte(self):
        """Test round-trip with single byte."""
        test_data = b"X"
        compressed = compress_jkr(test_data, CompressionType.RW)
        decompressed = decompress_jkr(compressed)
        self.assertEqual(decompressed, test_data)

    def test_roundtrip_binary_data(self):
        """Test round-trip with binary data."""
        test_data = bytes(range(256))
        compressed = compress_jkr(test_data, CompressionType.RW)
        decompressed = decompress_jkr(compressed)
        self.assertEqual(decompressed, test_data)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases for compression."""

    def test_all_zeros(self):
        """Test compressing all-zero data."""
        test_data = b"\x00" * 100
        compressed = compress_jkr(test_data, CompressionType.RW)
        decompressed = decompress_jkr(compressed)
        self.assertEqual(decompressed, test_data)

    def test_all_ones(self):
        """Test compressing all-ones data."""
        test_data = b"\xFF" * 100
        compressed = compress_jkr(test_data, CompressionType.RW)
        decompressed = decompress_jkr(compressed)
        self.assertEqual(decompressed, test_data)

    def test_alternating_pattern(self):
        """Test compressing alternating pattern."""
        test_data = b"\xAA\x55" * 50
        compressed = compress_jkr(test_data, CompressionType.RW)
        decompressed = decompress_jkr(compressed)
        self.assertEqual(decompressed, test_data)

    def test_large_data(self):
        """Test compressing larger data."""
        test_data = bytes(range(256)) * 40  # 10KB
        compressed = compress_jkr(test_data, CompressionType.RW)
        decompressed = decompress_jkr(compressed)
        self.assertEqual(decompressed, test_data)


class TestLZEncoderCompression(unittest.TestCase):
    """Test LZ77-only compression."""

    def test_lz_encode_literals_only(self):
        """Test LZ encoding with no matches (all literals)."""
        encoder = LZEncoder()
        # Non-repeating data
        data = bytes(range(10))
        result = encoder.encode(data)
        self.assertIsInstance(result, bytes)

    def test_lz_encode_repetitive(self):
        """Test LZ encoding with repetitive data."""
        encoder = LZEncoder()
        data = b"ABCDEFABCDEF" * 10
        result = encoder.encode(data)
        # Should compress repetitive data
        self.assertLess(len(result), len(data))


class TestHFIEncoder(unittest.TestCase):
    """Test combined Huffman + LZ77 encoding."""

    def test_hfi_encode_simple(self):
        """Test HFI encoding simple data."""
        encoder = HFIEncoder()
        data = b"Hello, World!"
        result = encoder.encode(data)
        self.assertIsInstance(result, bytes)
        self.assertGreater(len(result), 0)

    def test_hfi_encode_repetitive(self):
        """Test HFI encoding repetitive data."""
        encoder = HFIEncoder()
        data = b"ABCABCABC" * 10
        result = encoder.encode(data)
        self.assertIsInstance(result, bytes)


class TestHFIRWEncoder(unittest.TestCase):
    """Test Huffman-only encoding."""

    def test_hfirw_encode_simple(self):
        """Test HFIRW encoding simple data."""
        encoder = HFIRWEncoder()
        data = b"Hello, World!"
        result = encoder.encode(data)
        self.assertIsInstance(result, bytes)
        self.assertGreater(len(result), 0)

    def test_hfirw_encode_single_value(self):
        """Test HFIRW encoding single-value data."""
        encoder = HFIRWEncoder()
        data = b"AAAA"
        result = encoder.encode(data)
        self.assertIsInstance(result, bytes)


if __name__ == "__main__":
    unittest.main()
