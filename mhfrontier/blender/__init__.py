# -*- coding: utf-8 -*-
"""
Blender integration module.

This package provides:
- Abstract interfaces for Blender operations (api.py)
- Concrete Blender implementations (blender_impl.py)
- Mock implementations for testing (mock_impl.py)
- Shader node utilities (blender_nodes_functions.py)
"""

from .api import (
    MeshBuilder,
    ObjectBuilder,
    MaterialBuilder,
    ImageLoader,
    SceneManager,
    MatrixFactory,
)

__all__ = [
    "MeshBuilder",
    "ObjectBuilder",
    "MaterialBuilder",
    "ImageLoader",
    "SceneManager",
    "MatrixFactory",
]
