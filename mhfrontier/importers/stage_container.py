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
class _FmodGroup:
    """One or more FMODs paired with the PNG textures they reference."""
    fmods: List[bytes] = field(default_factory=list)
    pngs: List[bytes] = field(default_factory=list)


def _collect_groups(data: bytes, depth: int) -> List["_FmodGroup"]:
    """
    Recursively collect (FMOD, PNG[]) groups, pairing each FMOD with the PNG
    textures that are siblings at the same PAC level.

    The stage PAC structure has a clear pattern:
      inner PAC: [preamble, FMOD (pac1), preamble, PNG-bank (pac3), ...]

    FMODs use local imageIDs (0 = first PNG in *their own* sibling bank).
    Merging all PNGs globally would map wrong textures to wrong FMODs.

    Rules:
      - FMOD blob → bare FmodGroup(fmods=[blob])
      - PNG blob  → bare FmodGroup(pngs=[blob])
      - stage_container → recurse each segment, pass groups through unchanged
      - PAC archive → recurse each entry, then AT THIS LEVEL:
          * already-paired groups (have both FMODs and PNGs) → pass through
          * bare FMOD groups + bare PNG groups → merge into one new group
          * bare PNG groups with no bare FMODs → bubble up for parent to merge
    """
    if depth > _MAX_DEPTH or len(data) < 12:
        return []

    blob = fully_unwrap(data)

    if _is_fmod_block(blob):
        return [_FmodGroup(fmods=[blob])]

    if _is_png(blob):
        return [_FmodGroup(pngs=[blob])]

    # Stage container: pass sub-groups through unchanged (pairing happens at PAC level)
    if is_stage_container(blob):
        segments = parse_stage_container(blob)
        _logger.debug(f"[depth={depth}] stage_container: {len(segments)} segments")
        groups: List[_FmodGroup] = []
        for seg in segments:
            if seg.size == 0:
                continue
            groups.extend(_collect_groups(seg.data, depth + 1))
        return groups

    # PAC archive: recurse then merge bare FMODs with bare PNGs at this level
    if is_pac_archive(blob):
        pac = parse_pac(blob)
        if pac is None:
            return []
        _logger.debug(f"[depth={depth}] PAC: {len(pac.entries)} entries")
        sub_groups: List[_FmodGroup] = []
        for i in range(len(pac.entries)):
            entry_data = pac.extract(i)
            if not entry_data:
                continue
            sub_groups.extend(_collect_groups(entry_data, depth + 1))

        # Separate already-paired groups from bare ones
        paired = [g for g in sub_groups if g.fmods and g.pngs]
        bare_fmods = [g for g in sub_groups if g.fmods and not g.pngs]
        bare_pngs = [g for g in sub_groups if not g.fmods and g.pngs]

        result = list(paired)

        if bare_fmods:
            # Merge all bare FMODs at this level with all bare PNGs at this level
            merged = _FmodGroup()
            for g in bare_fmods:
                merged.fmods.extend(g.fmods)
            for g in bare_pngs:
                merged.pngs.extend(g.pngs)
            result.append(merged)
        elif bare_pngs:
            # No FMODs here — bubble up the PNG groups for the parent to merge
            merged_pngs = _FmodGroup()
            for g in bare_pngs:
                merged_pngs.pngs.extend(g.pngs)
            result.append(merged_pngs)

        return result

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

    groups = _collect_groups(raw, depth=0)
    total_fmods = sum(len(g.fmods) for g in groups)
    total_pngs = sum(len(g.pngs) for g in groups)
    _logger.info(
        f"Found {total_fmods} FMOD blobs in {len(groups)} groups"
        f" ({total_pngs} PNG blobs total) in {stage_path.name}"
    )

    if total_fmods == 0:
        _logger.warning(f"No FMOD models found in {stage_path}")
        return []

    collection = None
    if create_collection:
        collection = builders.scene.create_collection(stage_path.stem)
        builders.scene.link_collection_to_scene(collection)

    imported_objects: List[Any] = []
    fmod_index = 0

    for group_idx, group in enumerate(groups):
        if not group.fmods:
            continue

        # Each group has its own local PNG pool — write to a separate temp dir.
        # Named 0000.png, 0001.png, … so sorted order matches imageID indices.
        texture_search_path: Optional[str] = None
        if import_textures and group.pngs:
            tex_dir = Path(tempfile.mkdtemp(prefix=f"mhf_{stage_path.stem}_g{group_idx}_"))
            png_subdir = tex_dir / "textures"
            png_subdir.mkdir()
            for idx, png_blob in enumerate(group.pngs):
                (png_subdir / f"{idx:04d}.png").write_bytes(png_blob)
            texture_search_path = str(png_subdir / "dummy.fmod")
            _logger.debug(
                f"Group {group_idx}: wrote {len(group.pngs)} textures to {png_subdir}"
            )

        for blob in group.fmods:
            try:
                objects = import_fmod_from_bytes_func(
                    blob,
                    f"Stage_{fmod_index:04d}",
                    import_textures,
                    collection,
                    texture_search_path,
                )
                imported_objects.extend(objects)
            except Exception as e:
                _logger.error(f"FMOD blob {fmod_index}: import failed: {e}")
            fmod_index += 1

    return imported_objects
