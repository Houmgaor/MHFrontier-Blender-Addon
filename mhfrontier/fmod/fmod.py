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

    A single FMOD file usually contains multiple meshes.

    :param data: Raw FMOD file data.
    :param verbose: Print structure info if True.
    :return: Tuple of (list of meshes, list of materials)
    """
    frontier_file = fblock.FBlock()
    frontier_file.marshall(filelike.FileLike(data))
    if verbose:
        _logger.debug("FMOD file structure")
        frontier_file.pretty_print(_logger)
    for i, datum in enumerate(frontier_file.data[1:4]):
        if not isinstance(datum, fblock.FileBlock):
            raise TypeError(
                f"Child {i} should be {fblock.FileBlock.__name__}, "
                f"found type is {type(datum)}"
            )
    meshes = frontier_file.data[1].data
    for i, mesh in enumerate(meshes):
        if not isinstance(mesh, fblock.MainBlock):
            raise TypeError(
                f"Block type should be {fblock.MainBlock.__name__}, "
                f"found type is {type(mesh)}"
            )
    materials = frontier_file.data[2].data
    for i, material in enumerate(materials):
        if not isinstance(material, fblock.MaterialBlock):
            raise TypeError(
                f"Block {i} should be {fblock.MaterialBlock.__name__}, "
                f"found type is {type(frontier_file.data[2].data)}"
            )
    textures = frontier_file.data[3].data
    for i, texture in enumerate(textures):
        if not isinstance(texture, fblock.TextureBlock):
            raise TypeError(
                f"Block {i} should be {fblock.TextureBlock.__name__}, "
                f"found type is {type(texture)}"
            )
    mesh_parts = [fmesh.FMesh(mesh) for mesh in meshes]
    out_materials = [fmat.FMat(material, textures) for material in materials]
    return mesh_parts, out_materials
