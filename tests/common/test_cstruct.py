"""Unit tests for cstruct module."""

import struct
import unittest
from io import BytesIO

from mhfrontier.common.cstruct import (
    Cstruct,
    chunks,
    half_to_float,
    minifloat_deserialize,
    minifloat_serialize,
)


class TestChunks(unittest.TestCase):
    """Test the chunks helper function."""

    def test_chunks_exact_division(self):
        """Test chunking when length divides evenly."""
        result = list(chunks([1, 2, 3, 4, 5, 6], 2))
        self.assertEqual(result, [[1, 2], [3, 4], [5, 6]])

    def test_chunks_with_remainder(self):
        """Test chunking with remainder."""
        result = list(chunks([1, 2, 3, 4, 5], 2))
        self.assertEqual(result, [[1, 2], [3, 4], [5]])

    def test_chunks_bytes(self):
        """Test chunking bytes."""
        result = list(chunks(b"\x01\x02\x03\x04", 2))
        self.assertEqual(result, [b"\x01\x02", b"\x03\x04"])


class TestHalfFloat(unittest.TestCase):
    """Test half-precision float conversion."""

    def test_half_to_float_zero(self):
        """Test zero value."""
        self.assertEqual(half_to_float(0), 0)

    def test_half_to_float_one(self):
        """Test value 1.0 (0x3C00 in half-float)."""
        result = half_to_float(0x3C00)
        self.assertAlmostEqual(result, 1.0, places=3)

    def test_half_to_float_negative(self):
        """Test negative value."""
        result = half_to_float(0xBC00)  # -1.0
        self.assertAlmostEqual(result, -1.0, places=3)

    def test_minifloat_roundtrip(self):
        """Test serialize then deserialize produces similar value."""
        original = 1.5
        serialized = minifloat_serialize(original)
        deserialized = minifloat_deserialize(serialized)
        self.assertAlmostEqual(deserialized, original, places=2)


class TestCstructBasicTypes(unittest.TestCase):
    """Test Cstruct with basic C types."""

    def test_uint8(self):
        """Test unsigned 8-bit integer."""
        cs = Cstruct({"value": "uint8"})
        data = BytesIO(b"\xFF")
        result = cs.marshall(data)
        self.assertEqual(result["value"], 255)

    def test_int8(self):
        """Test signed 8-bit integer."""
        cs = Cstruct({"value": "int8"})
        data = BytesIO(b"\xFF")
        result = cs.marshall(data)
        self.assertEqual(result["value"], -1)

    def test_uint16(self):
        """Test unsigned 16-bit integer."""
        cs = Cstruct({"value": "uint16"})
        data = BytesIO(b"\x01\x00")  # Little endian
        result = cs.marshall(data)
        self.assertEqual(result["value"], 1)

    def test_uint32(self):
        """Test unsigned 32-bit integer."""
        cs = Cstruct({"value": "uint32"})
        data = BytesIO(b"\x01\x00\x00\x00")
        result = cs.marshall(data)
        self.assertEqual(result["value"], 1)

    def test_float(self):
        """Test 32-bit float."""
        cs = Cstruct({"value": "float"})
        data = BytesIO(struct.pack("f", 3.14))
        result = cs.marshall(data)
        self.assertAlmostEqual(result["value"], 3.14, places=5)

    def test_multiple_fields(self):
        """Test struct with multiple fields."""
        cs = Cstruct({
            "x": "float",
            "y": "float",
            "z": "float",
        })
        data = BytesIO(struct.pack("fff", 1.0, 2.0, 3.0))
        result = cs.marshall(data)
        self.assertAlmostEqual(result["x"], 1.0)
        self.assertAlmostEqual(result["y"], 2.0)
        self.assertAlmostEqual(result["z"], 3.0)


class TestCstructSize(unittest.TestCase):
    """Test Cstruct size calculation."""

    def test_size_single_field(self):
        """Test size with single field."""
        cs = Cstruct({"value": "uint32"})
        self.assertEqual(cs.size(), 4)

    def test_size_multiple_fields(self):
        """Test size with multiple fields."""
        cs = Cstruct({
            "a": "uint8",
            "b": "uint16",
            "c": "uint32",
        })
        self.assertEqual(cs.size(), 1 + 2 + 4)

    def test_size_array(self):
        """Test size with array field."""
        cs = Cstruct({"values": "uint32[4]"})
        self.assertEqual(cs.size(), 16)


class TestCstructArrays(unittest.TestCase):
    """Test Cstruct array types."""

    def test_uint8_array(self):
        """Test array of uint8."""
        cs = Cstruct({"values": "uint8[4]"})
        data = BytesIO(b"\x01\x02\x03\x04")
        result = cs.marshall(data)
        self.assertEqual(result["values"], [1, 2, 3, 4])

    def test_uint32_array(self):
        """Test array of uint32."""
        cs = Cstruct({"values": "uint32[2]"})
        data = BytesIO(struct.pack("<II", 100, 200))
        result = cs.marshall(data)
        self.assertEqual(result["values"], [100, 200])

    def test_char_array(self):
        """Test char array (string)."""
        cs = Cstruct({"name": "char[8]"})
        data = BytesIO(b"Test\x00\x00\x00\x00")
        result = cs.marshall(data)
        self.assertEqual(result["name"], "Test\x00\x00\x00\x00")


class TestCstructSerialize(unittest.TestCase):
    """Test Cstruct serialization (writing)."""

    def test_serialize_uint32(self):
        """Test serializing uint32."""
        cs = Cstruct({"value": "uint32"})
        result = cs.serialize({"value": 0x12345678})
        self.assertEqual(result, b"\x78\x56\x34\x12")

    def test_serialize_multiple(self):
        """Test serializing multiple fields."""
        cs = Cstruct({
            "a": "uint8",
            "b": "uint16",
        })
        result = cs.serialize({"a": 1, "b": 2})
        self.assertEqual(result, b"\x01\x02\x00")

    def test_roundtrip(self):
        """Test serialize then deserialize produces original values."""
        cs = Cstruct({
            "x": "float",
            "y": "float",
            "count": "uint32",
        })
        original = {"x": 1.5, "y": 2.5, "count": 42}
        serialized = cs.serialize(original)
        deserialized = cs.marshall(BytesIO(serialized))

        self.assertAlmostEqual(deserialized["x"], original["x"])
        self.assertAlmostEqual(deserialized["y"], original["y"])
        self.assertEqual(deserialized["count"], original["count"])


class TestCstructInvalidTypes(unittest.TestCase):
    """Test Cstruct error handling."""

    def test_invalid_type_raises(self):
        """Test that invalid type raises ValueError."""
        with self.assertRaises(ValueError):
            Cstruct({"value": "invalid_type"})


if __name__ == "__main__":
    unittest.main()
