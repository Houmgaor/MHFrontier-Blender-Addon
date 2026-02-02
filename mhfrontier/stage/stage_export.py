# -*- coding: utf-8 -*-
"""
Stage container builder for Monster Hunter Frontier.

Builds stage container files (.pac) from segment data.
The format mirrors the parser in stage_container.py.

Container structure:
- First 3 segments: 8 bytes each (offset: 4 bytes, size: 4 bytes)
- Header for remaining segments: count (4 bytes) + unknown (4 bytes)
- Remaining segments: 12 bytes each (offset: 4 bytes, size: 4 bytes, unknown: 4 bytes)
- Data section: concatenated segment data

Ported from ReFrontier Pack.cs by Houmgaor.
"""

import struct
from dataclasses import dataclass, field
from typing import List, Optional

from .stage_container import SegmentType, StageSegment


@dataclass
class StageSegmentBuilder:
    """
    Builder for a segment to be included in a stage container.

    Attributes:
        data: Raw segment data bytes.
        segment_type: Type of segment content (FMOD, PNG, etc.).
        unknown: Unknown field value (for segments 4+).
    """

    data: bytes
    segment_type: SegmentType = SegmentType.UNKNOWN
    unknown: int = 0


def build_stage_container(segments: List[StageSegmentBuilder]) -> bytes:
    """
    Build a stage container (.pac) file from segments.

    :param segments: List of segment builders with data.
    :return: Complete stage container bytes.
    """
    if not segments:
        # Empty container - return minimal valid structure
        return b"\x00" * 32

    # Calculate header size
    # First 3 segments: 8 bytes each = 24 bytes
    # Header for rest: 8 bytes (count + unknown)
    # Remaining segments: 12 bytes each
    first_segment_count = min(len(segments), 3)
    rest_segment_count = max(0, len(segments) - 3)

    header_size = 24 + 8 + (rest_segment_count * 12)

    # Align data start to 16-byte boundary (common in game files)
    data_start = (header_size + 15) & ~15

    # Calculate segment offsets
    segment_entries = []
    current_offset = data_start

    for i, seg in enumerate(segments):
        size = len(seg.data)
        unknown = seg.unknown if i >= 3 else 0

        segment_entries.append({
            "offset": current_offset,
            "size": size,
            "unknown": unknown,
        })

        # Align each segment to 4-byte boundary
        current_offset += (size + 3) & ~3

    # Build header
    header_parts = []

    # First 3 segment entries (8 bytes each)
    for i in range(3):
        if i < len(segment_entries):
            entry = segment_entries[i]
            header_parts.append(struct.pack("<II", entry["offset"], entry["size"]))
        else:
            # Empty entry
            header_parts.append(struct.pack("<II", 0, 0))

    # Rest segments header (count + unknown)
    header_parts.append(struct.pack("<II", rest_segment_count, 0))

    # Remaining segment entries (12 bytes each)
    for i in range(3, len(segment_entries)):
        entry = segment_entries[i]
        header_parts.append(struct.pack(
            "<III",
            entry["offset"],
            entry["size"],
            entry["unknown"],
        ))

    header = b"".join(header_parts)

    # Pad header to data start
    padding_size = data_start - len(header)
    if padding_size > 0:
        header += b"\x00" * padding_size

    # Build data section
    data_parts = []
    for i, seg in enumerate(segments):
        data_parts.append(seg.data)
        # Add padding to align next segment
        remainder = len(seg.data) % 4
        if remainder != 0:
            data_parts.append(b"\x00" * (4 - remainder))

    data = b"".join(data_parts)

    return header + data


def segments_to_builders(segments: List[StageSegment]) -> List[StageSegmentBuilder]:
    """
    Convert parsed StageSegments to StageSegmentBuilders.

    Useful for round-trip testing.

    :param segments: Parsed segments from parse_stage_container().
    :return: List of builders ready for build_stage_container().
    """
    builders = []
    for seg in segments:
        builders.append(StageSegmentBuilder(
            data=seg.data,
            segment_type=seg.segment_type,
            unknown=seg.unknown,
        ))
    return builders


def build_segment_from_fmod(fmod_data: bytes) -> StageSegmentBuilder:
    """
    Create a segment builder from FMOD model data.

    :param fmod_data: Raw FMOD file bytes.
    :return: Segment builder.
    """
    return StageSegmentBuilder(
        data=fmod_data,
        segment_type=SegmentType.FMOD,
    )


def build_segment_from_texture(
    texture_data: bytes,
    is_dds: bool = False,
) -> StageSegmentBuilder:
    """
    Create a segment builder from texture data.

    :param texture_data: Raw PNG or DDS file bytes.
    :param is_dds: True if DDS format, False for PNG.
    :return: Segment builder.
    """
    seg_type = SegmentType.DDS if is_dds else SegmentType.PNG
    return StageSegmentBuilder(
        data=texture_data,
        segment_type=seg_type,
    )


def build_segment_from_audio(audio_data: bytes) -> StageSegmentBuilder:
    """
    Create a segment builder from audio data.

    :param audio_data: Raw OGG file bytes.
    :return: Segment builder.
    """
    return StageSegmentBuilder(
        data=audio_data,
        segment_type=SegmentType.OGG,
    )


def build_compressed_segment(
    raw_data: bytes,
    compress: bool = True,
) -> StageSegmentBuilder:
    """
    Create a segment builder with optional JKR compression.

    :param raw_data: Uncompressed data.
    :param compress: If True, apply JKR HFI compression.
    :return: Segment builder with JKR-wrapped or raw data.
    """
    if compress:
        from .jkr_compress import compress_jkr_hfi
        compressed = compress_jkr_hfi(raw_data)
        return StageSegmentBuilder(
            data=compressed,
            segment_type=SegmentType.JKR,
        )
    else:
        # Detect segment type from magic bytes
        from .stage_container import detect_segment_type
        seg_type = detect_segment_type(raw_data)
        return StageSegmentBuilder(
            data=raw_data,
            segment_type=seg_type,
        )
