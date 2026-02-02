# -*- coding: utf-8 -*-
"""
Stage directory import for unpacked stage files.

Handles importing FMOD and JKR files from unpacked stage directories.
"""

from pathlib import Path
from typing import Callable, List, Optional

import bpy

from ..stage.jkr_decompress import decompress_jkr
from ..logging_config import get_logger

_logger = get_logger("stage")


def import_unpacked_stage(
    stage_dir: Path,
    import_textures: bool,
    create_collection: bool,
    import_fmod_file_func: Callable,
    import_jkr_file_func: Callable,
) -> List[bpy.types.Object]:
    """
    Import an unpacked stage directory.

    Looks for .fmod and .jkr files in the directory.

    :param stage_dir: Path to the unpacked stage directory.
    :param import_textures: Import textures if available.
    :param create_collection: Create a collection for the stage objects.
    :param import_fmod_file_func: Function to import FMOD files.
    :param import_jkr_file_func: Function to import JKR files.
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

    _logger.info(f"Found {len(fmod_files)} FMOD files, {len(jkr_files)} JKR files")

    # Import FMOD files directly
    for fmod_file in fmod_files:
        try:
            objects = import_fmod_file_func(fmod_file, import_textures, collection)
            imported_objects.extend(objects)
        except Exception as e:
            _logger.error(f"Error importing {fmod_file.name}: {e}")

    # Import JKR files (decompress first)
    for jkr_file in jkr_files:
        try:
            objects = import_jkr_file_func(jkr_file, import_textures, collection)
            imported_objects.extend(objects)
        except Exception as e:
            _logger.error(f"Error importing {jkr_file.name}: {e}")

    return imported_objects


def import_fmod_file(
    fmod_path: Path,
    import_textures: bool,
    collection: Optional[bpy.types.Collection],
    import_fmod_from_bytes_func: Callable,
) -> List[bpy.types.Object]:
    """
    Import a single FMOD file.

    :param fmod_path: Path to the FMOD file.
    :param import_textures: Import textures if available.
    :param collection: Collection to add objects to.
    :param import_fmod_from_bytes_func: Function to import FMOD data from bytes.
    :return: List of imported Blender objects.
    """
    with open(fmod_path, "rb") as f:
        data = f.read()

    return import_fmod_from_bytes_func(
        data, fmod_path.stem, import_textures, collection, str(fmod_path)
    )


def import_jkr_file(
    jkr_path: Path,
    import_textures: bool,
    collection: Optional[bpy.types.Collection],
    import_fmod_from_bytes_func: Callable,
) -> List[bpy.types.Object]:
    """
    Import a JKR compressed file (decompress and import as FMOD).

    If the file is not actually JKR-compressed (no JKR magic), tries to
    import it directly as FMOD data.

    :param jkr_path: Path to the JKR file.
    :param import_textures: Import textures if available.
    :param collection: Collection to add objects to.
    :param import_fmod_from_bytes_func: Function to import FMOD data from bytes.
    :return: List of imported Blender objects.
    """
    with open(jkr_path, "rb") as f:
        data = f.read()

    # Try to decompress - returns None if not JKR format
    decompressed = decompress_jkr(data)

    if decompressed is None:
        # Not JKR compressed - try using the raw data as FMOD
        _logger.info(f"{jkr_path.name} is not JKR-compressed, trying as raw FMOD")
        decompressed = data

    return import_fmod_from_bytes_func(
        decompressed, jkr_path.stem, import_textures, collection
    )
