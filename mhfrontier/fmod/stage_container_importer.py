# -*- coding: utf-8 -*-
"""
Stage container import for packed .pac files.

Handles parsing and importing segments from packed stage containers.
"""

from typing import List, Optional

import bpy

from ..stage.jkr_decompress import decompress_jkr
from ..stage.stage_container import (
    parse_stage_container,
    StageSegment,
    SegmentType,
    get_fmod_segments,
    get_texture_segments,
)


def import_packed_stage(
    stage_path,
    import_textures: bool,
    create_collection: bool,
    import_fmod_from_bytes_func,
) -> List[bpy.types.Object]:
    """
    Import a packed stage container file.

    :param stage_path: Path to the stage .pac file.
    :param import_textures: Import textures if available.
    :param create_collection: Create a collection for the stage objects.
    :param import_fmod_from_bytes_func: Function to import FMOD data from bytes.
    :return: List of imported Blender objects.
    """
    with open(stage_path, "rb") as f:
        data = f.read()

    segments = parse_stage_container(data)
    print(f"Parsed stage container: {len(segments)} segments")

    return import_segments(
        segments,
        stage_path.stem,
        import_textures,
        create_collection,
        import_fmod_from_bytes_func,
    )


def import_segments(
    segments: List[StageSegment],
    stage_name: str,
    import_textures: bool,
    create_collection: bool,
    import_fmod_from_bytes_func,
) -> List[bpy.types.Object]:
    """
    Import segments from a parsed stage container.

    :param segments: List of parsed segments.
    :param stage_name: Name for the stage (used for collection).
    :param import_textures: Import textures if available.
    :param create_collection: Create a collection for the stage objects.
    :param import_fmod_from_bytes_func: Function to import FMOD data from bytes.
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

                # Try to import as FMOD
                try:
                    objects = import_fmod_from_bytes_func(
                        decompressed,
                        f"Stage_{segment.index:04d}",
                        import_textures,
                        collection,
                    )
                    imported_objects.extend(objects)
                except Exception as e:
                    print(f"Segment {segment.index}: decompressed but couldn't parse as FMOD: {e}")

            elif segment.segment_type == SegmentType.FMOD:
                objects = import_fmod_from_bytes_func(
                    segment.data,
                    f"Stage_{segment.index:04d}",
                    import_textures,
                    collection,
                )
                imported_objects.extend(objects)

        except Exception as e:
            print(f"Error processing segment {segment.index}: {e}")

    return imported_objects
