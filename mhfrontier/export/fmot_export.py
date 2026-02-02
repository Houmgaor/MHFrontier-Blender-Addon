# -*- coding: utf-8 -*-
"""
FMOT (Frontier Motion) file export.

Exports animation data to the Frontier FMOT binary format.
"""

import struct
from typing import List

from .blender_extractor import (
    ExtractedKeyframe,
    ExtractedChannel,
    ExtractedBoneAnimation,
    ExtractedMotion,
)
from ..fmod.fmot import (
    BLOCK_ANIMATION_HEADER,
    BLOCK_KEYFRAME_TYPE,
)
from ..logging_config import get_logger

_logger = get_logger("export.fmot")


def _clamp_int16(value: float) -> int:
    """
    Clamp a float value to int16 range.

    :param value: Float value to clamp.
    :return: Clamped int16 value.
    """
    clamped = max(-32768, min(32767, int(round(value))))
    return clamped


def serialize_keyframe(keyframe: ExtractedKeyframe) -> bytes:
    """
    Serialize a keyframe to 8 bytes.

    Keyframe format:
    - int16: tangent_in
    - int16: tangent_out
    - int16: value
    - uint16: frame

    :param keyframe: Extracted keyframe data.
    :return: 8-byte binary representation.
    """
    tangent_in = _clamp_int16(keyframe.tangent_in)
    tangent_out = _clamp_int16(keyframe.tangent_out)
    value = _clamp_int16(keyframe.value)
    frame = max(0, min(65535, keyframe.frame))

    return struct.pack("<hhHH", tangent_in, tangent_out, value, frame)


def build_keyframe_block(channel: ExtractedChannel) -> bytes:
    """
    Build a keyframe block for a channel.

    Block format:
    - uint32: block type (0x801200XX where XX = channel_type)
    - uint16: keyframe count
    - uint16: padding
    - N * 8 bytes: keyframes

    :param channel: Extracted channel with keyframes.
    :return: Binary block data.
    """
    # Build block type: 0x80120000 | channel_type
    block_type = BLOCK_KEYFRAME_TYPE | channel.channel_type

    # Header: type (4) + count (2) + padding (2)
    header = struct.pack("<IHH", block_type, len(channel.keyframes), 0)

    # Serialize all keyframes
    keyframe_data = b"".join(
        serialize_keyframe(kf) for kf in channel.keyframes
    )

    return header + keyframe_data


def build_bone_group_block(bone_id: int) -> bytes:
    """
    Build a bone group header block.

    This is an 8-byte block that marks the start of a bone's animation data.
    Block type: 0x80000000 | bone_id

    :param bone_id: Bone identifier.
    :return: 8-byte binary block.
    """
    block_type = 0x80000000 | bone_id
    # 8 bytes: type (4) + padding/count (4)
    return struct.pack("<II", block_type, 0)


def build_animation_block(motion: ExtractedMotion) -> bytes:
    """
    Build complete animation block content.

    Structure:
    - For each bone:
      - Bone group block (8 bytes)
      - Keyframe blocks for each channel

    :param motion: Extracted motion data.
    :return: Binary animation content.
    """
    parts = []

    # Sort bones by ID for consistent output
    sorted_bone_ids = sorted(motion.bone_animations.keys())

    for bone_id in sorted_bone_ids:
        bone_anim = motion.bone_animations[bone_id]

        # Add bone group header
        parts.append(build_bone_group_block(bone_id))

        # Sort channels by type for consistent output
        sorted_channel_types = sorted(bone_anim.channels.keys())

        for channel_type in sorted_channel_types:
            channel = bone_anim.channels[channel_type]
            if channel.keyframes:
                parts.append(build_keyframe_block(channel))

    return b"".join(parts)


def build_fmot_file(motion: ExtractedMotion) -> bytes:
    """
    Build complete FMOT file data.

    FMOT structure:
    - Animation header block (0x80000002)
      - type: uint32 (0x80000002)
      - count: uint32 (animation count, usually 1)
      - size: uint32 (total block size)
      - unknown: uint32 (padding)
    - Animation content (bone groups + keyframe blocks)

    :param motion: Extracted motion data.
    :return: Complete FMOT file data.
    """
    # Build animation content first to know size
    content = build_animation_block(motion)

    # Animation header: type (4) + count (4) + size (4) + padding (4) = 16 bytes
    header_size = 16
    total_size = header_size + len(content)

    # Count: number of bone animations
    bone_count = len(motion.bone_animations)

    header = struct.pack(
        "<IIII",
        BLOCK_ANIMATION_HEADER,  # 0x80000002
        bone_count,
        total_size,
        0,  # padding/unknown
    )

    return header + content


def export_fmot(filepath: str, motion: ExtractedMotion) -> None:
    """
    Export motion data to an FMOT file.

    :param filepath: Output file path.
    :param motion: Motion data to export.
    """
    bone_count = len(motion.bone_animations)
    channel_count = sum(
        len(ba.channels) for ba in motion.bone_animations.values()
    )
    keyframe_count = sum(
        len(ch.keyframes)
        for ba in motion.bone_animations.values()
        for ch in ba.channels.values()
    )

    _logger.info(
        "Exporting FMOT to %s: %d bones, %d channels, %d keyframes",
        filepath,
        bone_count,
        channel_count,
        keyframe_count,
    )

    data = build_fmot_file(motion)

    with open(filepath, "wb") as f:
        f.write(data)

    _logger.info("FMOT export complete: %d bytes written", len(data))
