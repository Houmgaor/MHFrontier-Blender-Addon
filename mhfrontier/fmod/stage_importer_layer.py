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
from ..blender.api import SceneManager, MaterialBuilder, MeshBuilder, ObjectBuilder


def _get_default_builders():
    """Get default Blender builders (lazy import to avoid Blender dependency at import time)."""
    from ..blender.blender_impl import (
        get_scene_manager,
        get_material_builder,
        get_mesh_builder,
        get_object_builder,
    )

    return (
        get_scene_manager(),
        get_material_builder(),
        get_mesh_builder(),
        get_object_builder(),
    )


def import_stage(
    stage_path: str,
    import_textures: bool = True,
    clear_scene: bool = True,
    create_collection: bool = True,
    import_audio: bool = True,
    scene_manager: Optional[SceneManager] = None,
    material_builder: Optional[MaterialBuilder] = None,
    mesh_builder: Optional[MeshBuilder] = None,
    object_builder: Optional[ObjectBuilder] = None,
) -> List[Any]:
    """
    Import a stage/map file into Blender.

    :param stage_path: Path to the stage .pac file or unpacked directory.
    :param import_textures: Import textures if available.
    :param clear_scene: Clear scene before import.
    :param create_collection: Create a collection for the stage objects.
    :param import_audio: Import audio files (OGG) if available.
    :param scene_manager: Optional scene manager (defaults to Blender implementation).
    :param material_builder: Optional material builder (defaults to Blender implementation).
    :param mesh_builder: Optional mesh builder (defaults to Blender implementation).
    :param object_builder: Optional object builder (defaults to Blender implementation).
    :return: List of imported Blender objects.
    """
    if scene_manager is None:
        scene_manager, material_builder, mesh_builder, object_builder = (
            _get_default_builders()
        )

    if clear_scene:
        fmod_importer_layer.clear_scene(scene_manager)

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
            scene_manager,
            material_builder,
            mesh_builder,
            object_builder,
        )

    # Check if this is a directory (unpacked) or a file (packed)
    if stage_path.is_dir():
        return import_unpacked_stage(
            stage_path,
            import_textures,
            create_collection,
            scene_manager,
            material_builder,
            mesh_builder,
            object_builder,
        )
    else:
        return import_packed_stage(
            stage_path,
            import_textures,
            create_collection,
            fmod_from_bytes_with_builders,
            import_audio,
            scene_manager,
        )


def import_unpacked_stage(
    stage_dir: Path,
    import_textures: bool,
    create_collection: bool,
    scene_manager: Optional[SceneManager] = None,
    material_builder: Optional[MaterialBuilder] = None,
    mesh_builder: Optional[MeshBuilder] = None,
    object_builder: Optional[ObjectBuilder] = None,
) -> List[Any]:
    """
    Import an unpacked stage directory.

    :param stage_dir: Path to the unpacked stage directory.
    :param import_textures: Import textures if available.
    :param create_collection: Create a collection for the stage objects.
    :param scene_manager: Optional scene manager (defaults to Blender implementation).
    :param material_builder: Optional material builder (defaults to Blender implementation).
    :param mesh_builder: Optional mesh builder (defaults to Blender implementation).
    :param object_builder: Optional object builder (defaults to Blender implementation).
    :return: List of imported Blender objects.
    """
    if scene_manager is None:
        scene_manager, material_builder, mesh_builder, object_builder = (
            _get_default_builders()
        )

    # Create closures that capture the builders
    def fmod_file_func(fmod_path, import_tex, collection):
        return import_fmod_file(
            fmod_path,
            import_tex,
            collection,
            scene_manager,
            material_builder,
            mesh_builder,
            object_builder,
        )

    def jkr_file_func(jkr_path, import_tex, collection):
        return import_jkr_file(
            jkr_path,
            import_tex,
            collection,
            scene_manager,
            material_builder,
            mesh_builder,
            object_builder,
        )

    return _import_unpacked_stage(
        stage_dir,
        import_textures,
        create_collection,
        fmod_file_func,
        jkr_file_func,
        scene_manager,
    )


def import_fmod_file(
    fmod_path: Path,
    import_textures: bool,
    collection: Optional[Any] = None,
    scene_manager: Optional[SceneManager] = None,
    material_builder: Optional[MaterialBuilder] = None,
    mesh_builder: Optional[MeshBuilder] = None,
    object_builder: Optional[ObjectBuilder] = None,
) -> List[Any]:
    """
    Import a single FMOD file.

    :param fmod_path: Path to the FMOD file.
    :param import_textures: Import textures if available.
    :param collection: Collection to add objects to.
    :param scene_manager: Optional scene manager (defaults to Blender implementation).
    :param material_builder: Optional material builder (defaults to Blender implementation).
    :param mesh_builder: Optional mesh builder (defaults to Blender implementation).
    :param object_builder: Optional object builder (defaults to Blender implementation).
    :return: List of imported Blender objects.
    """
    if scene_manager is None:
        scene_manager, material_builder, mesh_builder, object_builder = (
            _get_default_builders()
        )

    def fmod_from_bytes_func(data, name, import_tex, coll, texture_path=None):
        return import_fmod_from_bytes(
            data,
            name,
            import_tex,
            coll,
            texture_path,
            scene_manager,
            material_builder,
            mesh_builder,
            object_builder,
        )

    return _import_fmod_file(
        fmod_path, import_textures, collection, fmod_from_bytes_func
    )


def import_jkr_file(
    jkr_path: Path,
    import_textures: bool,
    collection: Optional[Any] = None,
    scene_manager: Optional[SceneManager] = None,
    material_builder: Optional[MaterialBuilder] = None,
    mesh_builder: Optional[MeshBuilder] = None,
    object_builder: Optional[ObjectBuilder] = None,
) -> List[Any]:
    """
    Import a JKR compressed file (decompress and import as FMOD).

    :param jkr_path: Path to the JKR file.
    :param import_textures: Import textures if available.
    :param collection: Collection to add objects to.
    :param scene_manager: Optional scene manager (defaults to Blender implementation).
    :param material_builder: Optional material builder (defaults to Blender implementation).
    :param mesh_builder: Optional mesh builder (defaults to Blender implementation).
    :param object_builder: Optional object builder (defaults to Blender implementation).
    :return: List of imported Blender objects.
    """
    if scene_manager is None:
        scene_manager, material_builder, mesh_builder, object_builder = (
            _get_default_builders()
        )

    def fmod_from_bytes_func(data, name, import_tex, coll, texture_path=None):
        return import_fmod_from_bytes(
            data,
            name,
            import_tex,
            coll,
            texture_path,
            scene_manager,
            material_builder,
            mesh_builder,
            object_builder,
        )

    return _import_jkr_file(jkr_path, import_textures, collection, fmod_from_bytes_func)


def import_fmod_from_bytes(
    data: bytes,
    name: str,
    import_textures: bool,
    collection: Optional[Any] = None,
    texture_search_path: Optional[str] = None,
    scene_manager: Optional[SceneManager] = None,
    material_builder: Optional[MaterialBuilder] = None,
    mesh_builder: Optional[MeshBuilder] = None,
    object_builder: Optional[ObjectBuilder] = None,
) -> List[Any]:
    """
    Import FMOD data from bytes.

    :param data: Raw FMOD file data.
    :param name: Name prefix for imported objects.
    :param import_textures: Import textures if available.
    :param collection: Collection to add objects to.
    :param texture_search_path: Path to search for textures.
    :param scene_manager: Optional scene manager (defaults to Blender implementation).
    :param material_builder: Optional material builder (defaults to Blender implementation).
    :param mesh_builder: Optional mesh builder (defaults to Blender implementation).
    :param object_builder: Optional object builder (defaults to Blender implementation).
    :return: List of imported Blender objects.
    """
    if scene_manager is None:
        scene_manager, material_builder, mesh_builder, object_builder = (
            _get_default_builders()
        )

    scene_manager.set_render_engine("CYCLES")

    meshes, materials = fmod.load_fmod_file_from_bytes(data, verbose=False)

    imported_objects: List[Any] = []

    # Create materials
    blender_materials = {}
    for mesh in meshes:
        for mat_id in mesh.material_list:
            if mat_id not in blender_materials:
                blender_materials[mat_id] = material_builder.create_material(
                    name=f"{name}_Material-{mat_id:03d}"
                )

    # Create meshes
    for ix, mesh in enumerate(meshes):
        obj = import_mesh_part(
            ix, mesh, name, blender_materials, mesh_builder, object_builder
        )
        imported_objects.append(obj)

        # Move to collection if specified
        if collection is not None:
            scene_manager.unlink_object_from_collections(obj)
            scene_manager.link_object_to_collection(obj, collection)

    # Import textures if requested and path provided
    if import_textures and texture_search_path:
        from .material_importer import import_textures as do_import_textures

        do_import_textures(materials, texture_search_path, blender_materials)

    return imported_objects


def import_mesh_part(
    index: int,
    mesh: Any,
    name_prefix: str,
    blender_materials: dict,
    mesh_builder: Optional[MeshBuilder] = None,
    object_builder: Optional[ObjectBuilder] = None,
) -> Any:
    """
    Import a single mesh part.

    :param index: Mesh index.
    :param mesh: FMesh object.
    :param name_prefix: Prefix for object name.
    :param blender_materials: Material dictionary.
    :param mesh_builder: Optional mesh builder (defaults to Blender implementation).
    :param object_builder: Optional object builder (defaults to Blender implementation).
    :return: Created Blender object.
    """
    if mesh_builder is None or object_builder is None:
        _, _, mesh_builder, object_builder = _get_default_builders()

    object_builder.deselect_all()

    object_name = f"{name_prefix}_Part_{index:03d}"
    blender_mesh = create_mesh(object_name, mesh.vertices, mesh.faces, mesh_builder)
    blender_object = create_blender_object(object_name, blender_mesh, object_builder)

    # Normals
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
        if mesh.bone_remap is None:
            mesh.bone_remap = list(range(max(mesh.weights.keys()) + 1))
        set_weights(mesh.weights, mesh.bone_remap, blender_object, object_builder)

    mesh_builder.update_mesh(blender_mesh)
    return blender_object
