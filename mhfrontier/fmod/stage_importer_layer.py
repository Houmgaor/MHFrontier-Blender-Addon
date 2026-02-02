# -*- coding: utf-8 -*-
"""
Stage import orchestration layer.

Coordinates the import of MHF stage/map files:
1. Parse stage container or unpacked directory
2. Decompress JKR segments if needed
3. Import FMOD meshes
4. Handle textures

Created for MHFrontier stage import support.
"""

from pathlib import Path
from typing import List, Optional

import bpy

from . import fmod
from . import fmod_importer_layer
from .mesh_importer import (
    create_mesh,
    create_blender_object,
    set_normals,
    create_texture_layer,
    set_weights,
)
from .stage_container_importer import import_packed_stage, import_segments
from .stage_directory_importer import (
    import_unpacked_stage as _import_unpacked_stage,
    import_fmod_file as _import_fmod_file,
    import_jkr_file as _import_jkr_file,
)


def import_stage(
    stage_path: str,
    import_textures: bool = True,
    clear_scene: bool = True,
    create_collection: bool = True,
) -> List[bpy.types.Object]:
    """
    Import a stage/map file into Blender.

    :param stage_path: Path to the stage .pac file or unpacked directory.
    :param import_textures: Import textures if available.
    :param clear_scene: Clear scene before import.
    :param create_collection: Create a collection for the stage objects.
    :return: List of imported Blender objects.
    """
    if clear_scene:
        fmod_importer_layer.clear_scene()

    stage_path = Path(stage_path)

    # Check if this is a directory (unpacked) or a file (packed)
    if stage_path.is_dir():
        return import_unpacked_stage(stage_path, import_textures, create_collection)
    else:
        return import_packed_stage(
            stage_path,
            import_textures,
            create_collection,
            import_fmod_from_bytes,
        )


def import_unpacked_stage(
    stage_dir: Path,
    import_textures: bool,
    create_collection: bool,
) -> List[bpy.types.Object]:
    """
    Import an unpacked stage directory.

    :param stage_dir: Path to the unpacked stage directory.
    :param import_textures: Import textures if available.
    :param create_collection: Create a collection for the stage objects.
    :return: List of imported Blender objects.
    """
    return _import_unpacked_stage(
        stage_dir,
        import_textures,
        create_collection,
        import_fmod_file,
        import_jkr_file,
    )


def import_fmod_file(
    fmod_path: Path,
    import_textures: bool,
    collection: Optional[bpy.types.Collection] = None,
) -> List[bpy.types.Object]:
    """
    Import a single FMOD file.

    :param fmod_path: Path to the FMOD file.
    :param import_textures: Import textures if available.
    :param collection: Collection to add objects to.
    :return: List of imported Blender objects.
    """
    return _import_fmod_file(
        fmod_path, import_textures, collection, import_fmod_from_bytes
    )


def import_jkr_file(
    jkr_path: Path,
    import_textures: bool,
    collection: Optional[bpy.types.Collection] = None,
) -> List[bpy.types.Object]:
    """
    Import a JKR compressed file (decompress and import as FMOD).

    :param jkr_path: Path to the JKR file.
    :param import_textures: Import textures if available.
    :param collection: Collection to add objects to.
    :return: List of imported Blender objects.
    """
    return _import_jkr_file(
        jkr_path, import_textures, collection, import_fmod_from_bytes
    )


def import_fmod_from_bytes(
    data: bytes,
    name: str,
    import_textures: bool,
    collection: Optional[bpy.types.Collection] = None,
    texture_search_path: Optional[str] = None,
) -> List[bpy.types.Object]:
    """
    Import FMOD data from bytes.

    :param data: Raw FMOD file data.
    :param name: Name prefix for imported objects.
    :param import_textures: Import textures if available.
    :param collection: Collection to add objects to.
    :param texture_search_path: Path to search for textures.
    :return: List of imported Blender objects.
    """
    bpy.context.scene.render.engine = "CYCLES"

    meshes, materials = fmod.load_fmod_file_from_bytes(data, verbose=False)

    imported_objects = []

    # Create materials
    blender_materials = {}
    for mesh in meshes:
        for mat_id in mesh.material_list:
            if mat_id not in blender_materials:
                blender_materials[mat_id] = bpy.data.materials.new(
                    name=f"{name}_Material-{mat_id:03d}"
                )

    # Create meshes
    for ix, mesh in enumerate(meshes):
        obj = import_mesh_part(ix, mesh, name, blender_materials)
        imported_objects.append(obj)

        # Move to collection if specified
        if collection is not None:
            # Remove from default collection
            for coll in obj.users_collection:
                coll.objects.unlink(obj)
            collection.objects.link(obj)

    # Import textures if requested and path provided
    if import_textures and texture_search_path:
        fmod_importer_layer.import_textures(
            materials, texture_search_path, blender_materials
        )

    return imported_objects


def import_mesh_part(
    index: int,
    mesh,
    name_prefix: str,
    blender_materials: dict,
) -> bpy.types.Object:
    """
    Import a single mesh part.

    :param index: Mesh index.
    :param mesh: FMesh object.
    :param name_prefix: Prefix for object name.
    :param blender_materials: Material dictionary.
    :return: Created Blender object.
    """
    bpy.ops.object.select_all(action="DESELECT")

    object_name = f"{name_prefix}_Part_{index:03d}"
    blender_mesh = create_mesh(object_name, mesh.vertices, mesh.faces)
    blender_object = create_blender_object(object_name, blender_mesh)

    # Normals
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
        if mesh.bone_remap is None:
            mesh.bone_remap = list(range(max(mesh.weights.keys()) + 1))
        set_weights(mesh.weights, mesh.bone_remap, blender_object)

    blender_mesh.update()
    return blender_object
