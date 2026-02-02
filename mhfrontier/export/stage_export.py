# -*- coding: utf-8 -*-
"""
Stage container export for Monster Hunter Frontier.

High-level export orchestration that extracts data from Blender collections
and builds stage container (.pac) files.
"""

from dataclasses import dataclass, field
from typing import Any, List, Optional

from .blender_extractor import ExtractedMaterial, ExtractedMesh, MeshExtractor, MaterialExtractor
from .fmod_export import build_fmod_file
from ..logging_config import get_logger
from ..stage.jkr_compress import compress_jkr_hfi, CompressionType, compress_jkr
from ..stage.stage_export import (
    StageSegmentBuilder,
    build_stage_container,
    build_segment_from_fmod,
    build_segment_from_texture,
    build_segment_from_audio,
)
from ..stage.stage_container import SegmentType

_logger = get_logger("export.stage")


@dataclass
class StageExportOptions:
    """Options for stage export."""

    compress_segments: bool = True
    compression_type: int = CompressionType.HFI
    include_textures: bool = True
    include_audio: bool = True
    apply_modifiers: bool = True


@dataclass
class ExtractedStageData:
    """Extracted data from a Blender collection ready for export."""

    meshes: List[ExtractedMesh] = field(default_factory=list)
    materials: List[ExtractedMaterial] = field(default_factory=list)
    textures: List[bytes] = field(default_factory=list)
    texture_is_dds: List[bool] = field(default_factory=list)
    audio: List[bytes] = field(default_factory=list)


class StageExtractor:
    """
    Extract stage data from a Blender collection.

    Collects mesh objects, materials, textures, and audio for export.
    """

    def __init__(self, options: Optional[StageExportOptions] = None) -> None:
        """
        Create a stage extractor.

        :param options: Export options.
        """
        self.options = options or StageExportOptions()
        self._mesh_extractor = MeshExtractor(apply_modifiers=self.options.apply_modifiers)
        self._material_extractor = MaterialExtractor()

    def extract_from_collection(
        self,
        collection: Any,
        depsgraph: Optional[Any] = None,
    ) -> ExtractedStageData:
        """
        Extract all stage data from a Blender collection.

        :param collection: Blender Collection object.
        :param depsgraph: Blender dependency graph (optional).
        :return: Extracted stage data.
        """
        result = ExtractedStageData()

        if collection is None:
            return result

        # Extract meshes from all objects in collection
        materials_dict = {}

        for obj in collection.all_objects:
            if obj.type != "MESH":
                continue

            try:
                mesh = self._mesh_extractor.extract(obj, depsgraph)
                result.meshes.append(mesh)

                # Collect materials
                if obj.data.materials:
                    for mat in obj.data.materials:
                        if mat and mat.name not in materials_dict:
                            materials_dict[mat.name] = self._material_extractor.extract(mat)
            except Exception as e:
                _logger.warning(f"Failed to extract mesh {obj.name}: {e}")
                continue

        result.materials = list(materials_dict.values())

        return result

    def extract_meshes(
        self,
        objects: List[Any],
        depsgraph: Optional[Any] = None,
    ) -> List[ExtractedMesh]:
        """
        Extract meshes from a list of Blender objects.

        :param objects: List of Blender objects to extract.
        :param depsgraph: Blender dependency graph.
        :return: List of extracted meshes.
        """
        meshes = []
        for obj in objects:
            if obj.type != "MESH":
                continue
            try:
                mesh = self._mesh_extractor.extract(obj, depsgraph)
                meshes.append(mesh)
            except Exception as e:
                _logger.warning(f"Failed to extract mesh {obj.name}: {e}")
        return meshes


def build_fmod_segment(
    meshes: List[ExtractedMesh],
    materials: List[ExtractedMaterial],
    compress: bool = True,
    compression_type: int = CompressionType.HFI,
) -> StageSegmentBuilder:
    """
    Build an FMOD segment from mesh and material data.

    :param meshes: List of meshes to include.
    :param materials: List of materials.
    :param compress: Whether to JKR-compress the FMOD data.
    :param compression_type: JKR compression type to use.
    :return: Stage segment builder containing FMOD (optionally compressed).
    """
    # Build FMOD binary data
    fmod_data = build_fmod_file(meshes, materials)

    if compress:
        compressed = compress_jkr(fmod_data, compression_type)
        return StageSegmentBuilder(
            data=compressed,
            segment_type=SegmentType.JKR,
        )
    else:
        return StageSegmentBuilder(
            data=fmod_data,
            segment_type=SegmentType.FMOD,
        )


def export_stage(
    filepath: str,
    collection: Any,
    depsgraph: Optional[Any] = None,
    options: Optional[StageExportOptions] = None,
) -> None:
    """
    Export a Blender collection as a stage container (.pac file).

    :param filepath: Output file path.
    :param collection: Blender collection to export.
    :param depsgraph: Blender dependency graph.
    :param options: Export options.
    """
    options = options or StageExportOptions()

    _logger.info(f"Exporting stage to {filepath}")

    # Extract data from collection
    extractor = StageExtractor(options)
    stage_data = extractor.extract_from_collection(collection, depsgraph)

    if not stage_data.meshes:
        _logger.warning("No meshes found in collection")
        # Create empty container
        container_data = build_stage_container([])
        with open(filepath, "wb") as f:
            f.write(container_data)
        return

    # Build segments
    segments = []

    # Add default empty materials if none found
    materials = stage_data.materials
    if not materials:
        from .blender_extractor import ExtractedMaterial
        materials = [ExtractedMaterial(name="Default")]

    # Segment 0: Main FMOD model data
    fmod_segment = build_fmod_segment(
        stage_data.meshes,
        materials,
        compress=options.compress_segments,
        compression_type=options.compression_type,
    )
    segments.append(fmod_segment)

    # Segments 1-2: Usually empty or additional FMOD data
    # Add empty placeholders to maintain standard structure
    segments.append(StageSegmentBuilder(data=b"", segment_type=SegmentType.UNKNOWN))
    segments.append(StageSegmentBuilder(data=b"", segment_type=SegmentType.UNKNOWN))

    # Textures (segments 3+)
    if options.include_textures:
        for i, tex_data in enumerate(stage_data.textures):
            is_dds = stage_data.texture_is_dds[i] if i < len(stage_data.texture_is_dds) else False
            segments.append(build_segment_from_texture(tex_data, is_dds))

    # Audio (after textures)
    if options.include_audio:
        for audio_data in stage_data.audio:
            segments.append(build_segment_from_audio(audio_data))

    # Filter out empty segments (except first 3 which are structural)
    filtered_segments = []
    for i, seg in enumerate(segments):
        if i < 3 or len(seg.data) > 0:
            filtered_segments.append(seg)

    # Build container
    container_data = build_stage_container(filtered_segments)

    # Write to file
    with open(filepath, "wb") as f:
        f.write(container_data)

    _logger.info(
        f"Stage export complete: {len(stage_data.meshes)} meshes, "
        f"{len(filtered_segments)} segments, {len(container_data)} bytes"
    )


def export_stage_from_meshes(
    filepath: str,
    meshes: List[ExtractedMesh],
    materials: Optional[List[ExtractedMaterial]] = None,
    options: Optional[StageExportOptions] = None,
) -> None:
    """
    Export pre-extracted meshes as a stage container.

    Useful when mesh data is already available (e.g., from a modified import).

    :param filepath: Output file path.
    :param meshes: List of extracted meshes.
    :param materials: List of materials (optional).
    :param options: Export options.
    """
    options = options or StageExportOptions()

    if materials is None:
        from .blender_extractor import ExtractedMaterial
        materials = [ExtractedMaterial(name="Default")]

    _logger.info(f"Exporting stage to {filepath} with {len(meshes)} meshes")

    # Build segments
    segments = []

    # Segment 0: Main FMOD
    fmod_segment = build_fmod_segment(
        meshes,
        materials,
        compress=options.compress_segments,
        compression_type=options.compression_type,
    )
    segments.append(fmod_segment)

    # Empty placeholder segments
    segments.append(StageSegmentBuilder(data=b"", segment_type=SegmentType.UNKNOWN))
    segments.append(StageSegmentBuilder(data=b"", segment_type=SegmentType.UNKNOWN))

    # Build container
    container_data = build_stage_container(segments)

    with open(filepath, "wb") as f:
        f.write(container_data)

    _logger.info(f"Stage export complete: {len(container_data)} bytes")
