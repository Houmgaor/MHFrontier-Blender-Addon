# -*- coding: utf-8 -*-
"""
Stage/map file import module for MHFrontier.

This module provides functionality to import stage/map files from Monster Hunter Frontier.
Stage files are .pac containers that contain compressed geometry, textures, and object
placement data.
"""

from .jkr_decompress import decompress_jkr, JKRHeader, CompressionType
from .stage_container import parse_stage_container, StageSegment, SegmentType, FileMagic

__all__ = [
    "decompress_jkr",
    "JKRHeader",
    "CompressionType",
    "parse_stage_container",
    "StageSegment",
    "SegmentType",
    "FileMagic",
]
