# -*- coding: utf-8 -*-
"""
Mesh import utilities using the abstracted builder interfaces.

Converts parsed mesh data to Blender mesh objects.
"""

from typing import Any, Dict, List, Optional

from ..blender.builders import Builders, get_builders


def import_mesh(
    index: int,
    mesh: Any,
    blender_materials: Dict[int, Any],
    builders: Optional[Builders] = None,
) -> Any:
    """
    Create a Blender mesh from FMOD mesh data.

    :param index: Index of the mesh (for naming).
    :param mesh: FMesh object with geometry data.
    :param blender_materials: Dictionary mapping material IDs to Blender materials.
    :param builders: Optional builders (defaults to Blender implementation).
    :return: Created Blender object.
    """
    if builders is None:
        builders = get_builders()

    builders.object.deselect_all()

    object_name = "FMesh_%03d" % index
    blender_mesh = create_mesh(object_name, mesh.vertices, mesh.faces, builders)
    blender_object = create_blender_object(object_name, blender_mesh, builders)

    # Set normals
    set_normals(mesh.normals, blender_mesh, builders)

    # Create UV layer and apply textures
    if mesh.uvs is not None:
        builders.mesh.create_uv_layer(blender_mesh, "UV0")
        create_texture_layer(
            blender_mesh,
            mesh.uvs,
            mesh.material_list,
            mesh.material_map,
            blender_materials,
            builders,
        )

    # Set bone weights
    if mesh.weights is not None:
        if mesh.bone_remap is None:
            mesh.bone_remap = list(range(max(mesh.weights.keys()) + 1))
        set_weights(mesh.weights, mesh.bone_remap, blender_object, builders)

    builders.mesh.update_mesh(blender_mesh)
    return blender_object


def create_mesh(
    name: str,
    vertices: List,
    faces: List,
    builders: Optional[Builders] = None,
) -> Any:
    """
    Create a new mesh with vertices and faces.

    :param name: Name for the mesh.
    :param vertices: List of vertex positions.
    :param faces: List of face indices.
    :param builders: Optional builders (defaults to Blender implementation).
    :return: Created Blender mesh.
    """
    if builders is None:
        builders = get_builders()

    return builders.mesh.create_mesh(name, vertices, faces)


def create_blender_object(
    name: str,
    mesh: Any,
    builders: Optional[Builders] = None,
) -> Any:
    """
    Create a Blender object from a mesh.

    :param name: Name for the object.
    :param mesh: Blender mesh data.
    :param builders: Optional builders (defaults to Blender implementation).
    :return: Created Blender object.
    """
    if builders is None:
        builders = get_builders()

    blender_object = builders.object.create_object(name, mesh)
    builders.object.link_to_scene(blender_object)
    return blender_object


def create_texture_layer(
    blender_mesh: Any,
    uvs: List,
    material_list: List,
    material_map: Dict,
    blender_materials: Dict[int, Any],
    builders: Optional[Builders] = None,
) -> None:
    """
    Create UV coordinates and assign materials to faces.

    :param blender_mesh: Blender mesh to modify.
    :param uvs: UV coordinate data.
    :param material_list: List of material IDs used.
    :param material_map: Mapping of face indices to material indices.
    :param blender_materials: Dictionary of Blender materials.
    :param builders: Optional builders (defaults to Blender implementation).
    """
    if builders is None:
        builders = get_builders()

    # Add materials to mesh
    for mat_id in material_list:
        builders.mesh.add_material(blender_mesh, blender_materials[mat_id])

    # Map material IDs to local indices
    mat_local_index = {mat_id: i for i, mat_id in enumerate(material_list)}

    # Build face_materials list
    face_materials = []
    for face_idx in range(len(blender_mesh.faces)):
        mat_id = material_map.get(face_idx, material_list[0] if material_list else 0)
        face_materials.append(mat_local_index.get(mat_id, 0))

    # Set UVs and face materials using the API
    builders.mesh.set_uvs(blender_mesh, uvs, face_materials)


def set_normals(
    normals: List,
    blender_mesh: Any,
    builders: Optional[Builders] = None,
) -> None:
    """
    Set custom split normals on the mesh.

    :param normals: List of normal vectors.
    :param blender_mesh: Blender mesh to modify.
    :param builders: Optional builders (defaults to Blender implementation).
    """
    if builders is None:
        builders = get_builders()

    if not normals:
        return

    builders.mesh.set_normals(blender_mesh, normals)


def set_weights(
    weights: Dict,
    bone_remap: List,
    blender_object: Any,
    builders: Optional[Builders] = None,
) -> None:
    """
    Set vertex group weights from bone weight data.

    :param weights: Dictionary of bone_id -> [(vertex_index, weight), ...].
    :param bone_remap: Mapping of internal bone IDs to actual bone IDs.
    :param blender_object: Blender object to add vertex groups to.
    :param builders: Optional builders (defaults to Blender implementation).
    """
    if builders is None:
        builders = get_builders()

    for bone_id, vertex_weights in weights.items():
        # Get the remapped bone ID
        actual_bone_id = bone_remap[bone_id] if bone_id < len(bone_remap) else bone_id
        group_name = "Bone.%03d" % actual_bone_id

        # Create vertex group and add weights
        builders.object.create_vertex_group(blender_object, group_name)
        for vert_idx, weight in vertex_weights:
            builders.object.add_vertex_weight(blender_object, group_name, vert_idx, weight)
