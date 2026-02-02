# -*- coding: utf-8 -*-
"""Unit tests for fmot motion file parsing and import."""

import struct
import unittest
from dataclasses import dataclass

from mhfrontier.blender.mock_impl import (
    MockAnimationBuilder,
    MockAction,
    MockFCurve,
    MockObject,
)
from mhfrontier.blender.builders import get_mock_builders
from mhfrontier.fmod import fmot
from mhfrontier.fmod.fmot import (
    ChannelType,
    Keyframe,
    ChannelAnimation,
    BoneAnimation,
    MotionData,
)
from mhfrontier.importers import motion as motion_importer


class TestKeyframeDataClass(unittest.TestCase):
    """Test Keyframe data class."""

    def test_keyframe_defaults(self):
        """Test keyframe with default tangents."""
        kf = Keyframe(frame=10, value=100.0)

        self.assertEqual(kf.frame, 10)
        self.assertEqual(kf.value, 100.0)
        self.assertEqual(kf.tangent_in, 0.0)
        self.assertEqual(kf.tangent_out, 0.0)

    def test_keyframe_with_tangents(self):
        """Test keyframe with explicit tangents."""
        kf = Keyframe(frame=20, value=50.5, tangent_in=-10.0, tangent_out=15.0)

        self.assertEqual(kf.frame, 20)
        self.assertEqual(kf.value, 50.5)
        self.assertEqual(kf.tangent_in, -10.0)
        self.assertEqual(kf.tangent_out, 15.0)


class TestChannelAnimation(unittest.TestCase):
    """Test ChannelAnimation data class."""

    def test_empty_channel(self):
        """Test channel with no keyframes."""
        channel = ChannelAnimation(channel_type=ChannelType.POSITION_X)

        self.assertEqual(channel.channel_type, ChannelType.POSITION_X)
        self.assertEqual(len(channel.keyframes), 0)

    def test_channel_with_keyframes(self):
        """Test channel with multiple keyframes."""
        channel = ChannelAnimation(
            channel_type=ChannelType.ROTATION_Y,
            keyframes=[
                Keyframe(frame=0, value=0.0),
                Keyframe(frame=30, value=180.0),
                Keyframe(frame=60, value=0.0),
            ],
        )

        self.assertEqual(channel.channel_type, ChannelType.ROTATION_Y)
        self.assertEqual(len(channel.keyframes), 3)
        self.assertEqual(channel.keyframes[1].value, 180.0)


class TestBoneAnimation(unittest.TestCase):
    """Test BoneAnimation data class."""

    def test_bone_with_channels(self):
        """Test bone animation with multiple channels."""
        bone_anim = BoneAnimation(
            bone_id=42,
            channels={
                ChannelType.POSITION_X: ChannelAnimation(
                    channel_type=ChannelType.POSITION_X,
                    keyframes=[Keyframe(frame=0, value=0.0)],
                ),
                ChannelType.POSITION_Y: ChannelAnimation(
                    channel_type=ChannelType.POSITION_Y,
                    keyframes=[Keyframe(frame=0, value=10.0)],
                ),
            },
        )

        self.assertEqual(bone_anim.bone_id, 42)
        self.assertEqual(len(bone_anim.channels), 2)
        self.assertIn(ChannelType.POSITION_X, bone_anim.channels)


class TestMotionData(unittest.TestCase):
    """Test MotionData data class."""

    def test_empty_motion(self):
        """Test empty motion data."""
        motion = MotionData()

        self.assertEqual(motion.frame_count, 0)
        self.assertEqual(len(motion.bone_animations), 0)
        self.assertEqual(motion.name, "")

    def test_motion_with_data(self):
        """Test motion with bone animations."""
        motion = MotionData(
            frame_count=60,
            name="test_motion",
            bone_animations={
                0: BoneAnimation(bone_id=0),
                1: BoneAnimation(bone_id=1),
            },
        )

        self.assertEqual(motion.frame_count, 60)
        self.assertEqual(motion.name, "test_motion")
        self.assertEqual(len(motion.bone_animations), 2)


class TestLoadMotionFromBytes(unittest.TestCase):
    """Test loading motion data from bytes."""

    def test_empty_data(self):
        """Test with empty data returns empty motion."""
        motion = fmot.load_motion_from_bytes(b"")

        self.assertEqual(motion.frame_count, 0)
        self.assertEqual(len(motion.bone_animations), 0)

    def test_invalid_data(self):
        """Test with random invalid data returns empty motion."""
        motion = fmot.load_motion_from_bytes(b"\x00\x01\x02\x03")

        self.assertEqual(len(motion.bone_animations), 0)


class TestChannelToPropertyInfo(unittest.TestCase):
    """Test channel type to Blender property mapping."""

    def test_position_channels(self):
        """Test position channel mapping with axis swap."""
        # X stays X
        prop, idx, ttype = motion_importer._channel_to_property_info(
            ChannelType.POSITION_X
        )
        self.assertEqual(prop, "location")
        self.assertEqual(idx, 0)
        self.assertEqual(ttype, "position")

        # Y becomes Z (index 2)
        prop, idx, ttype = motion_importer._channel_to_property_info(
            ChannelType.POSITION_Y
        )
        self.assertEqual(prop, "location")
        self.assertEqual(idx, 2)
        self.assertEqual(ttype, "position")

        # Z becomes Y (index 1)
        prop, idx, ttype = motion_importer._channel_to_property_info(
            ChannelType.POSITION_Z
        )
        self.assertEqual(prop, "location")
        self.assertEqual(idx, 1)
        self.assertEqual(ttype, "position")

    def test_rotation_channels(self):
        """Test rotation channel mapping with axis swap."""
        prop, idx, ttype = motion_importer._channel_to_property_info(
            ChannelType.ROTATION_X
        )
        self.assertEqual(prop, "rotation_euler")
        self.assertEqual(idx, 0)
        self.assertEqual(ttype, "rotation")

        prop, idx, ttype = motion_importer._channel_to_property_info(
            ChannelType.ROTATION_Y
        )
        self.assertEqual(prop, "rotation_euler")
        self.assertEqual(idx, 2)  # Y -> Z
        self.assertEqual(ttype, "rotation")

    def test_scale_channels(self):
        """Test scale channel mapping."""
        prop, idx, ttype = motion_importer._channel_to_property_info(
            ChannelType.SCALE_X
        )
        self.assertEqual(prop, "scale")
        self.assertEqual(idx, 0)
        self.assertEqual(ttype, "scale")

    def test_unknown_channel(self):
        """Test unknown channel returns None."""
        prop, idx, ttype = motion_importer._channel_to_property_info(0x9999)
        self.assertIsNone(prop)
        self.assertEqual(ttype, "unknown")


class TestTransformValue(unittest.TestCase):
    """Test value transformation."""

    def test_position_scaling(self):
        """Test position values are scaled by IMPORT_SCALE."""
        # IMPORT_SCALE is 0.01, so 100 -> 1.0
        result = motion_importer._transform_value(100.0, "position", 0)
        self.assertAlmostEqual(result, 1.0, places=5)

    def test_rotation_scaling(self):
        """Test rotation values are converted to radians."""
        import math

        # 32768 should map to pi
        result = motion_importer._transform_value(32768.0, "rotation", 0)
        self.assertAlmostEqual(result, math.pi, places=5)

        # -32768 should map to -pi
        result = motion_importer._transform_value(-32768.0, "rotation", 0)
        self.assertAlmostEqual(result, -math.pi, places=5)


class TestMockAnimationBuilder(unittest.TestCase):
    """Test the mock animation builder."""

    def test_create_action(self):
        """Test creating an action."""
        builder = MockAnimationBuilder()
        action = builder.create_action("TestAction")

        self.assertEqual(action.name, "TestAction")
        self.assertEqual(len(action.fcurves), 0)
        self.assertIn(action, builder.created_actions)

    def test_create_fcurve(self):
        """Test creating an FCurve."""
        builder = MockAnimationBuilder()
        action = builder.create_action("TestAction")
        fcurve = builder.create_fcurve(action, 'pose.bones["Bone.001"].location', 0)

        self.assertEqual(fcurve.data_path, 'pose.bones["Bone.001"].location')
        self.assertEqual(fcurve.index, 0)
        self.assertIn(fcurve, action.fcurves)

    def test_add_keyframe(self):
        """Test adding keyframes."""
        builder = MockAnimationBuilder()
        action = builder.create_action("TestAction")
        fcurve = builder.create_fcurve(action, "location", 0)

        kf = builder.add_keyframe(fcurve, 10.0, 5.5, "BEZIER")

        self.assertEqual(kf.frame, 10.0)
        self.assertEqual(kf.value, 5.5)
        self.assertEqual(kf.interpolation, "BEZIER")
        self.assertIn(kf, fcurve.keyframe_points)

    def test_add_keyframe_with_handles(self):
        """Test adding keyframes with Bezier handles."""
        builder = MockAnimationBuilder()
        action = builder.create_action("TestAction")
        fcurve = builder.create_fcurve(action, "location", 0)

        kf = builder.add_keyframe(
            fcurve,
            10.0,
            5.5,
            "BEZIER",
            handle_left=(9.0, 5.0),
            handle_right=(11.0, 6.0),
        )

        self.assertEqual(kf.handle_left, (9.0, 5.0))
        self.assertEqual(kf.handle_right, (11.0, 6.0))

    def test_set_frame_range(self):
        """Test setting action frame range."""
        builder = MockAnimationBuilder()
        action = builder.create_action("TestAction")

        builder.set_action_frame_range(action, 0, 60)

        self.assertEqual(action.frame_start, 0)
        self.assertEqual(action.frame_end, 60)


class TestImportMotionWithMock(unittest.TestCase):
    """Test motion import using mock builders."""

    def test_import_empty_motion(self):
        """Test importing motion with no bone data."""
        builders = get_mock_builders()

        # Create a mock armature-like object
        @dataclass
        class MockArmature:
            name: str = "TestArmature"
            pose: None = None

        armature = MockArmature()

        # Import empty bytes
        action = motion_importer.import_motion_from_bytes(
            b"", armature, "EmptyMotion", builders
        )

        # Should return None for empty motion
        self.assertIsNone(action)

    def test_import_creates_action(self):
        """Test that import creates action when given valid motion data."""
        builders = get_mock_builders()

        # Create motion data manually
        motion = MotionData(
            frame_count=30,
            name="TestMotion",
            bone_animations={
                1: BoneAnimation(
                    bone_id=1,
                    channels={
                        ChannelType.POSITION_X: ChannelAnimation(
                            channel_type=ChannelType.POSITION_X,
                            keyframes=[
                                Keyframe(frame=0, value=0.0),
                                Keyframe(frame=30, value=100.0),
                            ],
                        ),
                    },
                ),
            },
        )

        # Directly create action using builder to test builder works
        action = builders.animation.create_action("TestMotion")
        fcurve = builders.animation.create_fcurve(action, 'pose.bones["Bone.001"].location', 0)
        builders.animation.add_keyframe(fcurve, 0.0, 0.0)
        builders.animation.add_keyframe(fcurve, 30.0, 1.0)  # 100 * 0.01 scale
        builders.animation.set_action_frame_range(action, 0, 29)

        self.assertEqual(len(builders.animation.created_actions), 1)
        self.assertEqual(action.name, "TestMotion")
        self.assertEqual(len(action.fcurves), 1)
        self.assertEqual(len(action.fcurves[0].keyframe_points), 2)


class TestBezierHandleCalculation(unittest.TestCase):
    """Test Bezier handle calculation."""

    def test_zero_tangents(self):
        """Test handle calculation with zero tangents."""
        left, right = motion_importer._calculate_bezier_handles(
            frame=10.0,
            value=5.0,
            tangent_in=0.0,
            tangent_out=0.0,
            transform_type="position",
        )

        # With zero tangents, handles should be at the value level
        self.assertAlmostEqual(left[1], 5.0, places=5)
        self.assertAlmostEqual(right[1], 5.0, places=5)

    def test_nonzero_tangents(self):
        """Test handle calculation with non-zero tangents."""
        left, right = motion_importer._calculate_bezier_handles(
            frame=10.0,
            value=5.0,
            tangent_in=100.0,  # Slope going up coming in
            tangent_out=100.0,  # Slope going up going out
            transform_type="position",
        )

        # Handle distance is 1/3 frame
        # Left handle should be lower (we're coming up to the point)
        self.assertLess(left[1], 5.0)
        # Right handle should be higher (we're continuing up)
        self.assertGreater(right[1], 5.0)


if __name__ == "__main__":
    unittest.main()
