# -*- coding: utf-8 -*-
"""
Stage container parser for Monster Hunter Frontier.

Stage files are .pac containers with the following structure:
- First 3 segments: 8 bytes each (offset: 4 bytes, size: 4 bytes)
- Header for remaining segments: count (4 bytes) + unknown (4 bytes)
- Remaining segments: 12 bytes each (offset: 4 bytes, size: 4 bytes, unknown: 4 bytes)

Ported from ReFrontier Unpack.cs by Houmgaor.
"""

import struct
from dataclasses import dataclass
from enum import IntEnum
from io import BytesIO
from typing import Dict, List, Optional

from .jkr_decompress import is_jkr_file, decompress_jkr
from .file_crypto import is_encrypted_file, decrypt_file


class FileMagic(IntEnum):
    """
    Magic byte signatures for file type detection.

    These are the first 4 bytes of each file format, read as little-endian uint32.
    Used to identify segment types within stage containers.
    """

    JKR = 0x1A524B4A    # "JKR\x1A" - Compressed data (JKR/JPK format)
    FMOD = 0x444F4D46   # "FMOD" - 3D model data
    PNG = 0x474E5089    # "\x89PNG" - PNG image (note: reversed due to little-endian)
    DDS = 0x20534444    # "DDS " - DirectDraw Surface texture
    OGG = 0x5367674F    # "OggS" - Ogg Vorbis audio


class SegmentType(IntEnum):
    """Known segment types based on magic bytes."""
    UNKNOWN = 0
    JKR = 1         # Compressed data (JKR/JPK)
    FMOD = 2        # Model data
    PNG = 3         # Texture
    DDS = 4         # DirectDraw Surface texture
    OGG = 5         # Audio


# Magic bytes to segment type mapping
MAGIC_TO_SEGMENT: Dict[int, SegmentType] = {
    FileMagic.JKR: SegmentType.JKR,
    FileMagic.FMOD: SegmentType.FMOD,
    FileMagic.PNG: SegmentType.PNG,
    FileMagic.DDS: SegmentType.DDS,
    FileMagic.OGG: SegmentType.OGG,
}


@dataclass
class StageSegment:
    """A segment within a stage container."""
    index: int
    offset: int
    size: int
    unknown: int  # Only used for segments 4+
    data: bytes
    segment_type: SegmentType

    @property
    def extension(self) -> str:
        """Get file extension for this segment type."""
        extensions = {
            SegmentType.JKR: "jkr",
            SegmentType.FMOD: "fmod",
            SegmentType.PNG: "png",
            SegmentType.DDS: "dds",
            SegmentType.OGG: "ogg",
            SegmentType.UNKNOWN: "bin",
        }
        return extensions.get(self.segment_type, "bin")


def detect_segment_type(data: bytes) -> SegmentType:
    """
    Detect segment type from magic bytes.

    :param data: Segment data (at least 4 bytes).
    :return: Detected segment type.
    """
    if len(data) < 4:
        return SegmentType.UNKNOWN

    magic = struct.unpack("<I", data[:4])[0]
    return MAGIC_TO_SEGMENT.get(magic, SegmentType.UNKNOWN)


def fully_unwrap(data: bytes, max_iterations: int = 4) -> bytes:
    """
    Iteratively decrypt and decompress data, mirroring MHBridge's fully_unwrap().

    Applies up to max_iterations rounds of ECD/EXF decryption or JKR
    decompression until the data is neither encrypted nor compressed.

    :param data: Raw file data (may be encrypted and/or compressed).
    :param max_iterations: Maximum unwrap rounds (default 4).
    :return: Unwrapped data.
    """
    for _ in range(max_iterations):
        if is_encrypted_file(data):
            data = decrypt_file(data)
        elif is_jkr_file(data):
            result = decompress_jkr(data)
            if result is None:
                break
            data = result
        else:
            break
    return data


def parse_stage_container(data: bytes) -> List[StageSegment]:
    """
    Parse a stage container file.

    :param data: Raw stage container data.
    :return: List of parsed segments.
    """
    segments = []
    stream = BytesIO(data)

    # Parse first 3 segments (8 bytes each: offset + size)
    for i in range(3):
        stream.seek(i * 8)
        offset, size = struct.unpack("<II", stream.read(8))

        if size == 0:
            continue

        # Read segment data
        stream.seek(offset)
        segment_data = stream.read(size)

        segment_type = detect_segment_type(segment_data)

        segments.append(StageSegment(
            index=i,
            offset=offset,
            size=size,
            unknown=0,
            data=segment_data,
            segment_type=segment_type,
        ))

    # Parse remaining segments header
    stream.seek(3 * 8)  # After first 3 segment entries
    rest_count, unk_header = struct.unpack("<II", stream.read(8))

    # Parse remaining segments (12 bytes each: offset + size + unknown)
    for i in range(rest_count):
        stream.seek(3 * 8 + 8 + i * 12)  # 3*8 = first entries, 8 = header
        offset, size, unknown = struct.unpack("<III", stream.read(12))

        if size == 0:
            continue

        # Read segment data
        stream.seek(offset)
        segment_data = stream.read(size)

        segment_type = detect_segment_type(segment_data)

        segments.append(StageSegment(
            index=3 + i,
            offset=offset,
            size=size,
            unknown=unknown,
            data=segment_data,
            segment_type=segment_type,
        ))

    return segments


def is_stage_container(data: bytes) -> bool:
    """
    Check if data appears to be a stage container.

    Mirrors MHBridge's is_stage_container() bounds-checking logic:
    - Fixed segment 0 must have a small, valid offset (1–4096) and size within file
    - rest_count at offset 24 must be <= 1000
    - rest segment table must fit within the file

    :param data: Raw file data.
    :return: True if this appears to be a stage container.
    """
    if len(data) < 32:
        return False

    try:
        off0 = struct.unpack_from("<I", data, 0)[0]
        sz0 = struct.unpack_from("<I", data, 4)[0]

        if off0 == 0 or off0 > 4096:
            return False
        if sz0 > len(data):
            return False
        if off0 + sz0 > len(data):
            return False

        rest_count = struct.unpack_from("<I", data, 24)[0]
        if rest_count > 1000:
            return False

        rest_table_end = 32 + rest_count * 12
        if rest_table_end > len(data):
            return False

        # Validate first rest segment if any
        if rest_count > 0:
            roff = struct.unpack_from("<I", data, 32)[0]
            rsz = struct.unpack_from("<I", data, 36)[0]
            if rsz > 0 and roff + rsz > len(data):
                return False

        return True
    except Exception:
        return False


def get_fmod_segments(segments: List[StageSegment]) -> List[StageSegment]:
    """
    Get all segments that contain FMOD data (directly or compressed).

    :param segments: List of parsed segments.
    :return: Segments containing FMOD data.
    """
    fmod_segments = []
    for segment in segments:
        if segment.segment_type == SegmentType.FMOD:
            fmod_segments.append(segment)
        elif segment.segment_type == SegmentType.JKR:
            # Check if decompressed data would be FMOD
            # This is a quick check - full decompression happens later
            fmod_segments.append(segment)
    return fmod_segments


def get_texture_segments(segments: List[StageSegment]) -> List[StageSegment]:
    """
    Get all texture segments (PNG, DDS).

    :param segments: List of parsed segments.
    :return: Texture segments.
    """
    return [s for s in segments if s.segment_type in (SegmentType.PNG, SegmentType.DDS)]


def get_audio_segments(segments: List[StageSegment]) -> List[StageSegment]:
    """
    Get all audio segments (OGG).

    :param segments: List of parsed segments.
    :return: Audio segments.
    """
    return [s for s in segments if s.segment_type == SegmentType.OGG]
