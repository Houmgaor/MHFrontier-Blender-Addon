"""
Frontier 3D model file format utility.

Created on Fri Apr  5 23:03:36 2019

@author: AsteriskAmpersand
"""

from typing import List, Tuple

from . import fblock, fmat, fmesh
from ..common import filelike
from ..logging_config import get_logger

_logger = get_logger("fmod")


def load_fmod_file(file_path: str) -> Tuple[List["fmesh.FMesh"], List["fmat.FMat"]]:
    """
    Load a 3D models with materials from an FMOD file.

    A single FMOD file usually contains multiple meshes.

    :param file_path: FMOD file to read.
    :return: Tuple of (list of meshes, list of materials)
    """
    with open(file_path, "rb") as model_file:
        return load_fmod_file_from_bytes(model_file.read())


def load_fmod_file_from_bytes(
    data: bytes, verbose: bool = True
) -> Tuple[List["fmesh.FMesh"], List["fmat.FMat"]]:
    """
    Load a 3D model with materials from FMOD data bytes.

    A single FMOD file usually contains multiple meshes. Invalid or unexpected
    blocks are skipped with warnings rather than failing the entire import.

    :param data: Raw FMOD file data.
    :param verbose: Print structure info if True.
    :return: Tuple of (list of meshes, list of materials)
    """
    frontier_file = fblock.FBlock()
    frontier_file.marshall(filelike.FileLike(data))
    if verbose:
        _logger.debug("FMOD file structure")
        frontier_file.pretty_print(_logger)

    # Validate top-level structure
    if not frontier_file.data or len(frontier_file.data) < 4:
        _logger.warning(
            "FMOD file has insufficient data blocks: expected 4, found %d",
            len(frontier_file.data) if frontier_file.data else 0,
        )
        return [], []

    # Extract and validate file blocks (indices 1-3: meshes, materials, textures)
    file_blocks = []
    for i, datum in enumerate(frontier_file.data[1:4], start=1):
        if not isinstance(datum, fblock.FileBlock):
            _logger.warning(
                "Block %d: expected %s, found %s (skipping)",
                i,
                fblock.FileBlock.__name__,
                type(datum).__name__,
            )
            file_blocks.append(None)
        else:
            file_blocks.append(datum)

    mesh_block, material_block, texture_block = file_blocks

    # Extract meshes
    meshes = []
    if mesh_block and mesh_block.data:
        for i, mesh in enumerate(mesh_block.data):
            if not isinstance(mesh, fblock.MainBlock):
                _logger.warning(
                    "Mesh %d: expected %s, found %s (skipping)",
                    i,
                    fblock.MainBlock.__name__,
                    type(mesh).__name__,
                )
                continue
            meshes.append(mesh)

    # Extract textures first (needed for materials)
    textures = []
    if texture_block and texture_block.data:
        for i, texture in enumerate(texture_block.data):
            if not isinstance(texture, fblock.TextureBlock):
                _logger.warning(
                    "Texture %d: expected %s, found %s (skipping)",
                    i,
                    fblock.TextureBlock.__name__,
                    type(texture).__name__,
                )
                continue
            textures.append(texture)

    # Extract materials
    materials = []
    if material_block and material_block.data:
        for i, material in enumerate(material_block.data):
            if not isinstance(material, fblock.MaterialBlock):
                _logger.warning(
                    "Material %d: expected %s, found %s (skipping)",
                    i,
                    fblock.MaterialBlock.__name__,
                    type(material).__name__,
                )
                continue
            materials.append(material)

    mesh_parts = [fmesh.FMesh(mesh) for mesh in meshes]
    out_materials = [fmat.FMat(material, textures) for material in materials]
    return mesh_parts, out_materials
