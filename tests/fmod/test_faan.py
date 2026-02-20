# -*- coding: utf-8 -*-
"""Unit tests for AAN animation file parsing and import."""

import math
import struct
import unittest
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from mhfrontier.blender.mock_impl import (
    MockAnimationBuilder,
    MockAction,
    MockFCurve,
    MockObject,
)
from mhfrontier.blender.builders import get_mock_builders
from mhfrontier.config import AAN_SHORT_ROTATION_SCALE, AAN_SHORT_LOCATION_SCALE
from mhfrontier.fmod import faan
from mhfrontier.fmod.faan import (
    AANChannelFlag,
    AANKeyframeType,
    AANKeyframe,
    AANChannel,
    AANBoneTrack,
    AANMotion,
    AANPart,
    AANData,
    _parse_keyframes,
    _parse_component,
    _parse_motion,
)
from mhfrontier.importers import aan as aan_importer


# =============================================================================
# Parser Data Class Tests
# =============================================================================


class TestAANKeyframeDataClass(unittest.TestCase):
    """Test AANKeyframe data class."""

    def test_defaults(self):
        kf = AANKeyframe(frame=10, value=1.5)
        self.assertEqual(kf.frame, 10)
        self.assertEqual(kf.value, 1.5)
        self.assertEqual(kf.tangent_in, 0.0)
        self.assertEqual(kf.tangent_out, 0.0)
        self.assertEqual(kf.interpolation, "LINEAR")

    def test_with_tangents(self):
        kf = AANKeyframe(
            frame=5, value=2.0, tangent_in=-1.0, tangent_out=1.0,
            interpolation="BEZIER",
        )
        self.assertEqual(kf.tangent_in, -1.0)
        self.assertEqual(kf.tangent_out, 1.0)
        self.assertEqual(kf.interpolation, "BEZIER")


class TestAANChannelDataClass(unittest.TestCase):
    """Test AANChannel data class."""

    def test_empty_channel(self):
        ch = AANChannel(channel_flag=AANChannelFlag.ROTATION_X)
        self.assertEqual(ch.channel_flag, AANChannelFlag.ROTATION_X)
        self.assertEqual(len(ch.keyframes), 0)

    def test_channel_with_keyframes(self):
        ch = AANChannel(
            channel_flag=AANChannelFlag.LOCATION_Y,
            keyframes=[AANKeyframe(frame=0, value=0.0), AANKeyframe(frame=10, value=5.0)],
        )
        self.assertEqual(len(ch.keyframes), 2)


class TestAANMotionDataClass(unittest.TestCase):
    """Test AANMotion data class."""

    def test_defaults(self):
        m = AANMotion()
        self.assertEqual(m.frame_count, 0)
        self.assertEqual(m.loop_flag, 0)
        self.assertEqual(m.loop_start_frame, 0)
        self.assertEqual(len(m.bone_tracks), 0)


class TestAANDataClass(unittest.TestCase):
    """Test AANData data class."""

    def test_defaults(self):
        d = AANData()
        self.assertEqual(len(d.parts), 0)
        self.assertEqual(d.name, "")


# =============================================================================
# Parser Keyframe Tests
# =============================================================================


class TestParseKeyframes(unittest.TestCase):
    """Test _parse_keyframes for all 6 encoding types."""

    def test_linear_short(self):
        """LinearShort: 4 bytes per keyframe (uint16 frame, int16 value)."""
        frame = 5
        raw_value = 4096  # rotation
        data = struct.pack("<Hh", frame, raw_value)
        kfs = _parse_keyframes(
            data, 0, AANKeyframeType.LINEAR_SHORT, 1, AANChannelFlag.ROTATION_X,
        )
        self.assertEqual(len(kfs), 1)
        self.assertEqual(kfs[0].frame, 5)
        self.assertAlmostEqual(kfs[0].value, 4096 * AAN_SHORT_ROTATION_SCALE, places=6)
        self.assertEqual(kfs[0].interpolation, "LINEAR")

    def test_linear_short_location(self):
        """LinearShort for location channel."""
        raw_value = 160  # 160 / 16.0 = 10.0
        data = struct.pack("<Hh", 0, raw_value)
        kfs = _parse_keyframes(
            data, 0, AANKeyframeType.LINEAR_SHORT, 1, AANChannelFlag.LOCATION_X,
        )
        self.assertEqual(len(kfs), 1)
        self.assertAlmostEqual(kfs[0].value, 10.0, places=6)

    def test_hermite_short(self):
        """HermiteShort: 8 bytes (frame, value, tangent_in, tangent_out)."""
        data = struct.pack("<Hhhh", 10, 2000, -500, 500)
        kfs = _parse_keyframes(
            data, 0, AANKeyframeType.HERMITE_SHORT, 1, AANChannelFlag.ROTATION_Z,
        )
        self.assertEqual(len(kfs), 1)
        self.assertEqual(kfs[0].frame, 10)
        self.assertAlmostEqual(kfs[0].value, 2000 * AAN_SHORT_ROTATION_SCALE, places=6)
        self.assertAlmostEqual(kfs[0].tangent_in, -500 * AAN_SHORT_ROTATION_SCALE, places=6)
        self.assertEqual(kfs[0].interpolation, "BEZIER")

    def test_complex_short_linear(self):
        """ComplexShort with LINEAR flag."""
        frame_flags = 7 | 0x10000  # frame=7, LINEAR flag
        data = struct.pack("<Ihh", frame_flags, 1000, 200)
        kfs = _parse_keyframes(
            data, 0, AANKeyframeType.COMPLEX_SHORT, 1, AANChannelFlag.ROTATION_Y,
        )
        self.assertEqual(len(kfs), 1)
        self.assertEqual(kfs[0].frame, 7)
        self.assertEqual(kfs[0].interpolation, "LINEAR")

    def test_complex_short_bezier(self):
        """ComplexShort with BEZIER flag."""
        frame_flags = 3 | 0x20000  # frame=3, BEZIER flag
        data = struct.pack("<Ihh", frame_flags, 800, 100)
        kfs = _parse_keyframes(
            data, 0, AANKeyframeType.COMPLEX_SHORT, 1, AANChannelFlag.ROTATION_X,
        )
        self.assertEqual(len(kfs), 1)
        self.assertEqual(kfs[0].frame, 3)
        self.assertEqual(kfs[0].interpolation, "BEZIER")

    def test_linear_float(self):
        """LinearFloat: 8 bytes (uint16 frame, 2 pad, float value)."""
        data = struct.pack("<HHf", 15, 0, 3.14159)
        kfs = _parse_keyframes(
            data, 0, AANKeyframeType.LINEAR_FLOAT, 1, AANChannelFlag.ROTATION_X,
        )
        self.assertEqual(len(kfs), 1)
        self.assertEqual(kfs[0].frame, 15)
        self.assertAlmostEqual(kfs[0].value, 3.14159, places=4)
        self.assertEqual(kfs[0].interpolation, "LINEAR")

    def test_hermite_float(self):
        """HermiteFloat: 16 bytes (frame, pad, value, tan_in, tan_out)."""
        data = struct.pack("<HHfff", 20, 0, 1.0, -0.5, 0.5)
        kfs = _parse_keyframes(
            data, 0, AANKeyframeType.HERMITE_FLOAT, 1, AANChannelFlag.LOCATION_Y,
        )
        self.assertEqual(len(kfs), 1)
        self.assertEqual(kfs[0].frame, 20)
        self.assertAlmostEqual(kfs[0].value, 1.0, places=5)
        self.assertAlmostEqual(kfs[0].tangent_in, -0.5, places=5)
        self.assertAlmostEqual(kfs[0].tangent_out, 0.5, places=5)
        self.assertEqual(kfs[0].interpolation, "BEZIER")

    def test_complex_float_bezier(self):
        """ComplexFloat with BEZIER flag."""
        frame_flags = 12 | 0x20000
        data = struct.pack("<Ifff", frame_flags, 2.5, -1.0, 1.0)
        kfs = _parse_keyframes(
            data, 0, AANKeyframeType.COMPLEX_FLOAT, 1, AANChannelFlag.ROTATION_Z,
        )
        self.assertEqual(len(kfs), 1)
        self.assertEqual(kfs[0].frame, 12)
        self.assertAlmostEqual(kfs[0].value, 2.5, places=5)
        self.assertEqual(kfs[0].interpolation, "BEZIER")

    def test_complex_float_linear(self):
        """ComplexFloat with LINEAR flag."""
        frame_flags = 8 | 0x10000
        data = struct.pack("<Ifff", frame_flags, 0.0, 0.0, 0.0)
        kfs = _parse_keyframes(
            data, 0, AANKeyframeType.COMPLEX_FLOAT, 1, AANChannelFlag.LOCATION_X,
        )
        self.assertEqual(len(kfs), 1)
        self.assertEqual(kfs[0].interpolation, "LINEAR")

    def test_multiple_keyframes(self):
        """Parse multiple keyframes in sequence."""
        data = struct.pack("<Hh", 0, 0) + struct.pack("<Hh", 10, 160) + struct.pack("<Hh", 20, 320)
        kfs = _parse_keyframes(
            data, 0, AANKeyframeType.LINEAR_SHORT, 3, AANChannelFlag.LOCATION_X,
        )
        self.assertEqual(len(kfs), 3)
        self.assertEqual(kfs[0].frame, 0)
        self.assertEqual(kfs[1].frame, 10)
        self.assertEqual(kfs[2].frame, 20)
        self.assertAlmostEqual(kfs[2].value, 20.0, places=5)

    def test_unknown_type(self):
        """Unknown keyframe type returns empty list."""
        data = b"\x00" * 16
        kfs = _parse_keyframes(data, 0, 99, 1, AANChannelFlag.ROTATION_X)
        self.assertEqual(len(kfs), 0)


# =============================================================================
# Parser Component Tests
# =============================================================================


class TestParseComponent(unittest.TestCase):
    """Test _parse_component header decoding."""

    def test_component_header(self):
        """Test that channel_flag and type_id are correctly extracted."""
        channel_flag = AANChannelFlag.ROTATION_X
        type_id = AANKeyframeType.LINEAR_SHORT
        key_count = 1
        kf_data = struct.pack("<Hh", 5, 1000)
        data_size = len(kf_data)

        header = struct.pack("<HHII", channel_flag, type_id, key_count, data_size)
        data = header + kf_data

        channel, next_offset = _parse_component(data, 0)

        self.assertEqual(channel.channel_flag, AANChannelFlag.ROTATION_X)
        self.assertEqual(len(channel.keyframes), 1)
        self.assertEqual(channel.keyframes[0].frame, 5)
        self.assertEqual(next_offset, 12 + data_size)

    def test_component_truncated(self):
        """Truncated data returns empty channel."""
        channel, _ = _parse_component(b"\x00" * 4, 0)
        self.assertEqual(len(channel.keyframes), 0)


# =============================================================================
# Parser Motion Tests
# =============================================================================


class TestParseMotion(unittest.TestCase):
    """Test _parse_motion."""

    def test_minimal_motion(self):
        """Parse motion with 1 bone, 1 component, 1 keyframe."""
        # Build component: ROTATION_X, LINEAR_SHORT, 1 key
        kf_data = struct.pack("<Hh", 0, 4096)
        comp_header = struct.pack(
            "<HHII",
            AANChannelFlag.ROTATION_X,
            AANKeyframeType.LINEAR_SHORT,
            1,
            len(kf_data),
        )
        comp_data = comp_header + kf_data

        # Build bone track: 1 component
        track_header = struct.pack("<III", 1, len(comp_data), 0)
        track_data = track_header + comp_data

        # Build motion header: 1 bone, 30 frames
        motion_header = struct.pack("<IIIII", 1, 30, 0, 0, len(track_data))
        data = motion_header + track_data

        motion = _parse_motion(data, 0)

        self.assertEqual(motion.frame_count, 30)
        self.assertEqual(len(motion.bone_tracks), 1)
        self.assertEqual(len(motion.bone_tracks[0].channels), 1)
        self.assertEqual(
            motion.bone_tracks[0].channels[0].channel_flag,
            AANChannelFlag.ROTATION_X,
        )

    def test_truncated_motion(self):
        """Truncated data returns empty motion."""
        motion = _parse_motion(b"\x00" * 8, 0)
        self.assertEqual(motion.frame_count, 0)
        self.assertEqual(len(motion.bone_tracks), 0)


# =============================================================================
# Parser Full File Tests
# =============================================================================


class TestLoadAANFromBytes(unittest.TestCase):
    """Test load_aan_from_bytes."""

    def test_empty_data(self):
        aan = faan.load_aan_from_bytes(b"")
        self.assertEqual(len(aan.parts), 0)

    def test_invalid_data(self):
        aan = faan.load_aan_from_bytes(b"\x00\x00\x00\x00")
        self.assertEqual(len(aan.parts), 0)

    def test_minimal_file(self):
        """Test a minimal 1-part, 1-motion, 1-bone, 1-channel AAN file."""
        # Build the motion data first
        kf_data = struct.pack("<Hh", 0, 160)  # frame=0, value=160 (loc_x -> 10.0)
        comp_header = struct.pack(
            "<HHII",
            AANChannelFlag.LOCATION_X,
            AANKeyframeType.LINEAR_SHORT,
            1,
            len(kf_data),
        )
        comp_data = comp_header + kf_data

        track_header = struct.pack("<III", 1, len(comp_data), 0)
        track_data = track_header + comp_data

        motion_header = struct.pack("<IIIII", 1, 10, 0, 0, len(track_data))
        motion_data = motion_header + track_data

        # We need to build the file structure:
        # Byte 0: first_table_offset (uint32) — offset to first motion table
        # Byte 4+: part table entries (motion_table_offset, motion_count) * part_count
        # Then: motion table (array of uint32 offsets to motion data)
        # Then: motion data

        # 1 part: first_table_offset = 8 (so part_count = 8 // 8 = 1)
        # Part table at offset 4: (motion_table_offset, motion_count)
        # Motion table: 1 entry pointing to motion data

        # Layout:
        # [0..3]   first_table_offset = 8
        # [4..7]   part 0 motion_table_offset (= 12)
        # [8..11]  part 0 motion_count = 1
        # [12..15] motion 0 offset (= 16)
        # [16..]   motion data

        motion_table_offset = 12
        motion_offset = 16

        file_data = struct.pack("<I", 8)  # first_table_offset
        file_data += struct.pack("<II", motion_table_offset, 1)  # part 0 entry
        file_data += struct.pack("<I", motion_offset)  # motion table entry
        file_data += motion_data  # motion data at offset 16

        aan = faan.load_aan_from_bytes(file_data)

        self.assertEqual(len(aan.parts), 1)
        self.assertEqual(len(aan.parts[0].motions), 1)

        motion = aan.parts[0].motions[0]
        self.assertEqual(motion.frame_count, 10)
        self.assertEqual(len(motion.bone_tracks), 1)
        self.assertEqual(len(motion.bone_tracks[0].channels), 1)

        ch = motion.bone_tracks[0].channels[0]
        self.assertEqual(ch.channel_flag, AANChannelFlag.LOCATION_X)
        self.assertEqual(len(ch.keyframes), 1)
        self.assertAlmostEqual(ch.keyframes[0].value, 10.0, places=5)


# =============================================================================
# Import Channel Mapping Tests
# =============================================================================


class TestAANChannelToPropertyInfo(unittest.TestCase):
    """Test _aan_channel_to_property_info for all 9 channel flags."""

    def test_location_x(self):
        prop, idx, tt = aan_importer._aan_channel_to_property_info(AANChannelFlag.LOCATION_X)
        self.assertEqual(prop, "location")
        self.assertEqual(idx, 0)  # MHF X -> Blender X

    def test_location_y(self):
        prop, idx, tt = aan_importer._aan_channel_to_property_info(AANChannelFlag.LOCATION_Y)
        self.assertEqual(prop, "location")
        self.assertEqual(idx, 2)  # MHF Y -> Blender Z

    def test_location_z(self):
        prop, idx, tt = aan_importer._aan_channel_to_property_info(AANChannelFlag.LOCATION_Z)
        self.assertEqual(prop, "location")
        self.assertEqual(idx, 1)  # MHF Z -> Blender Y

    def test_rotation_x(self):
        prop, idx, tt = aan_importer._aan_channel_to_property_info(AANChannelFlag.ROTATION_X)
        self.assertEqual(prop, "rotation_euler")
        self.assertEqual(idx, 0)

    def test_rotation_y(self):
        prop, idx, tt = aan_importer._aan_channel_to_property_info(AANChannelFlag.ROTATION_Y)
        self.assertEqual(prop, "rotation_euler")
        self.assertEqual(idx, 2)  # MHF Y -> Blender Z

    def test_rotation_z(self):
        prop, idx, tt = aan_importer._aan_channel_to_property_info(AANChannelFlag.ROTATION_Z)
        self.assertEqual(prop, "rotation_euler")
        self.assertEqual(idx, 1)  # MHF Z -> Blender Y

    def test_scale_x(self):
        prop, idx, tt = aan_importer._aan_channel_to_property_info(AANChannelFlag.SCALE_X)
        self.assertEqual(prop, "scale")
        self.assertEqual(idx, 0)

    def test_scale_y(self):
        prop, idx, tt = aan_importer._aan_channel_to_property_info(AANChannelFlag.SCALE_Y)
        self.assertEqual(prop, "scale")
        self.assertEqual(idx, 2)  # MHF Y -> Blender Z

    def test_scale_z(self):
        prop, idx, tt = aan_importer._aan_channel_to_property_info(AANChannelFlag.SCALE_Z)
        self.assertEqual(prop, "scale")
        self.assertEqual(idx, 1)  # MHF Z -> Blender Y

    def test_unknown_channel(self):
        prop, idx, tt = aan_importer._aan_channel_to_property_info(0x9999)
        self.assertIsNone(prop)
        self.assertEqual(tt, "unknown")


# =============================================================================
# Import Rotation Negation Tests
# =============================================================================


class TestShouldNegateAANRotation(unittest.TestCase):
    """Test _should_negate_aan_rotation for all flags."""

    def test_rotation_x_negated(self):
        self.assertTrue(aan_importer._should_negate_aan_rotation(AANChannelFlag.ROTATION_X))

    def test_rotation_y_negated(self):
        self.assertTrue(aan_importer._should_negate_aan_rotation(AANChannelFlag.ROTATION_Y))

    def test_rotation_z_not_negated(self):
        self.assertFalse(aan_importer._should_negate_aan_rotation(AANChannelFlag.ROTATION_Z))

    def test_location_not_negated(self):
        self.assertFalse(aan_importer._should_negate_aan_rotation(AANChannelFlag.LOCATION_X))
        self.assertFalse(aan_importer._should_negate_aan_rotation(AANChannelFlag.LOCATION_Y))
        self.assertFalse(aan_importer._should_negate_aan_rotation(AANChannelFlag.LOCATION_Z))

    def test_scale_not_negated(self):
        self.assertFalse(aan_importer._should_negate_aan_rotation(AANChannelFlag.SCALE_X))


# =============================================================================
# Import Value Transform Tests
# =============================================================================


class TestTransformAANValue(unittest.TestCase):
    """Test _transform_aan_value for each transform type."""

    def test_location_scaled(self):
        # IMPORT_SCALE is 0.01
        result = aan_importer._transform_aan_value(100.0, "location")
        self.assertAlmostEqual(result, 1.0, places=5)

    def test_rotation_passthrough(self):
        result = aan_importer._transform_aan_value(1.5, "rotation")
        self.assertAlmostEqual(result, 1.5, places=5)

    def test_rotation_negated(self):
        result = aan_importer._transform_aan_value(1.5, "rotation", negate=True)
        self.assertAlmostEqual(result, -1.5, places=5)

    def test_scale_passthrough(self):
        result = aan_importer._transform_aan_value(2.0, "scale")
        self.assertAlmostEqual(result, 2.0, places=5)


# =============================================================================
# Import Integration Tests (Mock Builders)
# =============================================================================


@dataclass
class MockPoseBone:
    """Mock pose bone for testing."""
    name: str
    rotation_mode: str = "QUATERNION"
    bone: Any = None

    def __post_init__(self):
        if self.bone is None:
            self.bone = MockBoneData(name=self.name)


@dataclass
class MockBoneData:
    """Mock bone data with custom properties."""
    name: str
    custom_properties: Dict[str, Any] = field(default_factory=dict)

    def get(self, key, default=None):
        return self.custom_properties.get(key, default)


@dataclass
class MockPoseBones:
    """Mock pose bones collection."""
    _bones: Dict[str, MockPoseBone] = field(default_factory=dict)

    def __contains__(self, name):
        return name in self._bones

    def __getitem__(self, name):
        return self._bones[name]

    def keys(self):
        return self._bones.keys()

    def __iter__(self):
        return iter(self._bones.values())


@dataclass
class MockArmature:
    """Mock armature for testing."""
    name: str = "TestArmature"
    type: str = "ARMATURE"
    pose: Any = None

    def __post_init__(self):
        if self.pose is None:
            self.pose = type("Pose", (), {"bones": MockPoseBones()})()


def _build_test_aan_file(
    parts_config: List[List[dict]],
) -> bytes:
    """Build a minimal AAN file from a configuration.

    :param parts_config: List of parts, each a list of motions.
        Each motion is a dict with 'frame_count' and 'tracks' (list of
        list of (channel_flag, [(frame, value), ...]) tuples).
    :return: Raw AAN file bytes.
    """
    # First build all motion data blobs and record their offsets
    motion_blobs = []
    for part_motions in parts_config:
        part_blobs = []
        for motion_cfg in part_motions:
            frame_count = motion_cfg.get("frame_count", 10)
            tracks = motion_cfg.get("tracks", [])

            # Build track data
            all_track_data = b""
            for track_channels in tracks:
                comp_data = b""
                for ch_flag, kf_list in track_channels:
                    kf_bytes = b""
                    for frame, value in kf_list:
                        kf_bytes += struct.pack("<Hh", frame, value)
                    comp_header = struct.pack(
                        "<HHII",
                        ch_flag,
                        AANKeyframeType.LINEAR_SHORT,
                        len(kf_list),
                        len(kf_bytes),
                    )
                    comp_data += comp_header + kf_bytes

                track_header = struct.pack("<III", len(track_channels), len(comp_data), 0)
                all_track_data += track_header + comp_data

            motion_header = struct.pack(
                "<IIIII", len(tracks), frame_count, 0, 0, len(all_track_data)
            )
            part_blobs.append(motion_header + all_track_data)
        motion_blobs.append(part_blobs)

    part_count = len(parts_config)
    # first_table_offset = part_count * 8
    first_table_offset = part_count * 8

    # Calculate offsets
    # File layout:
    # [0..3] first_table_offset
    # [4..4+part_count*8-1] part table entries
    # [4+part_count*8..] motion tables + motion data
    part_table_start = 4
    motion_tables_start = part_table_start + part_count * 8

    # Build motion tables and calculate motion offsets
    current_offset = motion_tables_start
    # First pass: allocate space for all motion tables
    for blobs in motion_blobs:
        current_offset += len(blobs) * 4  # uint32 per motion offset

    # Second pass: assign motion data offsets
    motion_data_offset = current_offset
    motion_offsets = []  # per-part list of motion offsets
    for blobs in motion_blobs:
        part_offsets = []
        for blob in blobs:
            part_offsets.append(motion_data_offset)
            motion_data_offset += len(blob)
        motion_offsets.append(part_offsets)

    # Build the file
    file_data = struct.pack("<I", first_table_offset)

    # Part table entries
    mt_offset = motion_tables_start
    for p_idx, blobs in enumerate(motion_blobs):
        file_data += struct.pack("<II", mt_offset, len(blobs))
        mt_offset += len(blobs) * 4

    # Motion tables
    for p_idx, offsets in enumerate(motion_offsets):
        for off in offsets:
            file_data += struct.pack("<I", off)

    # Motion data
    for blobs in motion_blobs:
        for blob in blobs:
            file_data += blob

    return file_data


class TestImportAANMonster(unittest.TestCase):
    """Test import_aan_monster with mock builders."""

    def _make_armature(self, bone_count, bucket_map=None):
        """Create a mock armature with bones.

        :param bone_count: Number of bones to create.
        :param bucket_map: Optional dict mapping bone_name -> part_id.
        """
        armature = MockArmature()
        bones_dict = {}
        for i in range(bone_count):
            name = f"Bone.{i:03d}"
            bone = MockPoseBone(name=name)
            if bucket_map and name in bucket_map:
                bone.bone.custom_properties["part_id"] = bucket_map[name]
            bones_dict[name] = bone
        armature.pose.bones = MockPoseBones(_bones=bones_dict)
        return armature

    def test_empty_file(self):
        """Import with no data returns None."""
        import tempfile, os

        builders = get_mock_builders()
        with tempfile.NamedTemporaryFile(suffix=".aan", delete=False) as f:
            f.write(b"\x00" * 4)
            f.flush()
            tmppath = f.name

        try:
            result = aan_importer.import_aan_monster(
                tmppath, None, motion_index=0, builders=builders,
            )
            self.assertIsNone(result)
        finally:
            os.unlink(tmppath)

    def test_single_part_monster(self):
        """Import a 1-part AAN with 1 bone, rotation channel."""
        import tempfile, os

        builders = get_mock_builders()
        armature = self._make_armature(1)

        # Build file: 1 part, 1 motion, 1 bone, 1 channel (ROTATION_X)
        file_data = _build_test_aan_file([
            [{"frame_count": 20, "tracks": [
                [(AANChannelFlag.ROTATION_X, [(0, 0), (10, 4096)])],
            ]}],
        ])

        with tempfile.NamedTemporaryFile(suffix=".aan", delete=False) as f:
            f.write(file_data)
            f.flush()
            tmppath = f.name

        try:
            action = aan_importer.import_aan_monster(
                tmppath, armature, motion_index=0, builders=builders,
            )
            self.assertIsNotNone(action)
            self.assertEqual(len(builders.animation.created_actions), 1)

            # Check FCurves were created
            self.assertGreater(len(action.fcurves), 0)
            # Rotation X -> rotation_euler index 0
            fc = action.fcurves[0]
            self.assertIn("rotation_euler", fc.data_path)
            self.assertEqual(fc.index, 0)
            # Should have 2 keyframes
            self.assertEqual(len(fc.keyframe_points), 2)
        finally:
            os.unlink(tmppath)

    def test_two_part_monster(self):
        """Import 2-part AAN, each part maps to different bone bucket."""
        import tempfile, os

        builders = get_mock_builders()
        armature = self._make_armature(
            2,
            bucket_map={"Bone.000": 0, "Bone.001": 1},
        )

        file_data = _build_test_aan_file([
            # Part 0 -> bucket 0 (Bone.000)
            [{"frame_count": 10, "tracks": [
                [(AANChannelFlag.LOCATION_X, [(0, 160)])],
            ]}],
            # Part 1 -> bucket 0 still (part_idx 1 // 2 = 0)
            [{"frame_count": 10, "tracks": [
                [(AANChannelFlag.LOCATION_Y, [(0, 320)])],
            ]}],
        ])

        with tempfile.NamedTemporaryFile(suffix=".aan", delete=False) as f:
            f.write(file_data)
            f.flush()
            tmppath = f.name

        try:
            action = aan_importer.import_aan_monster(
                tmppath, armature, motion_index=0, builders=builders,
            )
            self.assertIsNotNone(action)
            # Both parts map to bucket 0 (Bone.000)
            self.assertGreater(len(action.fcurves), 0)
        finally:
            os.unlink(tmppath)


class TestImportAANPlayer(unittest.TestCase):
    """Test import_aan_player with mock builders."""

    def _make_armature(self, bone_count, bucket_map=None):
        armature = MockArmature()
        bones_dict = {}
        for i in range(bone_count):
            name = f"Bone.{i:03d}"
            bone = MockPoseBone(name=name)
            if bucket_map and name in bucket_map:
                bone.bone.custom_properties["part_id"] = bucket_map[name]
            bones_dict[name] = bone
        armature.pose.bones = MockPoseBones(_bones=bones_dict)
        return armature

    def test_player_upper_lower(self):
        """Even parts = upper body (bucket 0), odd = lower body (bucket 1)."""
        import tempfile, os

        builders = get_mock_builders()
        armature = self._make_armature(
            2,
            bucket_map={"Bone.000": 0, "Bone.001": 1},
        )

        file_data = _build_test_aan_file([
            # Part 0 (even) -> upper body (bucket 0, Bone.000)
            [{"frame_count": 15, "tracks": [
                [(AANChannelFlag.ROTATION_Z, [(0, 0), (10, 2000)])],
            ]}],
            # Part 1 (odd) -> lower body (bucket 1, Bone.001)
            [{"frame_count": 15, "tracks": [
                [(AANChannelFlag.ROTATION_Z, [(0, 0), (10, 1000)])],
            ]}],
        ])

        with tempfile.NamedTemporaryFile(suffix=".aan", delete=False) as f:
            f.write(file_data)
            f.flush()
            tmppath = f.name

        try:
            action = aan_importer.import_aan_player(
                tmppath, armature, motion_index=0, builders=builders,
            )
            self.assertIsNotNone(action)

            # Should have 2 FCurves (one per bone)
            self.assertEqual(len(action.fcurves), 2)

            # Verify data paths reference different bones
            data_paths = {fc.data_path for fc in action.fcurves}
            self.assertIn('pose.bones["Bone.000"].rotation_euler', data_paths)
            self.assertIn('pose.bones["Bone.001"].rotation_euler', data_paths)
        finally:
            os.unlink(tmppath)


class TestImportAANDispatcher(unittest.TestCase):
    """Test import_aan dispatcher."""

    def test_mode_selection(self):
        """Verify dispatcher calls correct function based on mode."""
        import tempfile, os

        builders = get_mock_builders()

        file_data = _build_test_aan_file([
            [{"frame_count": 5, "tracks": [
                [(AANChannelFlag.LOCATION_X, [(0, 0)])],
            ]}],
        ])

        with tempfile.NamedTemporaryFile(suffix=".aan", delete=False) as f:
            f.write(file_data)
            f.flush()
            tmppath = f.name

        try:
            # Monster mode
            action = aan_importer.import_aan(
                tmppath, None, mode="monster", motion_index=0, builders=builders,
            )
            self.assertIsNotNone(action)
            self.assertIn("_m0", action.name)

            # Player mode
            action2 = aan_importer.import_aan(
                tmppath, None, mode="player", motion_index=0, builders=builders,
            )
            self.assertIsNotNone(action2)
        finally:
            os.unlink(tmppath)


if __name__ == "__main__":
    unittest.main()
