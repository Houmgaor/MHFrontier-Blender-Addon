# -*- coding: utf-8 -*-
"""
Binary parsing infrastructure for Monster Hunter Frontier file formats.

This package provides:
- C-struct serialization (cstruct.py) - parse binary data with C-like types
- PyCStruct base class (pycstruct.py) - structured data with attribute access
- FileLike stream wrapper (filelike.py) - in-memory stream for binary parsing
- Standard structures (standard_structures.py) - common data types
- Data containers (data_containers.py) - geometry data blocks
"""

from .cstruct import Cstruct
from .pycstruct import PyCStruct
from .filelike import FileLike

__all__ = [
    "Cstruct",
    "PyCStruct",
    "FileLike",
]
