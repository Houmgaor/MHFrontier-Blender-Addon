# -*- coding: utf-8 -*-
"""
Mesh import utilities for Blender.

Handles core geometry import: vertices, faces, normals, UVs, and weights.
This module is Blender-dependent but format-agnostic.
"""

import array
from typing import Any, Dict, List, Tuple, TYPE_CHECKING

import bpy
import bmesh

if TYPE_CHECKING:
    from .fmesh import FMesh


def import_mesh(
    index: int,
    mesh: "FMesh",
    blender_materials: Dict[int, bpy.types.Material],
) -> bpy.types.Object:
    """
    Import a mesh part into Blender.

    :param index: Mesh index for naming.
    :param mesh: FMesh with geometry data.
    :param blender_materials: Materials associated with the mesh.
    :return: The created Blender object.
    """
    bpy.ops.object.select_all(action="DESELECT")

    # Geometry
    object_name = "FModMeshpart %03d" % (index,)
    blender_mesh = create_mesh(object_name, mesh.vertices, mesh.faces)
    blender_object = create_blender_object(object_name, blender_mesh)

    # Normals Handling
    set_normals(mesh.normals, blender_mesh)

    # UVs
    if mesh.uvs is not None:
        if bpy.app.version >= (2, 8):
            blender_object.data.uv_layers.new(name="UV0")
        create_texture_layer(
            blender_mesh,
            mesh.uvs,
            mesh.material_list,
            mesh.material_map,
            blender_materials,
        )

    # Weights
    if mesh.weights is not None:
        # Weapons with different parts such as lance mesh.bone_remap is None
        if mesh.bone_remap is None:
            # Different weapon parts share the same vertex indexes,
            # this is a workaround for this unhandled case
            mesh.bone_remap = list(range(max(mesh.weights.keys()) + 1))
        set_weights(mesh.weights, mesh.bone_remap, blender_object)

    blender_mesh.update()
    return blender_object


def create_mesh(
    name: str,
    vertices: List[Tuple[float, float, float]],
    faces: List[List[int]],
) -> bpy.types.Mesh:
    """
    Create a new Blender mesh from vertices and faces.

    :param name: Name for the mesh.
    :param vertices: Vertices to assign, will be scaled and axis-remapped.
    :param faces: List of faces as vertex index lists.
    :return: Created Blender mesh.
    """
    blender_mesh = bpy.data.meshes.new(name)
    # Change scale (1/100) and swap Y/Z axes for Blender coordinate system
    transformed_vertices: List[Tuple[float, float, float]] = [tuple() for _ in vertices]  # type: ignore
    for i, vertex in enumerate(vertices):
        scaled = tuple(v / 100 for v in vertex)
        transformed_vertices[i] = (scaled[0], scaled[2], scaled[1])
    blender_mesh.from_pydata(transformed_vertices, [], faces)
    blender_mesh.update()
    return blender_mesh


def create_blender_object(name: str, blender_mesh: bpy.types.Mesh) -> bpy.types.Object:
    """
    Create a new Blender object with a linked mesh.

    :param name: Name for the object.
    :param blender_mesh: Mesh to link.
    :return: Created Blender object.
    """
    blender_object = bpy.data.objects.new(name, blender_mesh)
    # Blender 2.8+
    if bpy.app.version >= (2, 8):
        bpy.context.collection.objects.link(blender_object)
    else:
        # Blender <2.8
        bpy.context.scene.objects.link(blender_object)
    return blender_object


def create_texture_layer(
    blender_mesh: bpy.types.Mesh,
    uv: List[List[float]],
    material_list: List[int],
    face_materials: List[int],
    blender_materials: Dict[int, bpy.types.Material],
) -> None:
    """
    Assign UV mapping and materials to a mesh.

    :param blender_mesh: Mesh to modify.
    :param uv: UV coordinates per vertex.
    :param material_list: List of material IDs.
    :param face_materials: Material index for each face.
    :param blender_materials: Blender material objects by ID.
    """
    # Add the materials to the mesh
    for mat_id in material_list:
        blender_mesh.materials.append(blender_materials[mat_id])
    if bpy.app.version < (2, 8):
        blender_mesh.uv_textures.new("UV0")
    blender_mesh.update()

    # Create an empty BMesh
    blender_b_mesh = bmesh.new()
    blender_b_mesh.from_mesh(blender_mesh)

    # Assign UVs
    uv_layer = blender_b_mesh.loops.layers.uv["UV0"]
    blender_b_mesh.faces.ensure_lookup_table()
    for face in blender_b_mesh.faces:
        for loop in face.loops:
            loop[uv_layer].uv = uv[loop.vert.index]
        face.material_index = face_materials[face.index]
    blender_b_mesh.to_mesh(blender_mesh)
    blender_mesh.update()


def set_normals(normals: List[List[float]], mesh_part: bpy.types.Mesh) -> None:
    """
    Set custom normals on a mesh.

    :param normals: Normal vectors per vertex.
    :param mesh_part: Mesh to set normals on.
    """
    mesh_part.update(calc_edges=True)

    cl_normals = array.array("f", [0.0] * (len(mesh_part.loops) * 3))
    mesh_part.loops.foreach_get("normal", cl_normals)
    mesh_part.polygons.foreach_set("use_smooth", [True] * len(mesh_part.polygons))

    mesh_part.normals_split_custom_set_from_vertices(normals)

    # use_auto_smooth removed in Blender 4.1+
    if bpy.app.version < (4, 1):
        mesh_part.use_auto_smooth = True

    # Setting is True by default on Blender 2.8+
    if bpy.app.version < (2, 8):
        # Blender 2.7x
        mesh_part.show_edge_sharp = True


def set_weights(
    weights: Dict[int, List[Tuple[int, float]]],
    remap: List[int],
    mesh_obj: bpy.types.Object,
) -> None:
    """
    Set vertex weights for skeletal animation.

    :param weights: Dict of bone_id -> [(vertex_id, weight)].
    :param remap: Mapping of local bone indices to skeleton IDs.
    :param mesh_obj: Blender object to add vertex groups to.
    """
    for mesh_bone_ix, group in weights.items():
        group_ix = remap[mesh_bone_ix]
        group_id = "%03d" % group_ix if isinstance(group_ix, int) else str(group_ix)
        group_name = f"Bone.{group_id}"
        for vertex, weight in group:
            if group_name not in mesh_obj.vertex_groups:
                mesh_obj.vertex_groups.new(name=group_name)
            mesh_obj.vertex_groups[group_name].add([vertex], weight, "ADD")
