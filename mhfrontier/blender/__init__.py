# -*- coding: utf-8 -*-
"""
Blender integration module.

This package provides:
- Abstract interfaces for Blender operations (api.py)
- Concrete Blender implementations (blender_impl.py)
- Mock implementations for testing (mock_impl.py)
- Shader node utilities (blender_nodes_functions.py)
- Centralized builder factory (builders.py)
"""

from .api import (
    MeshBuilder,
    ObjectBuilder,
    MaterialBuilder,
    ImageLoader,
    SceneManager,
    MatrixFactory,
    AnimationBuilder,
)
from .builders import Builders, get_builders, get_mock_builders

__all__ = [
    # Interfaces
    "MeshBuilder",
    "ObjectBuilder",
    "MaterialBuilder",
    "ImageLoader",
    "SceneManager",
    "MatrixFactory",
    "AnimationBuilder",
    # Builder factory
    "Builders",
    "get_builders",
    "get_mock_builders",
]
