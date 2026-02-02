# -*- coding: utf-8 -*-
"""Unit tests for fmot motion file export."""

import struct
import unittest

from mhfrontier.export.blender_extractor import (
    ExtractedKeyframe,
    ExtractedChannel,
    ExtractedBoneAnimation,
    ExtractedMotion,
    MotionExtractor,
    BLENDER_TO_FRONTIER_CHANNEL,
)
from mhfrontier.export.fmot_export import (
    serialize_keyframe,
    build_keyframe_block,
    build_bone_group_block,
    build_animation_block,
    build_fmot_file,
    _clamp_int16,
)
from mhfrontier.fmod.fmot import (
    ChannelType,
    BLOCK_ANIMATION_HEADER,
    BLOCK_KEYFRAME_TYPE,
    load_motion_from_bytes,
)


class TestClampInt16(unittest.TestCase):
    """Test int16 clamping function."""

    def test_clamp_within_range(self):
        """Test values within int16 range are unchanged."""
        self.assertEqual(_clamp_int16(0.0), 0)
        self.assertEqual(_clamp_int16(100.0), 100)
        self.assertEqual(_clamp_int16(-100.0), -100)
        self.assertEqual(_clamp_int16(32767.0), 32767)
        self.assertEqual(_clamp_int16(-32768.0), -32768)

    def test_clamp_overflow(self):
        """Test values above max are clamped."""
        self.assertEqual(_clamp_int16(32768.0), 32767)
        self.assertEqual(_clamp_int16(100000.0), 32767)

    def test_clamp_underflow(self):
        """Test values below min are clamped."""
        self.assertEqual(_clamp_int16(-32769.0), -32768)
        self.assertEqual(_clamp_int16(-100000.0), -32768)

    def test_clamp_rounding(self):
        """Test float values are rounded to nearest int."""
        self.assertEqual(_clamp_int16(10.4), 10)
        self.assertEqual(_clamp_int16(10.5), 10)  # Python rounds to even
        self.assertEqual(_clamp_int16(10.6), 11)
        self.assertEqual(_clamp_int16(11.5), 12)


class TestSerializeKeyframe(unittest.TestCase):
    """Test keyframe serialization."""

    def test_serialize_simple_keyframe(self):
        """Test serializing a simple keyframe."""
        kf = ExtractedKeyframe(frame=10, value=100.0)
        data = serialize_keyframe(kf)

        # Should be 8 bytes
        self.assertEqual(len(data), 8)

        # Unpack and verify
        tan_in, tan_out, value, frame = struct.unpack("<hhHH", data)
        self.assertEqual(tan_in, 0)
        self.assertEqual(tan_out, 0)
        self.assertEqual(value, 100)
        self.assertEqual(frame, 10)

    def test_serialize_keyframe_with_tangents(self):
        """Test serializing keyframe with tangent values."""
        kf = ExtractedKeyframe(
            frame=20,
            value=500.0,
            tangent_in=-50.0,
            tangent_out=75.0,
        )
        data = serialize_keyframe(kf)

        tan_in, tan_out, value, frame = struct.unpack("<hhHH", data)
        self.assertEqual(tan_in, -50)
        self.assertEqual(tan_out, 75)
        self.assertEqual(value, 500)
        self.assertEqual(frame, 20)

    def test_serialize_keyframe_clamping(self):
        """Test values are clamped to valid range."""
        kf = ExtractedKeyframe(
            frame=0,
            value=50000.0,  # Above int16 max
            tangent_in=-50000.0,  # Below int16 min
            tangent_out=50000.0,
        )
        data = serialize_keyframe(kf)

        tan_in, tan_out, value, frame = struct.unpack("<hhHH", data)
        self.assertEqual(tan_in, -32768)
        self.assertEqual(tan_out, 32767)
        self.assertEqual(value, 32767)


class TestBuildKeyframeBlock(unittest.TestCase):
    """Test keyframe block building."""

    def test_build_single_keyframe_block(self):
        """Test building block with single keyframe."""
        channel = ExtractedChannel(
            channel_type=ChannelType.POSITION_X,
            keyframes=[ExtractedKeyframe(frame=0, value=100.0)],
        )
        data = build_keyframe_block(channel)

        # Header (8 bytes) + 1 keyframe (8 bytes) = 16 bytes
        self.assertEqual(len(data), 16)

        # Verify header
        block_type, count, padding = struct.unpack_from("<IHH", data, 0)
        expected_type = BLOCK_KEYFRAME_TYPE | ChannelType.POSITION_X
        self.assertEqual(block_type, expected_type)
        self.assertEqual(count, 1)
        self.assertEqual(padding, 0)

    def test_build_multiple_keyframe_block(self):
        """Test building block with multiple keyframes."""
        channel = ExtractedChannel(
            channel_type=ChannelType.ROTATION_Y,
            keyframes=[
                ExtractedKeyframe(frame=0, value=0.0),
                ExtractedKeyframe(frame=30, value=16384.0),
                ExtractedKeyframe(frame=60, value=0.0),
            ],
        )
        data = build_keyframe_block(channel)

        # Header (8 bytes) + 3 keyframes (24 bytes) = 32 bytes
        self.assertEqual(len(data), 32)

        # Verify count in header
        count = struct.unpack_from("<H", data, 4)[0]
        self.assertEqual(count, 3)


class TestBuildBoneGroupBlock(unittest.TestCase):
    """Test bone group block building."""

    def test_build_bone_group(self):
        """Test building a bone group header."""
        data = build_bone_group_block(5)

        # Should be 8 bytes
        self.assertEqual(len(data), 8)

        # Verify block type
        block_type, padding = struct.unpack("<II", data)
        expected_type = 0x80000000 | 5
        self.assertEqual(block_type, expected_type)
        self.assertEqual(padding, 0)


class TestBuildAnimationBlock(unittest.TestCase):
    """Test animation block building."""

    def test_build_empty_animation(self):
        """Test building animation with no bones."""
        motion = ExtractedMotion(
            name="EmptyMotion",
            frame_count=0,
            bone_animations={},
        )
        data = build_animation_block(motion)

        self.assertEqual(len(data), 0)

    def test_build_single_bone_animation(self):
        """Test building animation with one bone."""
        motion = ExtractedMotion(
            name="SingleBone",
            frame_count=30,
            bone_animations={
                1: ExtractedBoneAnimation(
                    bone_id=1,
                    channels={
                        ChannelType.POSITION_X: ExtractedChannel(
                            channel_type=ChannelType.POSITION_X,
                            keyframes=[ExtractedKeyframe(frame=0, value=0.0)],
                        ),
                    },
                ),
            },
        )
        data = build_animation_block(motion)

        # Bone group (8) + keyframe block (16) = 24 bytes
        self.assertEqual(len(data), 24)


class TestBuildFmotFile(unittest.TestCase):
    """Test complete FMOT file building."""

    def test_build_simple_file(self):
        """Test building a simple FMOT file."""
        motion = ExtractedMotion(
            name="TestMotion",
            frame_count=30,
            bone_animations={
                0: ExtractedBoneAnimation(
                    bone_id=0,
                    channels={
                        ChannelType.POSITION_X: ExtractedChannel(
                            channel_type=ChannelType.POSITION_X,
                            keyframes=[
                                ExtractedKeyframe(frame=0, value=0.0),
                                ExtractedKeyframe(frame=30, value=100.0),
                            ],
                        ),
                    },
                ),
            },
        )
        data = build_fmot_file(motion)

        # Header (16) + bone group (8) + keyframe block (8 + 16) = 48 bytes
        self.assertEqual(len(data), 48)

        # Verify header
        header_type = struct.unpack_from("<I", data, 0)[0]
        self.assertEqual(header_type, BLOCK_ANIMATION_HEADER)


class TestRoundTripConsistency(unittest.TestCase):
    """Test round-trip export/import consistency."""

    def test_roundtrip_simple_motion(self):
        """Test exporting and re-importing motion data."""
        # Create motion data
        original = ExtractedMotion(
            name="RoundTrip",
            frame_count=60,
            bone_animations={
                0: ExtractedBoneAnimation(
                    bone_id=0,
                    channels={
                        ChannelType.POSITION_X: ExtractedChannel(
                            channel_type=ChannelType.POSITION_X,
                            keyframes=[
                                ExtractedKeyframe(frame=0, value=0.0),
                                ExtractedKeyframe(frame=30, value=500.0),
                                ExtractedKeyframe(frame=60, value=0.0),
                            ],
                        ),
                        ChannelType.ROTATION_Y: ExtractedChannel(
                            channel_type=ChannelType.ROTATION_Y,
                            keyframes=[
                                ExtractedKeyframe(frame=0, value=0.0),
                                ExtractedKeyframe(frame=60, value=16384.0),
                            ],
                        ),
                    },
                ),
            },
        )

        # Export to bytes
        exported = build_fmot_file(original)

        # Re-import
        reimported = load_motion_from_bytes(exported)

        # Verify structure is preserved
        self.assertEqual(len(reimported.bone_animations), 1)
        self.assertIn(0, reimported.bone_animations)

        bone = reimported.bone_animations[0]
        self.assertIn(ChannelType.POSITION_X, bone.channels)
        self.assertIn(ChannelType.ROTATION_Y, bone.channels)

        # Verify position X keyframes
        pos_x = bone.channels[ChannelType.POSITION_X]
        self.assertEqual(len(pos_x.keyframes), 3)
        self.assertEqual(pos_x.keyframes[0].frame, 0)
        self.assertAlmostEqual(pos_x.keyframes[0].value, 0.0, places=0)
        self.assertEqual(pos_x.keyframes[1].frame, 30)
        self.assertAlmostEqual(pos_x.keyframes[1].value, 500.0, places=0)

        # Verify rotation Y keyframes
        rot_y = bone.channels[ChannelType.ROTATION_Y]
        self.assertEqual(len(rot_y.keyframes), 2)
        self.assertAlmostEqual(rot_y.keyframes[1].value, 16384.0, places=0)

    def test_roundtrip_multiple_bones(self):
        """Test round-trip with multiple bones."""
        original = ExtractedMotion(
            name="MultiBone",
            frame_count=30,
            bone_animations={
                0: ExtractedBoneAnimation(
                    bone_id=0,
                    channels={
                        ChannelType.POSITION_X: ExtractedChannel(
                            channel_type=ChannelType.POSITION_X,
                            keyframes=[ExtractedKeyframe(frame=0, value=100.0)],
                        ),
                    },
                ),
                1: ExtractedBoneAnimation(
                    bone_id=1,
                    channels={
                        ChannelType.POSITION_Y: ExtractedChannel(
                            channel_type=ChannelType.POSITION_Y,
                            keyframes=[ExtractedKeyframe(frame=0, value=200.0)],
                        ),
                    },
                ),
                2: ExtractedBoneAnimation(
                    bone_id=2,
                    channels={
                        ChannelType.POSITION_Z: ExtractedChannel(
                            channel_type=ChannelType.POSITION_Z,
                            keyframes=[ExtractedKeyframe(frame=0, value=300.0)],
                        ),
                    },
                ),
            },
        )

        exported = build_fmot_file(original)
        reimported = load_motion_from_bytes(exported)

        # All bones should be present
        self.assertEqual(len(reimported.bone_animations), 3)
        self.assertIn(0, reimported.bone_animations)
        self.assertIn(1, reimported.bone_animations)
        self.assertIn(2, reimported.bone_animations)

    def test_roundtrip_with_tangents(self):
        """Test round-trip preserves tangent values."""
        original = ExtractedMotion(
            name="Tangents",
            frame_count=30,
            bone_animations={
                0: ExtractedBoneAnimation(
                    bone_id=0,
                    channels={
                        ChannelType.POSITION_X: ExtractedChannel(
                            channel_type=ChannelType.POSITION_X,
                            keyframes=[
                                ExtractedKeyframe(
                                    frame=0,
                                    value=0.0,
                                    tangent_in=-100.0,
                                    tangent_out=100.0,
                                ),
                                ExtractedKeyframe(
                                    frame=30,
                                    value=500.0,
                                    tangent_in=50.0,
                                    tangent_out=-50.0,
                                ),
                            ],
                        ),
                    },
                ),
            },
        )

        exported = build_fmot_file(original)
        reimported = load_motion_from_bytes(exported)

        channel = reimported.bone_animations[0].channels[ChannelType.POSITION_X]

        # Verify tangents are preserved
        self.assertEqual(len(channel.keyframes), 2)
        self.assertAlmostEqual(channel.keyframes[0].tangent_in, -100.0, places=0)
        self.assertAlmostEqual(channel.keyframes[0].tangent_out, 100.0, places=0)
        self.assertAlmostEqual(channel.keyframes[1].tangent_in, 50.0, places=0)
        self.assertAlmostEqual(channel.keyframes[1].tangent_out, -50.0, places=0)


class TestBlenderToFrontierChannelMapping(unittest.TestCase):
    """Test the Blender to Frontier channel mapping."""

    def test_position_mapping(self):
        """Test position channels are mapped correctly."""
        # Blender X -> Frontier X
        self.assertEqual(
            BLENDER_TO_FRONTIER_CHANNEL[("location", 0)],
            ChannelType.POSITION_X,
        )
        # Blender Y -> Frontier Z (Y/Z swap)
        self.assertEqual(
            BLENDER_TO_FRONTIER_CHANNEL[("location", 1)],
            ChannelType.POSITION_Z,
        )
        # Blender Z -> Frontier Y (Y/Z swap)
        self.assertEqual(
            BLENDER_TO_FRONTIER_CHANNEL[("location", 2)],
            ChannelType.POSITION_Y,
        )

    def test_rotation_mapping(self):
        """Test rotation channels are mapped correctly."""
        self.assertEqual(
            BLENDER_TO_FRONTIER_CHANNEL[("rotation_euler", 0)],
            ChannelType.ROTATION_X,
        )
        self.assertEqual(
            BLENDER_TO_FRONTIER_CHANNEL[("rotation_euler", 1)],
            ChannelType.ROTATION_Z,
        )
        self.assertEqual(
            BLENDER_TO_FRONTIER_CHANNEL[("rotation_euler", 2)],
            ChannelType.ROTATION_Y,
        )

    def test_scale_mapping(self):
        """Test scale channels are mapped correctly."""
        self.assertEqual(
            BLENDER_TO_FRONTIER_CHANNEL[("scale", 0)],
            ChannelType.SCALE_X,
        )
        self.assertEqual(
            BLENDER_TO_FRONTIER_CHANNEL[("scale", 1)],
            ChannelType.SCALE_Z,
        )
        self.assertEqual(
            BLENDER_TO_FRONTIER_CHANNEL[("scale", 2)],
            ChannelType.SCALE_Y,
        )


class TestExtractedDataClasses(unittest.TestCase):
    """Test the extracted motion data classes."""

    def test_extracted_keyframe_defaults(self):
        """Test ExtractedKeyframe default values."""
        kf = ExtractedKeyframe(frame=10, value=50.0)
        self.assertEqual(kf.frame, 10)
        self.assertEqual(kf.value, 50.0)
        self.assertEqual(kf.tangent_in, 0.0)
        self.assertEqual(kf.tangent_out, 0.0)

    def test_extracted_channel(self):
        """Test ExtractedChannel initialization."""
        channel = ExtractedChannel(channel_type=ChannelType.POSITION_X)
        self.assertEqual(channel.channel_type, ChannelType.POSITION_X)
        self.assertEqual(len(channel.keyframes), 0)

    def test_extracted_bone_animation(self):
        """Test ExtractedBoneAnimation initialization."""
        bone_anim = ExtractedBoneAnimation(bone_id=5)
        self.assertEqual(bone_anim.bone_id, 5)
        self.assertEqual(len(bone_anim.channels), 0)

    def test_extracted_motion(self):
        """Test ExtractedMotion initialization."""
        motion = ExtractedMotion(name="Test", frame_count=60)
        self.assertEqual(motion.name, "Test")
        self.assertEqual(motion.frame_count, 60)
        self.assertEqual(len(motion.bone_animations), 0)


class TestMotionExtractorHelpers(unittest.TestCase):
    """Test MotionExtractor helper methods."""

    def test_extract_bone_id_standard(self):
        """Test extracting bone ID from standard path."""
        extractor = MotionExtractor()

        bone_id = extractor._extract_bone_id('pose.bones["Bone.001"].location')
        self.assertEqual(bone_id, 1)

        bone_id = extractor._extract_bone_id('pose.bones["Bone.042"].rotation_euler')
        self.assertEqual(bone_id, 42)

        bone_id = extractor._extract_bone_id('pose.bones["Bone.123"].scale')
        self.assertEqual(bone_id, 123)

    def test_extract_bone_id_numeric(self):
        """Test extracting bone ID from numeric-only path."""
        extractor = MotionExtractor()

        bone_id = extractor._extract_bone_id('pose.bones["5"].location')
        self.assertEqual(bone_id, 5)

    def test_extract_bone_id_invalid(self):
        """Test invalid paths return None."""
        extractor = MotionExtractor()

        bone_id = extractor._extract_bone_id("location")
        self.assertIsNone(bone_id)

        bone_id = extractor._extract_bone_id('object["property"]')
        self.assertIsNone(bone_id)

    def test_extract_property_name(self):
        """Test property name extraction."""
        extractor = MotionExtractor()

        self.assertEqual(
            extractor._extract_property_name('pose.bones["Bone.001"].location'),
            "location",
        )
        self.assertEqual(
            extractor._extract_property_name('pose.bones["Bone.001"].rotation_euler'),
            "rotation_euler",
        )
        self.assertEqual(
            extractor._extract_property_name('pose.bones["Bone.001"].scale'),
            "scale",
        )
        self.assertIsNone(
            extractor._extract_property_name('pose.bones["Bone.001"].custom_prop')
        )

    def test_get_transform_type(self):
        """Test transform type mapping."""
        extractor = MotionExtractor()

        self.assertEqual(extractor._get_transform_type("location"), "position")
        self.assertEqual(extractor._get_transform_type("rotation_euler"), "rotation")
        self.assertEqual(extractor._get_transform_type("scale"), "scale")
        self.assertEqual(extractor._get_transform_type("unknown"), "unknown")


class TestMotionExtractorTransforms(unittest.TestCase):
    """Test MotionExtractor value transformation methods."""

    def test_transform_position_value(self):
        """Test position value transformation (Blender to Frontier)."""
        extractor = MotionExtractor()

        # Blender 1.0 with EXPORT_SCALE=100 -> Frontier 100
        result = extractor._transform_value(1.0, "position")
        self.assertAlmostEqual(result, 100.0, places=2)

        # Blender 0.5 -> Frontier 50
        result = extractor._transform_value(0.5, "position")
        self.assertAlmostEqual(result, 50.0, places=2)

    def test_transform_rotation_value(self):
        """Test rotation value transformation."""
        import math

        extractor = MotionExtractor()

        # pi radians -> 32768
        result = extractor._transform_value(math.pi, "rotation")
        self.assertAlmostEqual(result, 32768.0, places=0)

        # -pi radians -> -32768
        result = extractor._transform_value(-math.pi, "rotation")
        self.assertAlmostEqual(result, -32768.0, places=0)

        # pi/2 radians -> 16384
        result = extractor._transform_value(math.pi / 2, "rotation")
        self.assertAlmostEqual(result, 16384.0, places=0)

    def test_transform_scale_value(self):
        """Test scale value transformation."""
        extractor = MotionExtractor()

        # Blender 1.0 (no scale) -> Frontier 0
        result = extractor._transform_value(1.0, "scale")
        self.assertAlmostEqual(result, 0.0, places=2)

        # Blender 2.0 (double) -> Frontier 32768
        result = extractor._transform_value(2.0, "scale")
        self.assertAlmostEqual(result, 32768.0, places=0)

        # Blender 0.5 (half) -> Frontier -16384
        result = extractor._transform_value(0.5, "scale")
        self.assertAlmostEqual(result, -16384.0, places=0)


if __name__ == "__main__":
    unittest.main()
