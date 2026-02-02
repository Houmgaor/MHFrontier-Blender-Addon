# -*- coding: utf-8 -*-
"""
Stage/map file import and export module for MHFrontier.

This module provides functionality to import and export stage/map files from
Monster Hunter Frontier. Stage files are .pac containers that contain
compressed geometry, textures, and object placement data.
"""

from .jkr_decompress import decompress_jkr, JKRHeader, CompressionType
from .jkr_compress import compress_jkr, compress_jkr_hfi, compress_jkr_raw
from .stage_container import parse_stage_container, StageSegment, SegmentType, FileMagic
from .stage_export import (
    StageSegmentBuilder,
    build_stage_container,
    segments_to_builders,
)

__all__ = [
    # Decompression
    "decompress_jkr",
    "JKRHeader",
    "CompressionType",
    # Compression
    "compress_jkr",
    "compress_jkr_hfi",
    "compress_jkr_raw",
    # Container parsing
    "parse_stage_container",
    "StageSegment",
    "SegmentType",
    "FileMagic",
    # Container building
    "StageSegmentBuilder",
    "build_stage_container",
    "segments_to_builders",
]
