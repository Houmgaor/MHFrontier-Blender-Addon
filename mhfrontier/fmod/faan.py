# -*- coding: utf-8 -*-
"""
AAN animation file parser for Monster Hunter Frontier.

Parses animation package files (.aan) that contain multi-part animations
for both monsters and players. AAN files support 6 keyframe encoding types
and organize animations into parts (body regions) with multiple motion slots.

AAN file structure:
- Header with first_table_offset (part count derived from offset / 8)
- Part table: pairs of (motion_table_offset, motion_count) per part
- Motion table: offsets to individual motions
- Motion data: 20-byte header + bone tracks with component channels
"""

import struct
from dataclasses import dataclass, field
from enum import IntEnum
from typing import List, Optional

from ..config import AAN_SHORT_ROTATION_SCALE, AAN_SHORT_LOCATION_SCALE
from ..stage.jkr_decompress import decompress_jkr, is_jkr_file


class AANChannelFlag(IntEnum):
    """Channel bit flags for AAN bone track components.

    These flags indicate which SRT channel a component represents.
    Different flag space than .mot ChannelType.
    """
    LOCATION_X = 0x01
    LOCATION_Y = 0x02
    LOCATION_Z = 0x04
    ROTATION_X = 0x08
    ROTATION_Y = 0x10
    ROTATION_Z = 0x20
    SCALE_X = 0x40
    SCALE_Y = 0x80
    SCALE_Z = 0x100


class AANKeyframeType(IntEnum):
    """Keyframe encoding types in AAN files.

    Short types use int16 values with fixed-point scaling.
    Float types use IEEE 754 float32 values.
    """
    LINEAR_SHORT = 17
    HERMITE_SHORT = 18
    COMPLEX_SHORT = 19
    LINEAR_FLOAT = 33
    HERMITE_FLOAT = 34
    COMPLEX_FLOAT = 35


@dataclass
class AANKeyframe:
    """Single keyframe in an AAN animation channel."""
    frame: int
    value: float
    tangent_in: float = 0.0
    tangent_out: float = 0.0
    interpolation: str = "LINEAR"


@dataclass
class AANChannel:
    """Animation data for a single channel (e.g., rotation X)."""
    channel_flag: int
    keyframes: List[AANKeyframe] = field(default_factory=list)


@dataclass
class AANBoneTrack:
    """Animation data for a single bone, containing multiple channels."""
    channels: List[AANChannel] = field(default_factory=list)


@dataclass
class AANMotion:
    """A single motion/animation within a part."""
    bone_tracks: List[AANBoneTrack] = field(default_factory=list)
    loop_flag: int = 0
    loop_start_frame: int = 0
    frame_count: int = 0


@dataclass
class AANPart:
    """A part (body region) containing multiple motions."""
    motions: List[AANMotion] = field(default_factory=list)


@dataclass
class AANData:
    """Complete AAN animation package data."""
    parts: List[AANPart] = field(default_factory=list)
    name: str = ""


def _read_uint32(data: bytes, offset: int) -> int:
    """Read unsigned 32-bit integer at offset."""
    return struct.unpack_from("<I", data, offset)[0]


def _read_int16(data: bytes, offset: int) -> int:
    """Read signed 16-bit integer at offset."""
    return struct.unpack_from("<h", data, offset)[0]


def _read_uint16(data: bytes, offset: int) -> int:
    """Read unsigned 16-bit integer at offset."""
    return struct.unpack_from("<H", data, offset)[0]


def _read_float(data: bytes, offset: int) -> float:
    """Read 32-bit float at offset."""
    return struct.unpack_from("<f", data, offset)[0]


def _decode_short_value(raw: int, channel_flag: int) -> float:
    """Decode a short (int16) value based on channel type.

    :param raw: Raw int16 value.
    :param channel_flag: Channel flag indicating transform type.
    :return: Decoded value (radians for rotation, scaled for location/scale).
    """
    if channel_flag in (
        AANChannelFlag.ROTATION_X,
        AANChannelFlag.ROTATION_Y,
        AANChannelFlag.ROTATION_Z,
    ):
        return raw * AAN_SHORT_ROTATION_SCALE
    elif channel_flag in (
        AANChannelFlag.LOCATION_X,
        AANChannelFlag.LOCATION_Y,
        AANChannelFlag.LOCATION_Z,
    ):
        return raw * AAN_SHORT_LOCATION_SCALE
    else:
        # Scale channels
        return raw * AAN_SHORT_LOCATION_SCALE


def _parse_keyframes(
    data: bytes,
    offset: int,
    type_id: int,
    key_count: int,
    channel_flag: int,
) -> List[AANKeyframe]:
    """Parse keyframes based on encoding type.

    Decodes all 6 keyframe types to uniform AANKeyframe objects.

    :param data: Raw file data.
    :param offset: Start offset of keyframe data.
    :param type_id: Keyframe encoding type (AANKeyframeType).
    :param key_count: Number of keyframes to read.
    :param channel_flag: Channel flag for value decoding.
    :return: List of decoded keyframes.
    """
    keyframes = []
    pos = offset
    is_rotation = channel_flag in (
        AANChannelFlag.ROTATION_X,
        AANChannelFlag.ROTATION_Y,
        AANChannelFlag.ROTATION_Z,
    )

    for _ in range(key_count):
        if type_id == AANKeyframeType.LINEAR_SHORT:
            # 4 bytes: uint16 frame, int16 value
            if pos + 4 > len(data):
                break
            frame = _read_uint16(data, pos)
            raw_value = _read_int16(data, pos + 2)
            value = _decode_short_value(raw_value, channel_flag)
            keyframes.append(AANKeyframe(
                frame=frame,
                value=value,
                interpolation="LINEAR",
            ))
            pos += 4

        elif type_id == AANKeyframeType.HERMITE_SHORT:
            # 8 bytes: uint16 frame, int16 value, int16 tangent_in, int16 tangent_out
            if pos + 8 > len(data):
                break
            frame = _read_uint16(data, pos)
            raw_value = _read_int16(data, pos + 2)
            raw_tan_in = _read_int16(data, pos + 4)
            raw_tan_out = _read_int16(data, pos + 6)
            value = _decode_short_value(raw_value, channel_flag)
            tan_in = _decode_short_value(raw_tan_in, channel_flag)
            tan_out = _decode_short_value(raw_tan_out, channel_flag)
            keyframes.append(AANKeyframe(
                frame=frame,
                value=value,
                tangent_in=tan_in,
                tangent_out=tan_out,
                interpolation="BEZIER",
            ))
            pos += 8

        elif type_id == AANKeyframeType.COMPLEX_SHORT:
            # 8 bytes: uint32 frame_and_flags, int16 value, int16 tangent
            # Bit 16: 0x10000 = LINEAR, 0x20000 = BEZIER
            # Lower 16 bits = frame
            if pos + 8 > len(data):
                break
            frame_flags = _read_uint32(data, pos)
            frame = frame_flags & 0xFFFF
            flags = frame_flags & 0xFFFF0000
            raw_value = _read_int16(data, pos + 4)
            raw_tangent = _read_int16(data, pos + 6)
            value = _decode_short_value(raw_value, channel_flag)
            tangent = _decode_short_value(raw_tangent, channel_flag)

            if flags & 0x20000:
                interpolation = "BEZIER"
            else:
                interpolation = "LINEAR"

            keyframes.append(AANKeyframe(
                frame=frame,
                value=value,
                tangent_in=tangent,
                tangent_out=tangent,
                interpolation=interpolation,
            ))
            pos += 8

        elif type_id == AANKeyframeType.LINEAR_FLOAT:
            # 8 bytes: uint16 frame, 2 pad, float value
            if pos + 8 > len(data):
                break
            frame = _read_uint16(data, pos)
            value = _read_float(data, pos + 4)
            if is_rotation:
                # Float rotations are already in radians
                pass
            keyframes.append(AANKeyframe(
                frame=frame,
                value=value,
                interpolation="LINEAR",
            ))
            pos += 8

        elif type_id == AANKeyframeType.HERMITE_FLOAT:
            # 16 bytes: uint16 frame, 2 pad, float value, float tangent_in, float tangent_out
            if pos + 16 > len(data):
                break
            frame = _read_uint16(data, pos)
            value = _read_float(data, pos + 4)
            tan_in = _read_float(data, pos + 8)
            tan_out = _read_float(data, pos + 12)
            keyframes.append(AANKeyframe(
                frame=frame,
                value=value,
                tangent_in=tan_in,
                tangent_out=tan_out,
                interpolation="BEZIER",
            ))
            pos += 16

        elif type_id == AANKeyframeType.COMPLEX_FLOAT:
            # 16 bytes: uint32 frame_and_flags, float value, float tangent_in, float tangent_out
            if pos + 16 > len(data):
                break
            frame_flags = _read_uint32(data, pos)
            frame = frame_flags & 0xFFFF
            flags = frame_flags & 0xFFFF0000
            value = _read_float(data, pos + 4)
            tan_in = _read_float(data, pos + 8)
            tan_out = _read_float(data, pos + 12)

            if flags & 0x20000:
                interpolation = "BEZIER"
            else:
                interpolation = "LINEAR"

            keyframes.append(AANKeyframe(
                frame=frame,
                value=value,
                tangent_in=tan_in,
                tangent_out=tan_out,
                interpolation=interpolation,
            ))
            pos += 16

        else:
            # Unknown type, stop parsing
            break

    return keyframes


def _parse_component(
    data: bytes,
    offset: int,
) -> tuple:
    """Parse a single component (channel) from a bone track.

    Component header (12 bytes):
    - uint16: channel_flag
    - uint16: type_id (AANKeyframeType)
    - uint32: key_count
    - uint32: data_size (bytes of keyframe data following header)

    :param data: Raw file data.
    :param offset: Start offset of component header.
    :return: Tuple of (AANChannel, next_offset).
    """
    if offset + 12 > len(data):
        return AANChannel(channel_flag=0), offset + 12

    channel_flag = _read_uint16(data, offset)
    type_id = _read_uint16(data, offset + 2)
    key_count = _read_uint32(data, offset + 4)
    data_size = _read_uint32(data, offset + 8)

    keyframes = _parse_keyframes(
        data, offset + 12, type_id, key_count, channel_flag
    )

    channel = AANChannel(channel_flag=channel_flag, keyframes=keyframes)
    next_offset = offset + 12 + data_size

    return channel, next_offset


def _parse_bone_track(
    data: bytes,
    offset: int,
) -> tuple:
    """Parse a single bone track containing multiple components.

    Bone track header (12 bytes):
    - uint32: component_count
    - uint32: data_size (total bytes of component data)
    - uint32: flags/padding

    :param data: Raw file data.
    :param offset: Start offset of bone track header.
    :return: Tuple of (AANBoneTrack, next_offset).
    """
    if offset + 12 > len(data):
        return AANBoneTrack(), offset + 12

    component_count = _read_uint32(data, offset)
    data_size = _read_uint32(data, offset + 4)
    # offset + 8 is flags/padding

    track = AANBoneTrack()
    pos = offset + 12

    for _ in range(component_count):
        if pos >= len(data):
            break
        channel, pos = _parse_component(data, pos)
        track.channels.append(channel)

    next_offset = offset + 12 + data_size

    return track, next_offset


def _parse_motion(data: bytes, offset: int) -> AANMotion:
    """Parse a single motion from the AAN data.

    Motion header (20 bytes):
    - uint32: bone_count
    - uint32: frame_count
    - uint32: loop_flag
    - uint32: loop_start_frame
    - uint32: data_size (total bytes of bone track data)

    :param data: Raw file data.
    :param offset: Start offset of motion header.
    :return: Parsed AANMotion.
    """
    if offset + 20 > len(data):
        return AANMotion()

    bone_count = _read_uint32(data, offset)
    frame_count = _read_uint32(data, offset + 4)
    loop_flag = _read_uint32(data, offset + 8)
    loop_start_frame = _read_uint32(data, offset + 12)
    # offset + 16 is data_size

    motion = AANMotion(
        frame_count=frame_count,
        loop_flag=loop_flag,
        loop_start_frame=loop_start_frame,
    )

    pos = offset + 20
    for _ in range(bone_count):
        if pos >= len(data):
            break
        track, pos = _parse_bone_track(data, pos)
        motion.bone_tracks.append(track)

    return motion


def load_aan_from_bytes(data: bytes) -> AANData:
    """Parse AAN animation package from raw bytes.

    Header:
    - uint32 at offset 0: first_table_offset
    - Part count = first_table_offset // 8
    - Part table at offset 0x04: pairs of (motion_table_offset, motion_count)
    - Motion tables: arrays of uint32 offsets to motion data

    :param data: Raw AAN file data (already decompressed).
    :return: Parsed AANData.
    """
    if len(data) < 8:
        return AANData()

    first_table_offset = _read_uint32(data, 0)
    if first_table_offset == 0 or first_table_offset > len(data):
        return AANData()

    part_count = first_table_offset // 8

    aan = AANData()

    for p in range(part_count):
        part_entry_offset = 4 + p * 8
        if part_entry_offset + 8 > len(data):
            break

        motion_table_offset = _read_uint32(data, part_entry_offset)
        motion_count = _read_uint32(data, part_entry_offset + 4)

        part = AANPart()

        for m in range(motion_count):
            motion_ptr_offset = motion_table_offset + m * 4
            if motion_ptr_offset + 4 > len(data):
                break

            motion_offset = _read_uint32(data, motion_ptr_offset)
            if motion_offset == 0 or motion_offset >= len(data):
                part.motions.append(AANMotion())
                continue

            motion = _parse_motion(data, motion_offset)
            part.motions.append(motion)

        aan.parts.append(part)

    return aan


def load_aan_file(filepath: str) -> AANData:
    """Load AAN animation data from a file.

    Handles JKR-compressed files automatically.

    :param filepath: Path to .aan file.
    :return: Parsed AANData.
    :raises FileNotFoundError: If file doesn't exist.
    """
    import os

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"AAN file not found: {filepath}")

    with open(filepath, "rb") as f:
        data = f.read()

    # Handle JKR compression
    if is_jkr_file(data):
        decompressed = decompress_jkr(data)
        if decompressed is None:
            return AANData()
        data = decompressed

    aan = load_aan_from_bytes(data)
    aan.name = os.path.splitext(os.path.basename(filepath))[0]

    return aan
