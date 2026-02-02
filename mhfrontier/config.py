# -*- coding: utf-8 -*-
"""
Configuration constants for MHFrontier importer.

These constants control coordinate system transformation between
Monster Hunter Frontier's format and Blender's coordinate system.

Frontier uses a different scale and axis orientation than Blender:
- Scale: Frontier models are 100x larger than Blender's typical scale
- Axes: Frontier uses Y-up, Blender uses Z-up (requires Y/Z swap)
"""

from typing import Tuple


# =============================================================================
# Scale Configuration
# =============================================================================

#: Scale factor applied during import (Frontier → Blender)
#: Frontier models are 100x larger than typical Blender scale
IMPORT_SCALE: float = 0.01  # 1/100

#: Scale factor applied during export (Blender → Frontier)
#: Inverse of IMPORT_SCALE
EXPORT_SCALE: float = 100.0


# =============================================================================
# Axis Configuration
# =============================================================================

#: Axis indices for remapping Frontier coordinates to Blender
#: Frontier: X, Y (up), Z, W → Blender: X, Z (up), Y, W
#: Usage: blender_coord[i] = frontier_coord[AXIS_REMAP[i]]
AXIS_REMAP: Tuple[int, int, int, int] = (0, 2, 1, 3)

#: Indices for 3D vertex transformation (without W component)
#: Usage: (frontier[0], frontier[2], frontier[1]) for Y/Z swap
AXIS_REMAP_3D: Tuple[int, int, int] = (0, 2, 1)


# =============================================================================
# Transformation Functions
# =============================================================================

def transform_vertex(
    vertex: Tuple[float, float, float],
    scale: float = IMPORT_SCALE,
) -> Tuple[float, float, float]:
    """
    Transform a vertex from Frontier to Blender coordinate system.

    Applies scale factor and swaps Y/Z axes.

    :param vertex: Frontier vertex (x, y, z).
    :param scale: Scale factor to apply (default: IMPORT_SCALE).
    :return: Transformed vertex for Blender (x, z, y) * scale.
    """
    return (
        vertex[AXIS_REMAP_3D[0]] * scale,
        vertex[AXIS_REMAP_3D[1]] * scale,
        vertex[AXIS_REMAP_3D[2]] * scale,
    )


def transform_vector4(
    vec4: Tuple[float, float, float, float],
    scale: float = IMPORT_SCALE,
) -> Tuple[float, float, float, float]:
    """
    Transform a 4D vector from Frontier to Blender coordinate system.

    Applies scale factor and remaps axes according to AXIS_REMAP.

    :param vec4: Frontier vector (x, y, z, w).
    :param scale: Scale factor to apply (default: IMPORT_SCALE).
    :return: Transformed vector for Blender.
    """
    return (
        vec4[AXIS_REMAP[0]] * scale,
        vec4[AXIS_REMAP[1]] * scale,
        vec4[AXIS_REMAP[2]] * scale,
        vec4[AXIS_REMAP[3]] * scale,
    )


# =============================================================================
# Export Transformation Functions (Blender → Frontier)
# =============================================================================

def reverse_transform_vertex(
    vertex: Tuple[float, float, float],
    scale: float = EXPORT_SCALE,
) -> Tuple[float, float, float]:
    """
    Transform a vertex from Blender to Frontier coordinate system.

    Applies scale factor and swaps Y/Z axes (inverse of transform_vertex).

    :param vertex: Blender vertex (x, y, z).
    :param scale: Scale factor to apply (default: EXPORT_SCALE).
    :return: Transformed vertex for Frontier (x, z, y) * scale.
    """
    # Blender (x, y, z) → Frontier (x, z, y) with scale
    return (
        vertex[0] * scale,
        vertex[2] * scale,
        vertex[1] * scale,
    )


def reverse_transform_vector4(
    vec4: Tuple[float, float, float, float],
    scale: float = EXPORT_SCALE,
) -> Tuple[float, float, float, float]:
    """
    Transform a 4D vector from Blender to Frontier coordinate system.

    Applies scale factor and remaps axes (inverse of transform_vector4).

    :param vec4: Blender vector (x, y, z, w).
    :param scale: Scale factor to apply (default: EXPORT_SCALE).
    :return: Transformed vector for Frontier.
    """
    # Blender (x, y, z, w) → Frontier (x, z, y, w) with scale
    return (
        vec4[0] * scale,
        vec4[2] * scale,
        vec4[1] * scale,
        vec4[3] * scale,
    )


def reverse_transform_uv(uv: Tuple[float, float]) -> Tuple[float, float]:
    """
    Transform UV coordinates from Blender to Frontier format.

    Flips V coordinate back (inverse of frontier_uvs in fmesh.py).

    :param uv: Blender UV coordinates (u, v).
    :return: Frontier UV coordinates (u, 1-v).
    """
    return (uv[0], 1.0 - uv[1])
