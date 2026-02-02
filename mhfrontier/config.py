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
