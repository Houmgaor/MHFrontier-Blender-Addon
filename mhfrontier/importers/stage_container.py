# -*- coding: utf-8 -*-
"""
Stage container import for packed .pac files.

Mirrors MHBridge's collect_assets / collect_bundles recursive descent:
  fully_unwrap → try FMOD → try PNG → try stage_container → try PAC archive
"""

import struct
from pathlib import Path
from typing import Any, Callable, List, Optional

from ..stage.stage_container import (
    parse_stage_container,
    fully_unwrap,
    is_stage_container,
)
from ..stage.pac import is_pac_archive, parse_pac
from ..blender.builders import Builders, get_builders
from ..logging_config import get_logger

_logger = get_logger("stage")

_PNG_MAGIC = b"\x89PNG"
_FMOD_FILE_BLOCK_TYPE = 0x00000001  # FileBlock — first 4 bytes of every FMOD file
_MAX_DEPTH = 8


def _is_png(data: bytes) -> bool:
    return len(data) >= 4 and data[:4] == _PNG_MAGIC


def _is_fmod_block(data: bytes) -> bool:
    """
    Check if data is an FMOD file by looking for FileBlock (type 0x00000001).

    FMOD files start with a 12-byte block header:
      - block_type (4 bytes): 0x00000001 for FileBlock
      - count      (4 bytes): number of child blocks (often small or negative)
      - size       (4 bytes): total block size == len(data) for well-formed files

    A PAC archive with count=1 also starts with 0x00000001, but its 'size' field
    (bytes 8-11) is the payload size, not the total file size, so the equality
    check discriminates them in practice.
    """
    if len(data) < 12:
        return False
    block_type = struct.unpack_from("<I", data, 0)[0]
    if block_type != _FMOD_FILE_BLOCK_TYPE:
        return False
    block_size = struct.unpack_from("<I", data, 8)[0]
    return block_size == len(data)


def _collect_fmod_blobs(data: bytes, depth: int) -> List[bytes]:
    """
    Recursively collect raw FMOD blobs from a data blob.

    Mirrors MHBridge collect_assets():
      1. fully_unwrap (decrypt ECD/EXF, decompress JKR)
      2. try FMOD block (FileBlock type 0x00000001 with matching size)
      3. try PNG (skip — no geometry)
      4. try stage_container → recurse into segments
      5. try PAC archive → recurse into entries
    """
    if depth > _MAX_DEPTH or len(data) < 12:
        return []

    blob = fully_unwrap(data)

    # FMOD model: FileBlock with matching total size
    if _is_fmod_block(blob):
        return [blob]

    # PNG texture — skip
    if _is_png(blob):
        return []

    results = []

    # Stage container (must check before PAC — no magic bytes, heuristic only)
    if is_stage_container(blob):
        segments = parse_stage_container(blob)
        _logger.debug(f"[depth={depth}] stage_container: {len(segments)} segments")
        for seg in segments:
            if seg.size == 0:
                continue
            results.extend(_collect_fmod_blobs(seg.data, depth + 1))
        return results

    # PAC archive
    if is_pac_archive(blob):
        pac = parse_pac(blob)
        if pac is None:
            return []
        _logger.debug(f"[depth={depth}] PAC: {len(pac.entries)} entries")
        for i in range(len(pac.entries)):
            entry_data = pac.extract(i)
            if not entry_data:
                continue
            results.extend(_collect_fmod_blobs(entry_data, depth + 1))
        return results

    return []


def import_packed_stage(
    stage_path: Path,
    import_textures: bool,
    create_collection: bool,
    import_fmod_from_bytes_func: Callable,
    import_audio: bool = True,
    builders: Optional[Builders] = None,
) -> List[Any]:
    """
    Import a packed stage .pac file.

    Recursively descends through PAC archives and stage containers to find
    FMOD models, mirroring MHBridge's collect_model_bundles / collect_assets.

    :param stage_path: Path to the stage .pac file.
    :param import_textures: Import textures if available.
    :param create_collection: Create a collection for the stage objects.
    :param import_fmod_from_bytes_func: Function to import FMOD data from bytes.
    :param import_audio: Unused (kept for API compatibility).
    :param builders: Optional builders (defaults to Blender implementation).
    :return: List of imported Blender objects.
    """
    if builders is None:
        builders = get_builders()

    with open(stage_path, "rb") as f:
        raw = f.read()

    fmod_blobs = _collect_fmod_blobs(raw, depth=0)
    _logger.info(f"Found {len(fmod_blobs)} FMOD blobs in {stage_path.name}")

    if not fmod_blobs:
        _logger.warning(f"No FMOD models found in {stage_path}")
        return []

    collection = None
    if create_collection:
        collection = builders.scene.create_collection(stage_path.stem)
        builders.scene.link_collection_to_scene(collection)

    imported_objects: List[Any] = []
    for i, blob in enumerate(fmod_blobs):
        try:
            objects = import_fmod_from_bytes_func(
                blob,
                f"Stage_{i:04d}",
                import_textures,
                collection,
            )
            imported_objects.extend(objects)
        except Exception as e:
            _logger.error(f"FMOD blob {i}: import failed: {e}")

    return imported_objects
