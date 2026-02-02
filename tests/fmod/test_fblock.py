"""Tests for fblock module, including BlockType enum."""

import unittest

from mhfrontier.fmod.fblock import (
    BlockType,
    BLOCK_TYPE_MAP,
    fblock_type_lookup,
    _format_block_type,
    FileBlock,
    MainBlock,
    ObjectBlock,
    FaceBlock,
    SkeletonBlock,
    UnknBlock,
)


class TestBlockTypeEnum(unittest.TestCase):
    """Tests for the BlockType enum."""

    def test_structural_block_values(self):
        """Test structural block type values match expected hex."""
        self.assertEqual(BlockType.FILE, 0x00000001)
        self.assertEqual(BlockType.MAIN, 0x00000002)
        self.assertEqual(BlockType.OBJECT, 0x00000004)
        self.assertEqual(BlockType.FACE, 0x00000005)
        self.assertEqual(BlockType.MATERIAL, 0x00000009)
        self.assertEqual(BlockType.TEXTURE, 0x0000000A)
        self.assertEqual(BlockType.INIT, 0x00020000)

    def test_geometry_block_values(self):
        """Test geometry block type values match expected hex."""
        self.assertEqual(BlockType.TRIS_STRIPS_A, 0x00030000)
        self.assertEqual(BlockType.TRIS_STRIPS_B, 0x00040000)
        self.assertEqual(BlockType.VERTEX, 0x00070000)
        self.assertEqual(BlockType.NORMALS, 0x00080000)
        self.assertEqual(BlockType.UV, 0x000A0000)
        self.assertEqual(BlockType.RGB, 0x000B0000)
        self.assertEqual(BlockType.WEIGHT, 0x000C0000)

    def test_skeleton_block_values(self):
        """Test skeleton block type values match expected hex."""
        self.assertEqual(BlockType.SKELETON, 0xC0000000)
        self.assertEqual(BlockType.BONE, 0x40000001)

    def test_enum_names(self):
        """Test enum names are uppercase identifiers."""
        for member in BlockType:
            self.assertTrue(member.name.isupper())
            self.assertFalse(" " in member.name)


class TestBlockTypeMap(unittest.TestCase):
    """Tests for the block type map lookup."""

    def test_all_enum_values_mapped(self):
        """Test all BlockType enum values are in BLOCK_TYPE_MAP."""
        for block_type in BlockType:
            self.assertIn(
                block_type,
                BLOCK_TYPE_MAP,
                f"BlockType.{block_type.name} not in BLOCK_TYPE_MAP",
            )

    def test_lookup_returns_correct_classes(self):
        """Test fblock_type_lookup returns correct block classes."""
        self.assertEqual(fblock_type_lookup(BlockType.FILE), FileBlock)
        self.assertEqual(fblock_type_lookup(BlockType.MAIN), MainBlock)
        self.assertEqual(fblock_type_lookup(BlockType.OBJECT), ObjectBlock)
        self.assertEqual(fblock_type_lookup(BlockType.FACE), FaceBlock)
        self.assertEqual(fblock_type_lookup(BlockType.SKELETON), SkeletonBlock)

    def test_lookup_unknown_returns_unknblock(self):
        """Test unknown type ID returns UnknBlock."""
        self.assertEqual(fblock_type_lookup(0xDEADBEEF), UnknBlock)
        self.assertEqual(fblock_type_lookup(0x99999999), UnknBlock)


class TestFormatBlockType(unittest.TestCase):
    """Tests for _format_block_type helper."""

    def test_known_type_returns_name(self):
        """Test known type returns enum name."""
        self.assertEqual(_format_block_type(BlockType.FILE), "FILE")
        self.assertEqual(_format_block_type(BlockType.SKELETON), "SKELETON")
        self.assertEqual(_format_block_type(0x00000001), "FILE")

    def test_unknown_type_returns_hex(self):
        """Test unknown type returns hex string."""
        self.assertEqual(_format_block_type(0xDEADBEEF), "0xdeadbeef")
        self.assertEqual(_format_block_type(0x12345678), "0x12345678")


if __name__ == "__main__":
    unittest.main()
