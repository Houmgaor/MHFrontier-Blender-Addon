# -*- coding: utf-8 -*-
"""
Importer modules for MHFrontier Blender addon.

This package contains the orchestration layer for importing various
Monster Hunter Frontier file formats into Blender. It separates the
import logic from the format parsing (which lives in fmod/).

Public API:
    - import_model: Import FMOD model files
    - import_skeleton: Import FSKL skeleton files
    - import_motion: Import motion/animation files
    - import_stage: Import stage containers or directories
    - clear_scene: Clear all objects from the scene
"""

from .fmod import import_model, clear_scene
from .skeleton import import_skeleton
from .motion import import_motion, import_motion_from_bytes
from .stage import (
    import_stage,
    import_fmod_file,
    import_jkr_file,
    import_fmod_from_bytes,
)

__all__ = [
    "import_model",
    "clear_scene",
    "import_skeleton",
    "import_motion",
    "import_motion_from_bytes",
    "import_stage",
    "import_fmod_file",
    "import_jkr_file",
    "import_fmod_from_bytes",
]
