# -*- coding: utf-8 -*-
"""
Stage container import for packed .pac files.

Mirrors MHBridge's collect_assets / collect_bundles recursive descent:
  fully_unwrap → try FMOD → try PNG → try stage_container → try PAC archive
"""

import struct
import tempfile
from dataclasses import dataclass, field
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


@dataclass
class _Assets:
    fmods: List[bytes] = field(default_factory=list)
    pngs: List[bytes] = field(default_factory=list)


def _collect_assets(data: bytes, depth: int) -> _Assets:
    """
    Recursively collect FMOD blobs and PNG texture blobs from a data blob.

    Mirrors MHBridge collect_assets():
      1. fully_unwrap (decrypt ECD/EXF, decompress JKR)
      2. try FMOD block (FileBlock type 0x00000001 with matching size)
      3. try PNG → collect for texture use
      4. try stage_container → recurse into segments
      5. try PAC archive → recurse into entries
    """
    if depth > _MAX_DEPTH or len(data) < 12:
        return _Assets()

    blob = fully_unwrap(data)

    # FMOD model: FileBlock with matching total size
    if _is_fmod_block(blob):
        return _Assets(fmods=[blob])

    # PNG texture — collect for later assignment
    if _is_png(blob):
        return _Assets(pngs=[blob])

    result = _Assets()

    # Stage container (must check before PAC — no magic bytes, heuristic only)
    if is_stage_container(blob):
        segments = parse_stage_container(blob)
        _logger.debug(f"[depth={depth}] stage_container: {len(segments)} segments")
        for seg in segments:
            if seg.size == 0:
                continue
            sub = _collect_assets(seg.data, depth + 1)
            result.fmods.extend(sub.fmods)
            result.pngs.extend(sub.pngs)
        return result

    # PAC archive
    if is_pac_archive(blob):
        pac = parse_pac(blob)
        if pac is None:
            return result
        _logger.debug(f"[depth={depth}] PAC: {len(pac.entries)} entries")
        for i in range(len(pac.entries)):
            entry_data = pac.extract(i)
            if not entry_data:
                continue
            sub = _collect_assets(entry_data, depth + 1)
            result.fmods.extend(sub.fmods)
            result.pngs.extend(sub.pngs)
        return result

    return result


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
    FMOD models and PNG textures, mirroring MHBridge's collect_model_bundles /
    collect_assets.

    PNG blobs are written to a persistent temp directory so that Blender can
    reference them by path.  The directory survives the import so that the
    saved .blend file can still reload the images.

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

    assets = _collect_assets(raw, depth=0)
    _logger.info(
        f"Found {len(assets.fmods)} FMOD blobs and {len(assets.pngs)} PNG blobs"
        f" in {stage_path.name}"
    )

    if not assets.fmods:
        _logger.warning(f"No FMOD models found in {stage_path}")
        return []

    # Write PNG textures to a persistent temp directory so Blender can load them.
    # Named 0000.png, 0001.png, … so that sorted order matches imageID indices.
    texture_search_path: Optional[str] = None
    if import_textures and assets.pngs:
        tex_dir = Path(tempfile.mkdtemp(prefix=f"mhf_{stage_path.stem}_"))
        png_subdir = tex_dir / "textures"
        png_subdir.mkdir()
        for idx, png_blob in enumerate(assets.pngs):
            (png_subdir / f"{idx:04d}.png").write_bytes(png_blob)
        # Pass a fake file path inside png_subdir so find_all_textures() searches it
        texture_search_path = str(png_subdir / "dummy.fmod")
        _logger.info(f"Wrote {len(assets.pngs)} textures to {png_subdir}")

    collection = None
    if create_collection:
        collection = builders.scene.create_collection(stage_path.stem)
        builders.scene.link_collection_to_scene(collection)

    imported_objects: List[Any] = []
    for i, blob in enumerate(assets.fmods):
        try:
            objects = import_fmod_from_bytes_func(
                blob,
                f"Stage_{i:04d}",
                import_textures,
                collection,
                texture_search_path,
            )
            imported_objects.extend(objects)
        except Exception as e:
            _logger.error(f"FMOD blob {i}: import failed: {e}")

    return imported_objects
