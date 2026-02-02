# -*- coding: utf-8 -*-
"""
Motion file (.mot) parser for Monster Hunter Frontier.

Parses animation data from motion files that can be applied to FSKL skeletons.

Motion file structure:
- Index table header pointing to animation blocks
- Animation blocks with bone groups and keyframe data
- Keyframe format: [tangent_in][tangent_out][value][frame]
"""

import struct
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, List, Optional, Tuple

from ..stage.jkr_decompress import decompress_jkr, is_jkr_file


class ChannelType(IntEnum):
    """Animation channel identifiers."""
    POSITION_X = 0x008
    POSITION_Y = 0x010
    POSITION_Z = 0x020
    ROTATION_X = 0x040
    ROTATION_Y = 0x080
    ROTATION_Z = 0x100
    SCALE_X = 0x200
    SCALE_Y = 0x400
    SCALE_Z = 0x800


# Block type constants
BLOCK_ANIMATION_HEADER = 0x80000002
BLOCK_KEYFRAME_TYPE_MASK = 0xFFFF0000
BLOCK_KEYFRAME_TYPE = 0x80120000


@dataclass
class Keyframe:
    """Single keyframe in an animation channel."""
    frame: int
    value: float
    tangent_in: float = 0.0
    tangent_out: float = 0.0


@dataclass
class ChannelAnimation:
    """Animation data for a single channel (e.g., position X)."""
    channel_type: int
    keyframes: List[Keyframe] = field(default_factory=list)


@dataclass
class BoneAnimation:
    """Animation data for a single bone."""
    bone_id: int
    channels: Dict[int, ChannelAnimation] = field(default_factory=dict)


@dataclass
class MotionData:
    """Complete motion/animation data."""
    frame_count: int = 0
    bone_animations: Dict[int, BoneAnimation] = field(default_factory=dict)
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


def _find_animation_blocks(data: bytes) -> List[int]:
    """
    Find offsets to animation blocks in the motion file.

    The .mot file has an index table at the start with offsets
    to animation data sections.

    :param data: Raw motion file data.
    :return: List of offsets to animation blocks.
    """
    offsets = []

    # Scan for animation header blocks (0x80000002)
    pos = 0
    while pos < len(data) - 8:
        val = _read_uint32(data, pos)
        if val == BLOCK_ANIMATION_HEADER:
            offsets.append(pos)
        pos += 4

    return offsets


def _parse_keyframes_from_block(
    data: bytes,
    pos: int,
    channel_type: int,
) -> Tuple[ChannelAnimation, int]:
    """
    Parse keyframe data from a keyframe block.

    Block format:
    - 4 bytes: block type (0x801200XX)
    - 2 bytes: keyframe count
    - 2 bytes: padding/unknown
    - N * 8 bytes: keyframes

    Keyframe format (8 bytes):
    - int16: tangent_in
    - int16: tangent_out
    - int16: value
    - uint16: frame number

    :param data: File data.
    :param pos: Start position of block.
    :param channel_type: Channel type from block header.
    :return: Tuple of (ChannelAnimation, next_position).
    """
    channel_anim = ChannelAnimation(channel_type=channel_type)

    if pos + 8 > len(data):
        return channel_anim, pos + 8

    # Read block header
    block_type = _read_uint32(data, pos)
    count = _read_uint16(data, pos + 4)

    # Parse keyframes
    kf_pos = pos + 8
    for i in range(count):
        if kf_pos + 8 > len(data):
            break

        tangent_in = _read_int16(data, kf_pos)
        tangent_out = _read_int16(data, kf_pos + 2)
        value = _read_int16(data, kf_pos + 4)
        frame = _read_uint16(data, kf_pos + 6)

        kf = Keyframe(
            frame=frame,
            value=float(value),
            tangent_in=float(tangent_in),
            tangent_out=float(tangent_out),
        )
        channel_anim.keyframes.append(kf)
        kf_pos += 8

    # Calculate next position (align to 4 bytes)
    next_pos = kf_pos
    if next_pos % 4 != 0:
        next_pos += 4 - (next_pos % 4)

    return channel_anim, next_pos


def _parse_animation_at_offset(data: bytes, start_offset: int) -> Optional[MotionData]:
    """
    Parse animation data starting at given offset.

    The bone blocks in MHF animation files use channel masks (not bone IDs) in
    the lower 16 bits. The actual skeleton bone index is determined by the
    sequential order of bone blocks:
    - First bone block = skeleton bone 0 (root)
    - Second bone block = skeleton bone 1
    - etc.

    Channel mask values:
    - 0x038 (56) = position channels (POS_X|POS_Y|POS_Z)
    - 0x1C0 (448) = rotation channels (ROT_X|ROT_Y|ROT_Z)
    - 0x1F8 (504) = all channels

    :param data: File data.
    :param start_offset: Offset to animation header.
    :return: Parsed MotionData or None.
    """
    if start_offset + 16 > len(data):
        return None

    # Read animation header
    header_type = _read_uint32(data, start_offset)
    if header_type != BLOCK_ANIMATION_HEADER:
        return None

    anim_count = _read_uint32(data, start_offset + 4)
    total_size = _read_uint32(data, start_offset + 8)

    motion = MotionData()
    max_frame = 0
    current_bone_index = 0  # Sequential bone index (maps to skeleton)
    bone_block_count = 0  # Track how many bone blocks we've seen

    # Parse blocks within this animation section
    pos = start_offset + 16
    end_pos = start_offset + total_size if total_size > 0 else len(data)

    while pos < end_pos and pos + 8 <= len(data):
        block_type = _read_uint32(data, pos)

        # Skip null/zero blocks
        if block_type == 0:
            pos += 4
            continue

        # Check for keyframe block (0x801200XX)
        if (block_type & BLOCK_KEYFRAME_TYPE_MASK) == BLOCK_KEYFRAME_TYPE:
            channel_type = block_type & 0x0FFF
            channel_anim, next_pos = _parse_keyframes_from_block(
                data, pos, channel_type
            )

            if channel_anim.keyframes:
                # Add to current bone (using sequential index)
                if current_bone_index not in motion.bone_animations:
                    motion.bone_animations[current_bone_index] = BoneAnimation(
                        bone_id=current_bone_index
                    )

                motion.bone_animations[current_bone_index].channels[channel_type] = channel_anim

                # Track max frame
                for kf in channel_anim.keyframes:
                    if kf.frame > max_frame:
                        max_frame = kf.frame

            pos = next_pos
            continue

        # Check for bone group block (0x80XXXXXX but not keyframe)
        if (block_type & 0x80000000) != 0:
            # The lower 16 bits contain a channel mask (not a bone ID)
            # Bone index is determined sequentially
            channel_mask = block_type & 0xFFFF

            # Increment bone index for each new bone block
            # (First block at index 0 is root, subsequent blocks are children)
            current_bone_index = bone_block_count
            bone_block_count += 1

            pos += 8
            continue

        # Unknown block type - skip
        pos += 4

    motion.frame_count = max_frame + 1 if max_frame > 0 else 0
    return motion


def load_motion_from_bytes(data: bytes) -> MotionData:
    """
    Load motion data from raw bytes.

    :param data: Raw motion file data.
    :return: Parsed MotionData.
    """
    # Check for JKR compression and decompress if needed
    if is_jkr_file(data):
        decompressed = decompress_jkr(data)
        if decompressed is None:
            return MotionData()
        data = decompressed

    # Find animation blocks
    block_offsets = _find_animation_blocks(data)

    if not block_offsets:
        return MotionData()

    # Parse all animation blocks and merge
    combined_motion = MotionData()

    for offset in block_offsets:
        motion = _parse_animation_at_offset(data, offset)
        if motion and motion.bone_animations:
            # Merge bone animations
            for bone_id, bone_anim in motion.bone_animations.items():
                if bone_id not in combined_motion.bone_animations:
                    combined_motion.bone_animations[bone_id] = bone_anim
                else:
                    # Merge channels
                    existing = combined_motion.bone_animations[bone_id]
                    for ch_type, ch_anim in bone_anim.channels.items():
                        if ch_type not in existing.channels:
                            existing.channels[ch_type] = ch_anim

            # Update frame count
            if motion.frame_count > combined_motion.frame_count:
                combined_motion.frame_count = motion.frame_count

    return combined_motion


def load_motion_file(filepath: str) -> MotionData:
    """
    Load motion data from a file.

    :param filepath: Path to .mot file.
    :return: Parsed MotionData.
    :raises FileNotFoundError: If file doesn't exist.
    """
    import os

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Motion file not found: {filepath}")

    with open(filepath, "rb") as f:
        data = f.read()

    motion = load_motion_from_bytes(data)
    motion.name = os.path.splitext(os.path.basename(filepath))[0]

    return motion
