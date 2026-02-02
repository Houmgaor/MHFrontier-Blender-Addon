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
from typing import Any, List, Optional

from ..fmod import fmod
from ..blender.builders import Builders, get_builders
from .mesh import (
    create_mesh,
    create_blender_object,
    set_normals,
    create_texture_layer,
    set_weights,
)
from .stage_container import import_packed_stage, import_segments
from .stage_directory import (
    import_unpacked_stage as _import_unpacked_stage,
    import_fmod_file as _import_fmod_file,
    import_jkr_file as _import_jkr_file,
)


def import_stage(
    stage_path: str,
    import_textures: bool = True,
    clear_scene: bool = True,
    create_collection: bool = True,
    import_audio: bool = True,
    builders: Optional[Builders] = None,
) -> List[Any]:
    """
    Import a stage/map file into Blender.

    :param stage_path: Path to the stage .pac file or unpacked directory.
    :param import_textures: Import textures if available.
    :param clear_scene: Clear scene before import.
    :param create_collection: Create a collection for the stage objects.
    :param import_audio: Import audio files (OGG) if available.
    :param builders: Optional builders (defaults to Blender implementation).
    :return: List of imported Blender objects.
    """
    if builders is None:
        builders = get_builders()

    if clear_scene:
        builders.scene.clear_scene()

    stage_path = Path(stage_path)

    # Create a closure that captures the builders
    def fmod_from_bytes_with_builders(
        data: bytes,
        name: str,
        import_tex: bool,
        collection: Optional[Any],
        texture_search_path: Optional[str] = None,
    ) -> List[Any]:
        return import_fmod_from_bytes(
            data,
            name,
            import_tex,
            collection,
            texture_search_path,
            builders,
        )

    # Check if this is a directory (unpacked) or a file (packed)
    if stage_path.is_dir():
        return import_unpacked_stage(
            stage_path,
            import_textures,
            create_collection,
            builders,
        )
    else:
        return import_packed_stage(
            stage_path,
            import_textures,
            create_collection,
            fmod_from_bytes_with_builders,
            import_audio,
            builders,
        )


def import_unpacked_stage(
    stage_dir: Path,
    import_textures: bool,
    create_collection: bool,
    builders: Optional[Builders] = None,
) -> List[Any]:
    """
    Import an unpacked stage directory.

    :param stage_dir: Path to the unpacked stage directory.
    :param import_textures: Import textures if available.
    :param create_collection: Create a collection for the stage objects.
    :param builders: Optional builders (defaults to Blender implementation).
    :return: List of imported Blender objects.
    """
    if builders is None:
        builders = get_builders()

    # Create closures that capture the builders
    def fmod_file_func(fmod_path, import_tex, collection):
        return import_fmod_file(
            fmod_path,
            import_tex,
            collection,
            builders,
        )

    def jkr_file_func(jkr_path, import_tex, collection):
        return import_jkr_file(
            jkr_path,
            import_tex,
            collection,
            builders,
        )

    return _import_unpacked_stage(
        stage_dir,
        import_textures,
        create_collection,
        fmod_file_func,
        jkr_file_func,
        builders,
    )


def import_fmod_file(
    fmod_path: Path,
    import_textures: bool,
    collection: Optional[Any] = None,
    builders: Optional[Builders] = None,
) -> List[Any]:
    """
    Import a single FMOD file.

    :param fmod_path: Path to the FMOD file.
    :param import_textures: Import textures if available.
    :param collection: Collection to add objects to.
    :param builders: Optional builders (defaults to Blender implementation).
    :return: List of imported Blender objects.
    """
    if builders is None:
        builders = get_builders()

    def fmod_from_bytes_func(data, name, import_tex, coll, texture_path=None):
        return import_fmod_from_bytes(
            data,
            name,
            import_tex,
            coll,
            texture_path,
            builders,
        )

    return _import_fmod_file(
        fmod_path, import_textures, collection, fmod_from_bytes_func
    )


def import_jkr_file(
    jkr_path: Path,
    import_textures: bool,
    collection: Optional[Any] = None,
    builders: Optional[Builders] = None,
) -> List[Any]:
    """
    Import a JKR compressed file (decompress and import as FMOD).

    :param jkr_path: Path to the JKR file.
    :param import_textures: Import textures if available.
    :param collection: Collection to add objects to.
    :param builders: Optional builders (defaults to Blender implementation).
    :return: List of imported Blender objects.
    """
    if builders is None:
        builders = get_builders()

    def fmod_from_bytes_func(data, name, import_tex, coll, texture_path=None):
        return import_fmod_from_bytes(
            data,
            name,
            import_tex,
            coll,
            texture_path,
            builders,
        )

    return _import_jkr_file(jkr_path, import_textures, collection, fmod_from_bytes_func)


def import_fmod_from_bytes(
    data: bytes,
    name: str,
    import_textures: bool,
    collection: Optional[Any] = None,
    texture_search_path: Optional[str] = None,
    builders: Optional[Builders] = None,
) -> List[Any]:
    """
    Import FMOD data from bytes.

    :param data: Raw FMOD file data.
    :param name: Name prefix for imported objects.
    :param import_textures: Import textures if available.
    :param collection: Collection to add objects to.
    :param texture_search_path: Path to search for textures.
    :param builders: Optional builders (defaults to Blender implementation).
    :return: List of imported Blender objects.
    """
    if builders is None:
        builders = get_builders()

    builders.scene.set_render_engine("CYCLES")

    meshes, materials = fmod.load_fmod_file_from_bytes(data, verbose=False)

    imported_objects: List[Any] = []

    # Create materials
    blender_materials = {}
    for mesh in meshes:
        for mat_id in mesh.material_list:
            if mat_id not in blender_materials:
                blender_materials[mat_id] = builders.material.create_material(
                    name=f"{name}_Material-{mat_id:03d}"
                )

    # Create meshes
    for ix, mesh in enumerate(meshes):
        obj = import_mesh_part(
            ix, mesh, name, blender_materials, builders
        )
        imported_objects.append(obj)

        # Move to collection if specified
        if collection is not None:
            builders.scene.unlink_object_from_collections(obj)
            builders.scene.link_object_to_collection(obj, collection)

    # Import textures if requested and path provided
    if import_textures and texture_search_path:
        from .material import import_textures as do_import_textures

        do_import_textures(materials, texture_search_path, blender_materials, builders)

    return imported_objects


def import_mesh_part(
    index: int,
    mesh: Any,
    name_prefix: str,
    blender_materials: dict,
    builders: Optional[Builders] = None,
) -> Any:
    """
    Import a single mesh part.

    :param index: Mesh index.
    :param mesh: FMesh object.
    :param name_prefix: Prefix for object name.
    :param blender_materials: Material dictionary.
    :param builders: Optional builders (defaults to Blender implementation).
    :return: Created Blender object.
    """
    if builders is None:
        builders = get_builders()

    builders.object.deselect_all()

    object_name = f"{name_prefix}_Part_{index:03d}"
    blender_mesh = create_mesh(object_name, mesh.vertices, mesh.faces, builders)
    blender_object = create_blender_object(object_name, blender_mesh, builders)

    # Normals
    set_normals(mesh.normals, blender_mesh, builders)

    # UVs
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

    # Weights
    if mesh.weights is not None:
        if mesh.bone_remap is None:
            mesh.bone_remap = list(range(max(mesh.weights.keys()) + 1))
        set_weights(mesh.weights, mesh.bone_remap, blender_object, builders)

    builders.mesh.update_mesh(blender_mesh)
    return blender_object
