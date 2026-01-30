# -*- coding: utf-8 -*-
"""
Stage import orchestration layer.

Coordinates the import of MHF stage/map files:
1. Parse stage container
2. Decompress JKR segments
3. Import FMOD meshes
4. Handle textures

Created for MHFrontier stage import support.
"""

import os
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

import bpy

from ..stage.jkr_decompress import decompress_jkr, is_jkr_file
from ..stage.stage_container import (
    parse_stage_container,
    StageSegment,
    SegmentType,
    get_fmod_segments,
    get_texture_segments,
)
from . import fmod
from . import fmod_importer_layer


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
    imported_objects = []

    # Check if this is a directory (unpacked) or a file (packed)
    if stage_path.is_dir():
        imported_objects = import_unpacked_stage(
            stage_path, import_textures, create_collection
        )
    else:
        imported_objects = import_packed_stage(
            stage_path, import_textures, create_collection
        )

    return imported_objects


def import_packed_stage(
    stage_path: Path,
    import_textures: bool,
    create_collection: bool,
) -> List[bpy.types.Object]:
    """
    Import a packed stage container file.

    :param stage_path: Path to the stage .pac file.
    :param import_textures: Import textures if available.
    :param create_collection: Create a collection for the stage objects.
    :return: List of imported Blender objects.
    """
    with open(stage_path, "rb") as f:
        data = f.read()

    segments = parse_stage_container(data)
    print(f"Parsed stage container: {len(segments)} segments")

    return import_segments(
        segments, stage_path.stem, import_textures, create_collection
    )


def import_unpacked_stage(
    stage_dir: Path,
    import_textures: bool,
    create_collection: bool,
) -> List[bpy.types.Object]:
    """
    Import an unpacked stage directory.

    Looks for .fmod and .jkr files in the directory.

    :param stage_dir: Path to the unpacked stage directory.
    :param import_textures: Import textures if available.
    :param create_collection: Create a collection for the stage objects.
    :return: List of imported Blender objects.
    """
    imported_objects = []
    collection = None

    if create_collection:
        collection = bpy.data.collections.new(stage_dir.name)
        bpy.context.scene.collection.children.link(collection)

    # Find all relevant files
    fmod_files = list(stage_dir.glob("*.fmod"))
    jkr_files = list(stage_dir.glob("*.jkr"))

    print(f"Found {len(fmod_files)} FMOD files, {len(jkr_files)} JKR files")

    # Import FMOD files directly
    for fmod_file in fmod_files:
        try:
            objects = import_fmod_file(fmod_file, import_textures, collection)
            imported_objects.extend(objects)
        except Exception as e:
            print(f"Error importing {fmod_file.name}: {e}")

    # Import JKR files (decompress first)
    for jkr_file in jkr_files:
        try:
            objects = import_jkr_file(jkr_file, import_textures, collection)
            imported_objects.extend(objects)
        except Exception as e:
            print(f"Error importing {jkr_file.name}: {e}")

    return imported_objects


def import_segments(
    segments: List[StageSegment],
    stage_name: str,
    import_textures: bool,
    create_collection: bool,
) -> List[bpy.types.Object]:
    """
    Import segments from a parsed stage container.

    :param segments: List of parsed segments.
    :param stage_name: Name for the stage (used for collection).
    :param import_textures: Import textures if available.
    :param create_collection: Create a collection for the stage objects.
    :return: List of imported Blender objects.
    """
    imported_objects = []
    collection = None

    if create_collection:
        collection = bpy.data.collections.new(stage_name)
        bpy.context.scene.collection.children.link(collection)

    # Collect texture data for later use
    texture_data = []
    if import_textures:
        texture_segments = get_texture_segments(segments)
        for seg in texture_segments:
            texture_data.append(seg.data)

    # Process FMOD segments (both direct and compressed)
    fmod_segments = get_fmod_segments(segments)

    for segment in fmod_segments:
        try:
            if segment.segment_type == SegmentType.JKR:
                # Decompress first
                decompressed = decompress_jkr(segment.data)
                if decompressed is None:
                    print(f"Failed to decompress segment {segment.index}")
                    continue

                # Try to import as FMOD (no magic check - FMOD files don't have magic bytes)
                try:
                    objects = import_fmod_from_bytes(
                        decompressed,
                        f"Stage_{segment.index:04d}",
                        import_textures,
                        collection,
                    )
                    imported_objects.extend(objects)
                except Exception as e:
                    print(f"Segment {segment.index}: decompressed but couldn't parse as FMOD: {e}")

            elif segment.segment_type == SegmentType.FMOD:
                objects = import_fmod_from_bytes(
                    segment.data,
                    f"Stage_{segment.index:04d}",
                    import_textures,
                    collection,
                )
                imported_objects.extend(objects)

        except Exception as e:
            print(f"Error processing segment {segment.index}: {e}")

    return imported_objects


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
    with open(fmod_path, "rb") as f:
        data = f.read()

    return import_fmod_from_bytes(
        data, fmod_path.stem, import_textures, collection, str(fmod_path)
    )


def import_jkr_file(
    jkr_path: Path,
    import_textures: bool,
    collection: Optional[bpy.types.Collection] = None,
) -> List[bpy.types.Object]:
    """
    Import a JKR compressed file (decompress and import as FMOD).

    If the file is not actually JKR-compressed (no JKR magic), tries to
    import it directly as FMOD data.

    :param jkr_path: Path to the JKR file.
    :param import_textures: Import textures if available.
    :param collection: Collection to add objects to.
    :return: List of imported Blender objects.
    """
    with open(jkr_path, "rb") as f:
        data = f.read()

    # Try to decompress - returns None if not JKR format
    decompressed = decompress_jkr(data)

    if decompressed is None:
        # Not JKR compressed - try using the raw data as FMOD
        print(f"Note: {jkr_path.name} is not JKR-compressed, trying as raw FMOD")
        decompressed = data

    # Try to import as FMOD (no magic check - FMOD files don't have magic bytes)
    return import_fmod_from_bytes(
        decompressed, jkr_path.stem, import_textures, collection
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

    Adapted from fmod_importer_layer.import_mesh.

    :param index: Mesh index.
    :param mesh: FMesh object.
    :param name_prefix: Prefix for object name.
    :param blender_materials: Material dictionary.
    :return: Created Blender object.
    """
    bpy.ops.object.select_all(action="DESELECT")

    object_name = f"{name_prefix}_Part_{index:03d}"
    blender_mesh = fmod_importer_layer.create_mesh(
        object_name, mesh.vertices, mesh.faces
    )
    blender_object = fmod_importer_layer.create_blender_object(object_name, blender_mesh)

    # Normals
    fmod_importer_layer.set_normals(mesh.normals, blender_mesh)

    # UVs
    if mesh.uvs is not None:
        if bpy.app.version >= (2, 8):
            blender_object.data.uv_layers.new(name="UV0")
        fmod_importer_layer.create_texture_layer(
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
        fmod_importer_layer.set_weights(mesh.weights, mesh.bone_remap, blender_object)

    blender_mesh.update()
    return blender_object
