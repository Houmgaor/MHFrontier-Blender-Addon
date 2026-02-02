"""Unit tests for stage_export module."""

import struct
import unittest

from mhfrontier.stage.stage_export import (
    StageSegmentBuilder,
    build_stage_container,
    segments_to_builders,
    build_segment_from_fmod,
    build_segment_from_texture,
    build_segment_from_audio,
    build_compressed_segment,
)
from mhfrontier.stage.stage_container import (
    SegmentType,
    StageSegment,
    parse_stage_container,
    is_stage_container,
)
from mhfrontier.stage.jkr_decompress import JKR_MAGIC


class TestStageSegmentBuilder(unittest.TestCase):
    """Test StageSegmentBuilder dataclass."""

    def test_create_default(self):
        """Test creating builder with defaults."""
        builder = StageSegmentBuilder(data=b"test")
        self.assertEqual(builder.data, b"test")
        self.assertEqual(builder.segment_type, SegmentType.UNKNOWN)
        self.assertEqual(builder.unknown, 0)

    def test_create_with_type(self):
        """Test creating builder with specific type."""
        builder = StageSegmentBuilder(
            data=b"FMOD",
            segment_type=SegmentType.FMOD,
        )
        self.assertEqual(builder.segment_type, SegmentType.FMOD)

    def test_create_with_unknown(self):
        """Test creating builder with unknown field."""
        builder = StageSegmentBuilder(
            data=b"data",
            unknown=12345,
        )
        self.assertEqual(builder.unknown, 12345)


class TestBuildStageContainer(unittest.TestCase):
    """Test build_stage_container function."""

    def test_build_empty_container(self):
        """Test building empty container."""
        result = build_stage_container([])
        # Should return minimal valid structure
        self.assertIsInstance(result, bytes)
        self.assertEqual(len(result), 32)

    def test_build_single_segment(self):
        """Test building container with single segment."""
        segments = [StageSegmentBuilder(data=b"FMOD" + b"\x00" * 12)]
        result = build_stage_container(segments)

        self.assertIsInstance(result, bytes)
        self.assertGreater(len(result), 16)

        # Should be parseable
        parsed = parse_stage_container(result)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0].data[:4], b"FMOD")

    def test_build_three_segments(self):
        """Test building container with exactly 3 segments."""
        segments = [
            StageSegmentBuilder(data=b"FMOD" + b"\x00" * 12),
            StageSegmentBuilder(data=b"\x89PNG" + b"\x00" * 12),
            StageSegmentBuilder(data=b"DDS " + b"\x00" * 12),
        ]
        result = build_stage_container(segments)

        parsed = parse_stage_container(result)
        self.assertEqual(len(parsed), 3)

    def test_build_four_segments(self):
        """Test building container with 4 segments (uses rest header)."""
        segments = [
            StageSegmentBuilder(data=b"FMOD" + b"\x00" * 12),
            StageSegmentBuilder(data=b"\x89PNG" + b"\x00" * 12),
            StageSegmentBuilder(data=b"DDS " + b"\x00" * 12),
            StageSegmentBuilder(data=b"OggS" + b"\x00" * 12, unknown=42),
        ]
        result = build_stage_container(segments)

        parsed = parse_stage_container(result)
        self.assertEqual(len(parsed), 4)
        # Check that unknown field is preserved
        self.assertEqual(parsed[3].unknown, 42)

    def test_build_many_segments(self):
        """Test building container with many segments."""
        segments = [
            StageSegmentBuilder(data=b"seg" + bytes([i]) * 10)
            for i in range(10)
        ]
        result = build_stage_container(segments)

        parsed = parse_stage_container(result)
        self.assertEqual(len(parsed), 10)

    def test_segment_alignment(self):
        """Test that segments are properly aligned."""
        # Create segments with non-aligned sizes
        segments = [
            StageSegmentBuilder(data=b"X" * 7),   # 7 bytes
            StageSegmentBuilder(data=b"Y" * 13),  # 13 bytes
        ]
        result = build_stage_container(segments)

        # Should be parseable without errors
        parsed = parse_stage_container(result)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(len(parsed[0].data), 7)
        self.assertEqual(len(parsed[1].data), 13)


class TestRoundTrip(unittest.TestCase):
    """Test round-trip: parse -> build -> parse."""

    def test_roundtrip_single_segment(self):
        """Test round-trip with single segment."""
        original_segments = [
            StageSegmentBuilder(data=b"FMOD_DATA_HERE" + b"\x00" * 10),
        ]
        container = build_stage_container(original_segments)

        # Parse and convert back
        parsed = parse_stage_container(container)
        builders = segments_to_builders(parsed)

        # Build again
        container2 = build_stage_container(builders)
        parsed2 = parse_stage_container(container2)

        # Verify data matches
        self.assertEqual(len(parsed2), len(original_segments))
        self.assertEqual(parsed2[0].data, original_segments[0].data)

    def test_roundtrip_multiple_segments(self):
        """Test round-trip with multiple segments."""
        original_segments = [
            StageSegmentBuilder(data=b"FMOD" + b"\x00" * 100),
            StageSegmentBuilder(data=b"\x89PNG" + b"\x00" * 50),
            StageSegmentBuilder(data=b"DDS " + b"\x00" * 75),
            StageSegmentBuilder(data=b"OggS" + b"\x00" * 25, unknown=123),
        ]
        container = build_stage_container(original_segments)

        parsed = parse_stage_container(container)
        builders = segments_to_builders(parsed)
        container2 = build_stage_container(builders)
        parsed2 = parse_stage_container(container2)

        self.assertEqual(len(parsed2), len(original_segments))
        for i, seg in enumerate(parsed2):
            self.assertEqual(seg.data, original_segments[i].data)

    def test_roundtrip_preserves_unknown(self):
        """Test that unknown field is preserved through round-trip."""
        original_segments = [
            StageSegmentBuilder(data=b"seg1"),
            StageSegmentBuilder(data=b"seg2"),
            StageSegmentBuilder(data=b"seg3"),
            StageSegmentBuilder(data=b"seg4", unknown=999),
            StageSegmentBuilder(data=b"seg5", unknown=777),
        ]
        container = build_stage_container(original_segments)

        parsed = parse_stage_container(container)
        self.assertEqual(parsed[3].unknown, 999)
        self.assertEqual(parsed[4].unknown, 777)


class TestHelperFunctions(unittest.TestCase):
    """Test helper functions for building segments."""

    def test_build_segment_from_fmod(self):
        """Test building FMOD segment."""
        fmod_data = b"FMOD" + b"\x00" * 100
        segment = build_segment_from_fmod(fmod_data)

        self.assertEqual(segment.data, fmod_data)
        self.assertEqual(segment.segment_type, SegmentType.FMOD)

    def test_build_segment_from_texture_png(self):
        """Test building PNG texture segment."""
        png_data = b"\x89PNG" + b"\x00" * 100
        segment = build_segment_from_texture(png_data, is_dds=False)

        self.assertEqual(segment.data, png_data)
        self.assertEqual(segment.segment_type, SegmentType.PNG)

    def test_build_segment_from_texture_dds(self):
        """Test building DDS texture segment."""
        dds_data = b"DDS " + b"\x00" * 100
        segment = build_segment_from_texture(dds_data, is_dds=True)

        self.assertEqual(segment.data, dds_data)
        self.assertEqual(segment.segment_type, SegmentType.DDS)

    def test_build_segment_from_audio(self):
        """Test building OGG audio segment."""
        ogg_data = b"OggS" + b"\x00" * 100
        segment = build_segment_from_audio(ogg_data)

        self.assertEqual(segment.data, ogg_data)
        self.assertEqual(segment.segment_type, SegmentType.OGG)


class TestSegmentsToBuilders(unittest.TestCase):
    """Test segments_to_builders conversion."""

    def test_convert_single_segment(self):
        """Test converting single segment."""
        segments = [
            StageSegment(
                index=0,
                offset=0,
                size=10,
                unknown=0,
                data=b"test data!",
                segment_type=SegmentType.FMOD,
            ),
        ]
        builders = segments_to_builders(segments)

        self.assertEqual(len(builders), 1)
        self.assertEqual(builders[0].data, b"test data!")
        self.assertEqual(builders[0].segment_type, SegmentType.FMOD)

    def test_convert_multiple_segments(self):
        """Test converting multiple segments."""
        segments = [
            StageSegment(0, 0, 5, 0, b"seg1a", SegmentType.FMOD),
            StageSegment(1, 8, 5, 0, b"seg2b", SegmentType.PNG),
            StageSegment(2, 16, 5, 0, b"seg3c", SegmentType.DDS),
            StageSegment(3, 24, 5, 99, b"seg4d", SegmentType.OGG),
        ]
        builders = segments_to_builders(segments)

        self.assertEqual(len(builders), 4)
        self.assertEqual(builders[3].unknown, 99)


class TestBuildCompressedSegment(unittest.TestCase):
    """Test build_compressed_segment function."""

    def test_uncompressed_segment(self):
        """Test building uncompressed segment."""
        data = b"FMOD" + b"\x00" * 20
        segment = build_compressed_segment(data, compress=False)

        self.assertEqual(segment.data, data)
        self.assertEqual(segment.segment_type, SegmentType.FMOD)

    def test_compressed_segment(self):
        """Test building compressed segment."""
        data = b"FMOD" + b"\x00" * 20
        segment = build_compressed_segment(data, compress=True)

        # Should be JKR type
        self.assertEqual(segment.segment_type, SegmentType.JKR)
        # Should start with JKR magic
        magic = struct.unpack("<I", segment.data[:4])[0]
        self.assertEqual(magic, JKR_MAGIC)


class TestContainerValidity(unittest.TestCase):
    """Test that built containers are structurally valid."""

    def test_container_is_parseable(self):
        """Test that built containers can be parsed back."""
        segments = [
            StageSegmentBuilder(data=b"FMOD" + b"\x00" * 100),
            StageSegmentBuilder(data=b"\x89PNG" + b"\x00" * 50),
        ]
        container = build_stage_container(segments)

        # Should be parseable
        parsed = parse_stage_container(container)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0].data[:4], b"FMOD")
        self.assertEqual(parsed[1].data[:4], b"\x89PNG")

    def test_container_structure(self):
        """Test container header structure."""
        import struct
        segments = [
            StageSegmentBuilder(data=b"TEST" * 10),
        ]
        container = build_stage_container(segments)

        # First 8 bytes should be offset and size of segment 0
        offset, size = struct.unpack("<II", container[:8])
        self.assertGreater(offset, 0)
        self.assertEqual(size, 40)  # "TEST" * 10 = 40 bytes


if __name__ == "__main__":
    unittest.main()
