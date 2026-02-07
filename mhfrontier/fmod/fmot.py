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
    """Animation channel identifiers.

    Two channel numbering schemes exist:
    - Standard (NPC/character): position=0x008-0x020, rotation=0x040-0x100
    - Alternate (weapon): position=0x001-0x004, rotation=0x008-0x020, scale=0x040-0x100

    The alternate scheme shifts all channels down by 3 bits.
    """
    # Alternate scheme (weapon animations) - bits 0-2 for position
    ALT_POSITION_X = 0x001
    ALT_POSITION_Y = 0x002
    ALT_POSITION_Z = 0x004
    # Standard scheme - bits 3-5 for position
    POSITION_X = 0x008
    POSITION_Y = 0x010
    POSITION_Z = 0x020
    # Standard scheme - bits 6-8 for rotation
    ROTATION_X = 0x040
    ROTATION_Y = 0x080
    ROTATION_Z = 0x100
    # Standard scheme - bits 9-11 for scale
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
    channel_mask: int = 0  # Bone block mask indicating which channels are present
    channel_count: int = 0  # Number of channels declared in bone block header


@dataclass
class MotionData:
    """Complete motion/animation data."""
    frame_count: int = 0
    bone_animations: Dict[int, BoneAnimation] = field(default_factory=dict)
    name: str = ""
    bone_offset: int = 0  # Offset to add to bone IDs for skeleton mapping


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


def _get_animation_bone_count(data: bytes, start_offset: int) -> int:
    """Read the declared bone count from an animation block header.

    :param data: Raw motion file data.
    :param start_offset: Offset to the animation header (0x80000002 marker).
    :return: Declared bone count, or 0 if invalid.
    """
    if start_offset + 16 > len(data):
        return 0
    if _read_uint32(data, start_offset) != BLOCK_ANIMATION_HEADER:
        return 0
    return _read_uint32(data, start_offset + 4)


def determine_tier_bone_offsets(
    data: bytes,
) -> List[Tuple[int, int, int]]:
    """Determine animation tier structure from a multi-animation motion file.

    MHF motion files group animations into tiers by body region.
    Each tier animates a contiguous range of skeleton bones:
    e.g. tier 0 = lower body (bones 0-15), tier 1 = upper body (bones 16-46),
    tier 2 = tail (bones 47-51).

    Bone IDs within each tier are local (0-based), so a bone_offset must be
    added to map them to the correct skeleton bones.

    :param data: Raw motion file data.
    :return: List of (start_anim_index, bone_count, bone_offset) per tier.
    """
    anim_offsets = _find_animation_blocks(data)
    if not anim_offsets:
        return []

    # Read declared bone count for each animation
    bone_counts = [_get_animation_bone_count(data, off) for off in anim_offsets]

    # Group consecutive animations with the same bone count into tiers
    tiers = []
    cumulative_offset = 0
    i = 0
    while i < len(bone_counts):
        count = bone_counts[i]
        start = i
        while i < len(bone_counts) and bone_counts[i] == count:
            i += 1
        tiers.append((start, count, cumulative_offset))
        cumulative_offset += count

    return tiers


def get_bone_offset_for_animation(
    data: bytes,
    anim_index: int,
) -> int:
    """Get the skeleton bone offset for a specific animation index.

    :param data: Raw motion file data.
    :param anim_index: Animation index (0-based).
    :return: Bone offset to add to local bone IDs.
    """
    tiers = determine_tier_bone_offsets(data)
    for start, count, offset in reversed(tiers):
        if anim_index >= start:
            return offset
    return 0


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

    Animation structure analysis:
    - Bone blocks use 0x80XXXXXX format where lower 16 bits indicate channel mask
    - Channel masks: 0x038=position, 0x1C0=rotation, 0x1F8=all
    - Animation bone blocks map directly to skeleton bones (block 0 -> Bone.000, etc.)

    Animation header format (16 bytes):
    - 4 bytes: type (0x80000002)
    - 4 bytes: bone count
    - 4 bytes: total size
    - 4 bytes: format version (0=standard, 1=extended with extra float)

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

    bone_count = _read_uint32(data, start_offset + 4)
    total_size = _read_uint32(data, start_offset + 8)
    format_version = _read_uint32(data, start_offset + 12)

    motion = MotionData()
    max_frame = 0

    # Bone mapping: animation bone blocks map directly to skeleton bones
    # Block 0 -> Bone.000, Block 1 -> Bone.001, etc.
    bone_block_count = 0
    current_bone_id = 0
    current_bone_mask = 0  # Channel mask from bone block header
    current_channel_count = 0  # Channel count from bone block header

    # Parse blocks within this animation section
    # Format version > 0 has extra header data (typically 4 bytes)
    extra_header_size = 4 if format_version > 0 else 0
    pos = start_offset + 16 + extra_header_size
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
                # Add to current bone
                if current_bone_id not in motion.bone_animations:
                    motion.bone_animations[current_bone_id] = BoneAnimation(
                        bone_id=current_bone_id,
                        channel_mask=current_bone_mask,
                        channel_count=current_channel_count,
                    )

                motion.bone_animations[current_bone_id].channels[channel_type] = channel_anim

                # Track max frame
                for kf in channel_anim.keyframes:
                    if kf.frame > max_frame:
                        max_frame = kf.frame

            pos = next_pos
            continue

        # Check for bone group block (0x80XXXXXX but not keyframe)
        if (block_type & 0x80000000) != 0:
            # Map animation bone blocks directly to skeleton bones
            # Block 0 -> Bone.000, Block 1 -> Bone.001, etc.
            current_bone_id = bone_block_count
            # Extract channel mask from lower bits (e.g., 0x038 for rotation-only,
            # 0x1F8 for position+rotation)
            current_bone_mask = block_type & 0x0FFF
            current_channel_count = _read_uint32(data, pos + 4)  # second word
            bone_block_count += 1

            pos += 8
            # Game files use 12-byte bone blocks (type + channel_count + block_size).
            # Exported files from older versions used 8-byte blocks.
            # Peek at the next word: if it's not a keyframe block, not another bone
            # block, and not zero, treat it as the block_size third word and skip it.
            if pos + 4 <= len(data):
                next_val = _read_uint32(data, pos)
                if (next_val & 0x80000000) == 0 and next_val != 0:
                    # Looks like a block_size value, skip it
                    pos += 4
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
