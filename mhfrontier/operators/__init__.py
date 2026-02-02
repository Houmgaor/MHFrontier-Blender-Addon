# -*- coding: utf-8 -*-
"""
Blender operators for Monster Hunter Frontier file import.

This package provides:
- FMOD import operator (fmod_import.py) - File > Import > MHF FMOD
- FSKL import operator (fskl_import.py) - File > Import > MHF FSKL
- FMOT import operator (fmot_import.py) - File > Import > MHF Motion
- Stage import operator (stage_import.py) - File > Import > MHF Stage
- FSKL to armature converter (fskl_convert.py) - Object > Create Armature

All operators are registered via the main mhfrontier/__init__.py module.
"""

from .fmod_import import ImportFMOD, menu_func_import as fmod_menu_func
from .fskl_import import ImportFSKL, menu_func_import as fskl_menu_func
from .fmot_import import ImportFMOT, menu_func_import as fmot_menu_func
from .fskl_convert import ConvertFSKL, menu_func as fskl_convert_menu_func
from .stage_import import (
    ImportStage,
    ImportStageDirect,
    menu_func_import as stage_menu_func,
    menu_func_import_direct as stage_direct_menu_func,
)

__all__ = [
    # FMOD
    "ImportFMOD",
    "fmod_menu_func",
    # FSKL
    "ImportFSKL",
    "fskl_menu_func",
    # FMOT
    "ImportFMOT",
    "fmot_menu_func",
    # FSKL Convert
    "ConvertFSKL",
    "fskl_convert_menu_func",
    # Stage
    "ImportStage",
    "ImportStageDirect",
    "stage_menu_func",
    "stage_direct_menu_func",
]
