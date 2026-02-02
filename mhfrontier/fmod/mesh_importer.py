# -*- coding: utf-8 -*-
"""
Mesh import utilities for Blender.

Handles core geometry import: vertices, faces, normals, UVs, and weights.
This module uses an abstraction layer for Blender operations to enable testing.
"""

from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from ..config import transform_vertex
from ..blender.api import MeshBuilder, ObjectBuilder

if TYPE_CHECKING:
    from .fmesh import FMesh


def _get_default_builders() -> Tuple[MeshBuilder, ObjectBuilder]:
    """Get default Blender builders (lazy import to avoid Blender dependency at import time)."""
    from ..blender.blender_impl import get_mesh_builder, get_object_builder

    return get_mesh_builder(), get_object_builder()


def import_mesh(
    index: int,
    mesh: "FMesh",
    blender_materials: Dict[int, Any],
    mesh_builder: Optional[MeshBuilder] = None,
    object_builder: Optional[ObjectBuilder] = None,
) -> Any:
    """
    Import a mesh part into Blender.

    :param index: Mesh index for naming.
    :param mesh: FMesh with geometry data.
    :param blender_materials: Materials associated with the mesh.
    :param mesh_builder: Optional mesh builder (defaults to Blender implementation).
    :param object_builder: Optional object builder (defaults to Blender implementation).
    :return: The created Blender object.
    """
    if mesh_builder is None or object_builder is None:
        default_mesh, default_obj = _get_default_builders()
        mesh_builder = mesh_builder or default_mesh
        object_builder = object_builder or default_obj

    object_builder.deselect_all()

    # Geometry
    object_name = "FModMeshpart %03d" % (index,)
    blender_mesh = create_mesh(object_name, mesh.vertices, mesh.faces, mesh_builder)
    blender_object = create_blender_object(
        object_name, blender_mesh, object_builder
    )

    # Normals Handling
    set_normals(mesh.normals, blender_mesh, mesh_builder)

    # UVs
    if mesh.uvs is not None:
        mesh_builder.create_uv_layer(blender_mesh, "UV0")
        create_texture_layer(
            blender_mesh,
            mesh.uvs,
            mesh.material_list,
            mesh.material_map,
            blender_materials,
            mesh_builder,
        )

    # Weights
    if mesh.weights is not None:
        # Weapons with different parts such as lance mesh.bone_remap is None
        if mesh.bone_remap is None:
            # Different weapon parts share the same vertex indexes,
            # this is a workaround for this unhandled case
            mesh.bone_remap = list(range(max(mesh.weights.keys()) + 1))
        set_weights(mesh.weights, mesh.bone_remap, blender_object, object_builder)

    mesh_builder.update_mesh(blender_mesh)
    return blender_object


def create_mesh(
    name: str,
    vertices: List[Tuple[float, float, float]],
    faces: List[List[int]],
    mesh_builder: Optional[MeshBuilder] = None,
) -> Any:
    """
    Create a new Blender mesh from vertices and faces.

    :param name: Name for the mesh.
    :param vertices: Vertices to assign, will be scaled and axis-remapped.
    :param faces: List of faces as vertex index lists.
    :param mesh_builder: Optional mesh builder (defaults to Blender implementation).
    :return: Created Blender mesh.
    """
    if mesh_builder is None:
        mesh_builder, _ = _get_default_builders()

    # Transform vertices from Frontier to Blender coordinate system
    transformed_vertices = [transform_vertex(v) for v in vertices]
    blender_mesh = mesh_builder.create_mesh(name, transformed_vertices, faces)
    return blender_mesh


def create_blender_object(
    name: str,
    blender_mesh: Any,
    object_builder: Optional[ObjectBuilder] = None,
) -> Any:
    """
    Create a new Blender object with a linked mesh.

    :param name: Name for the object.
    :param blender_mesh: Mesh to link.
    :param object_builder: Optional object builder (defaults to Blender implementation).
    :return: Created Blender object.
    """
    if object_builder is None:
        _, object_builder = _get_default_builders()

    blender_object = object_builder.create_object(name, blender_mesh)
    object_builder.link_to_scene(blender_object)
    return blender_object


def create_texture_layer(
    blender_mesh: Any,
    uv: List[List[float]],
    material_list: List[int],
    face_materials: List[int],
    blender_materials: Dict[int, Any],
    mesh_builder: Optional[MeshBuilder] = None,
) -> None:
    """
    Assign UV mapping and materials to a mesh.

    :param blender_mesh: Mesh to modify.
    :param uv: UV coordinates per vertex.
    :param material_list: List of material IDs.
    :param face_materials: Material index for each face.
    :param blender_materials: Blender material objects by ID.
    :param mesh_builder: Optional mesh builder (defaults to Blender implementation).
    """
    if mesh_builder is None:
        mesh_builder, _ = _get_default_builders()

    # Add the materials to the mesh
    for mat_id in material_list:
        mesh_builder.add_material(blender_mesh, blender_materials[mat_id])

    mesh_builder.set_uvs(blender_mesh, uv, face_materials)


def set_normals(
    normals: List[List[float]],
    mesh_part: Any,
    mesh_builder: Optional[MeshBuilder] = None,
) -> None:
    """
    Set custom normals on a mesh.

    :param normals: Normal vectors per vertex.
    :param mesh_part: Mesh to set normals on.
    :param mesh_builder: Optional mesh builder (defaults to Blender implementation).
    """
    if mesh_builder is None:
        mesh_builder, _ = _get_default_builders()

    mesh_builder.set_normals(mesh_part, normals)


def set_weights(
    weights: Dict[int, List[Tuple[int, float]]],
    remap: List[int],
    mesh_obj: Any,
    object_builder: Optional[ObjectBuilder] = None,
) -> None:
    """
    Set vertex weights for skeletal animation.

    :param weights: Dict of bone_id -> [(vertex_id, weight)].
    :param remap: Mapping of local bone indices to skeleton IDs.
    :param mesh_obj: Blender object to add vertex groups to.
    :param object_builder: Optional object builder (defaults to Blender implementation).
    """
    if object_builder is None:
        _, object_builder = _get_default_builders()

    for mesh_bone_ix, group in weights.items():
        group_ix = remap[mesh_bone_ix]
        group_id = "%03d" % group_ix if isinstance(group_ix, int) else str(group_ix)
        group_name = f"Bone.{group_id}"
        for vertex, weight in group:
            object_builder.add_vertex_weight(mesh_obj, group_name, vertex, weight)
