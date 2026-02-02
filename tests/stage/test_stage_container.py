"""Unit tests for stage_container module."""

import struct
import unittest

from mhfrontier.stage.stage_container import (
    MAGIC_BYTES,
    SegmentType,
    StageSegment,
    detect_segment_type,
    get_fmod_segments,
    get_texture_segments,
    is_stage_container,
    parse_stage_container,
)
from mhfrontier.stage.jkr_decompress import JKR_MAGIC


class TestDetectSegmentType(unittest.TestCase):
    """Test segment type detection from magic bytes."""

    def test_detect_jkr(self):
        """Test JKR detection."""
        data = struct.pack("<I", JKR_MAGIC) + b"\x00" * 10
        self.assertEqual(detect_segment_type(data), SegmentType.JKR)

    def test_detect_fmod(self):
        """Test FMOD detection."""
        data = b"FMOD" + b"\x00" * 10
        # FMOD magic is 0x444F4D46 in little endian
        self.assertEqual(detect_segment_type(data), SegmentType.FMOD)

    def test_detect_png(self):
        """Test PNG detection."""
        # PNG magic: 0x89 0x50 0x4E 0x47
        data = b"\x89PNG" + b"\x00" * 10
        self.assertEqual(detect_segment_type(data), SegmentType.PNG)

    def test_detect_dds(self):
        """Test DDS detection."""
        data = b"DDS " + b"\x00" * 10
        self.assertEqual(detect_segment_type(data), SegmentType.DDS)

    def test_detect_ogg(self):
        """Test OGG detection."""
        data = b"OggS" + b"\x00" * 10
        self.assertEqual(detect_segment_type(data), SegmentType.OGG)

    def test_detect_unknown(self):
        """Test unknown type."""
        data = b"XXXX" + b"\x00" * 10
        self.assertEqual(detect_segment_type(data), SegmentType.UNKNOWN)

    def test_detect_too_short(self):
        """Test with data too short."""
        self.assertEqual(detect_segment_type(b"AB"), SegmentType.UNKNOWN)


class TestStageSegment(unittest.TestCase):
    """Test StageSegment dataclass."""

    def test_extension_jkr(self):
        """Test JKR extension."""
        segment = StageSegment(
            index=0, offset=0, size=10, unknown=0,
            data=b"", segment_type=SegmentType.JKR
        )
        self.assertEqual(segment.extension, "jkr")

    def test_extension_fmod(self):
        """Test FMOD extension."""
        segment = StageSegment(
            index=0, offset=0, size=10, unknown=0,
            data=b"", segment_type=SegmentType.FMOD
        )
        self.assertEqual(segment.extension, "fmod")

    def test_extension_png(self):
        """Test PNG extension."""
        segment = StageSegment(
            index=0, offset=0, size=10, unknown=0,
            data=b"", segment_type=SegmentType.PNG
        )
        self.assertEqual(segment.extension, "png")

    def test_extension_unknown(self):
        """Test unknown extension defaults to bin."""
        segment = StageSegment(
            index=0, offset=0, size=10, unknown=0,
            data=b"", segment_type=SegmentType.UNKNOWN
        )
        self.assertEqual(segment.extension, "bin")


class TestIsStageContainer(unittest.TestCase):
    """Test stage container detection heuristic."""

    def test_too_short(self):
        """Test data too short returns False."""
        self.assertFalse(is_stage_container(b"\x00" * 10))

    def test_valid_heuristic(self):
        """Test valid stage container heuristic."""
        # Create data that passes heuristic:
        # - bytes 4-8: small value < 9999
        # - bytes 8-16: zero
        data = struct.pack("<IIQQ", 0, 100, 0, 0)
        self.assertTrue(is_stage_container(data))

    def test_invalid_large_count(self):
        """Test invalid container with large count."""
        data = struct.pack("<IIQQ", 0, 99999, 0, 0)
        self.assertFalse(is_stage_container(data))

    def test_invalid_nonzero_check(self):
        """Test invalid container with non-zero check bytes."""
        data = struct.pack("<IIQQ", 0, 100, 12345, 0)
        self.assertFalse(is_stage_container(data))


class TestGetFmodSegments(unittest.TestCase):
    """Test FMOD segment filtering."""

    def test_get_fmod_direct(self):
        """Test getting direct FMOD segments."""
        segments = [
            StageSegment(0, 0, 10, 0, b"", SegmentType.FMOD),
            StageSegment(1, 10, 10, 0, b"", SegmentType.PNG),
            StageSegment(2, 20, 10, 0, b"", SegmentType.FMOD),
        ]
        result = get_fmod_segments(segments)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].index, 0)
        self.assertEqual(result[1].index, 2)

    def test_get_fmod_includes_jkr(self):
        """Test that JKR segments are included (may contain FMOD)."""
        segments = [
            StageSegment(0, 0, 10, 0, b"", SegmentType.JKR),
            StageSegment(1, 10, 10, 0, b"", SegmentType.FMOD),
        ]
        result = get_fmod_segments(segments)
        self.assertEqual(len(result), 2)

    def test_get_fmod_excludes_textures(self):
        """Test that texture segments are excluded."""
        segments = [
            StageSegment(0, 0, 10, 0, b"", SegmentType.PNG),
            StageSegment(1, 10, 10, 0, b"", SegmentType.DDS),
            StageSegment(2, 20, 10, 0, b"", SegmentType.OGG),
        ]
        result = get_fmod_segments(segments)
        self.assertEqual(len(result), 0)


class TestGetTextureSegments(unittest.TestCase):
    """Test texture segment filtering."""

    def test_get_textures(self):
        """Test getting texture segments."""
        segments = [
            StageSegment(0, 0, 10, 0, b"", SegmentType.PNG),
            StageSegment(1, 10, 10, 0, b"", SegmentType.FMOD),
            StageSegment(2, 20, 10, 0, b"", SegmentType.DDS),
        ]
        result = get_texture_segments(segments)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].segment_type, SegmentType.PNG)
        self.assertEqual(result[1].segment_type, SegmentType.DDS)

    def test_get_textures_excludes_ogg(self):
        """Test that OGG (audio) is not included in textures."""
        segments = [
            StageSegment(0, 0, 10, 0, b"", SegmentType.OGG),
        ]
        result = get_texture_segments(segments)
        self.assertEqual(len(result), 0)


class TestMagicBytesConsistency(unittest.TestCase):
    """Test that MAGIC_BYTES dict is consistent."""

    def test_jkr_magic_matches(self):
        """Test JKR magic in dict matches module constant."""
        self.assertIn(JKR_MAGIC, MAGIC_BYTES)
        self.assertEqual(MAGIC_BYTES[JKR_MAGIC], SegmentType.JKR)

    def test_all_segment_types_have_extension(self):
        """Test all segment types have valid extensions."""
        for seg_type in SegmentType:
            segment = StageSegment(0, 0, 0, 0, b"", seg_type)
            ext = segment.extension
            self.assertIsInstance(ext, str)
            self.assertGreater(len(ext), 0)


if __name__ == "__main__":
    unittest.main()
