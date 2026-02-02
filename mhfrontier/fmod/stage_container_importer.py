# -*- coding: utf-8 -*-
"""
Stage container import for packed .pac files.

Handles parsing and importing segments from packed stage containers.
"""

import tempfile
from pathlib import Path
from typing import Any, Callable, List, Optional

from ..stage.jkr_decompress import decompress_jkr
from ..stage.stage_container import (
    parse_stage_container,
    StageSegment,
    SegmentType,
    get_fmod_segments,
    get_texture_segments,
    get_audio_segments,
)
from ..blender.api import SceneManager
from ..logging_config import get_logger

_logger = get_logger("stage")


def _get_default_scene_manager() -> SceneManager:
    """Get default Blender scene manager (lazy import)."""
    from ..blender.blender_impl import get_scene_manager

    return get_scene_manager()


def import_packed_stage(
    stage_path: Path,
    import_textures: bool,
    create_collection: bool,
    import_fmod_from_bytes_func: Callable,
    import_audio: bool = True,
    scene_manager: Optional[SceneManager] = None,
) -> List[Any]:
    """
    Import a packed stage container file.

    :param stage_path: Path to the stage .pac file.
    :param import_textures: Import textures if available.
    :param create_collection: Create a collection for the stage objects.
    :param import_fmod_from_bytes_func: Function to import FMOD data from bytes.
    :param import_audio: Import audio files (OGG) if available.
    :param scene_manager: Optional scene manager (defaults to Blender implementation).
    :return: List of imported Blender objects.
    """
    with open(stage_path, "rb") as f:
        data = f.read()

    segments = parse_stage_container(data)
    _logger.info(f"Parsed stage container: {len(segments)} segments")

    return import_segments(
        segments,
        stage_path.stem,
        import_textures,
        create_collection,
        import_fmod_from_bytes_func,
        import_audio,
        scene_manager,
    )


def import_segments(
    segments: List[StageSegment],
    stage_name: str,
    import_textures: bool,
    create_collection: bool,
    import_fmod_from_bytes_func: Callable,
    import_audio: bool = True,
    scene_manager: Optional[SceneManager] = None,
) -> List[Any]:
    """
    Import segments from a parsed stage container.

    :param segments: List of parsed segments.
    :param stage_name: Name for the stage (used for collection).
    :param import_textures: Import textures if available.
    :param create_collection: Create a collection for the stage objects.
    :param import_fmod_from_bytes_func: Function to import FMOD data from bytes.
    :param import_audio: Import audio files (OGG) if available.
    :param scene_manager: Optional scene manager (defaults to Blender implementation).
    :return: List of imported Blender objects.
    """
    if scene_manager is None:
        scene_manager = _get_default_scene_manager()

    imported_objects: List[Any] = []
    collection = None

    if create_collection:
        collection = scene_manager.create_collection(stage_name)
        scene_manager.link_collection_to_scene(collection)

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
                    _logger.warning(f"Failed to decompress segment {segment.index}")
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
                    _logger.warning(
                        f"Segment {segment.index}: decompressed but couldn't parse as FMOD: {e}"
                    )

            elif segment.segment_type == SegmentType.FMOD:
                objects = import_fmod_from_bytes_func(
                    segment.data,
                    f"Stage_{segment.index:04d}",
                    import_textures,
                    collection,
                )
                imported_objects.extend(objects)

        except Exception as e:
            _logger.error(f"Error processing segment {segment.index}: {e}")

    # Process audio segments (OGG)
    if import_audio:
        audio_segments = get_audio_segments(segments)
        if audio_segments:
            _logger.info(f"Found {len(audio_segments)} audio segments")

        for segment in audio_segments:
            try:
                sound_name = f"{stage_name}_audio_{segment.index:04d}"

                # Write to temp file (Blender requires file path to load sounds)
                with tempfile.NamedTemporaryFile(
                    suffix=".ogg", delete=False
                ) as tmp_file:
                    tmp_file.write(segment.data)
                    tmp_path = tmp_file.name

                # Load sound into Blender
                sound = scene_manager.load_sound(tmp_path)
                scene_manager.set_sound_name(sound, sound_name)

                # Pack the sound data into the blend file so temp file can be deleted
                scene_manager.pack_sound(sound)

                # Clean up temp file
                Path(tmp_path).unlink(missing_ok=True)

                _logger.info(f"Imported audio: {sound_name}")

            except Exception as e:
                _logger.error(f"Error importing audio segment {segment.index}: {e}")

    return imported_objects
