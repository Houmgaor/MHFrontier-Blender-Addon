# -*- coding: utf-8 -*-
"""
FMOD/FSKL/FMOT file format module for Monster Hunter Frontier.

This package provides:
- FMOD model loading (fmod.py) - 3D meshes with materials
- FSKL skeleton loading (fskl.py) - bone hierarchies
- FMOT motion loading (fmot.py) - animation data
- Block parsing (fblock.py) - recursive file structure parsing
- Data classes (fmesh.py, fmat.py, fbone.py) - extracted geometry/material data

For Blender import, use the importer layer modules which handle
coordinate transforms and Blender object creation.
"""

from .fmod import load_fmod_file, load_fmod_file_from_bytes
from .fskl import get_frontier_skeleton
from .fmot import load_motion_file, load_motion_from_bytes, MotionData
from .fblock import FBlock, BlockType
from .fmesh import FMesh
from .fmat import FMat
from .fbone import FBone

__all__ = [
    # Model loading
    "load_fmod_file",
    "load_fmod_file_from_bytes",
    # Skeleton loading
    "get_frontier_skeleton",
    # Motion loading
    "load_motion_file",
    "load_motion_from_bytes",
    "MotionData",
    # Block parsing
    "FBlock",
    "BlockType",
    # Data classes
    "FMesh",
    "FMat",
    "FBone",
]
