# -*- coding: utf-8 -*-
"""
Material and texture import utilities for Blender.

Handles texture discovery, loading, and material setup with shader nodes.
"""

import os
from pathlib import Path

import bpy

from ..blender import blender_nodes_functions as bnf


def import_textures(materials, path, blender_materials):
    """
    Import textures from the file system and assign to materials.

    Performs a greedy search for texture files in the directory hierarchy
    around the model file.

    :param materials: Materials data with texture IDs.
    :type materials: list[mhfrontier.fmod.fmat.FMat]
    :param str path: Path to the FMOD file.
    :param blender_materials: Dictionary of Blender materials.
    :type blender_materials: dict[int, bpy.types.Material]
    """
    for ix, mat in blender_materials.items():
        # Setup material for nodes
        mat.use_nodes = True
        node_tree = mat.node_tree
        nodes = node_tree.nodes
        for node in nodes:
            nodes.remove(node)

        # Get texture indices from material data
        diffuse_ix = materials[ix].diffuse_id
        normal_ix = materials[ix].normal_id
        specular_ix = materials[ix].specular_id

        # Find all available texture files
        texture_files = find_all_textures(path)

        # Build shader node tree
        setup = bnf.principled_setup(node_tree)
        next(setup)

        # Diffuse texture
        if diffuse_ix is None:
            setup.send(None)
        else:
            diffuse_node = bnf.diffuse_setup(
                node_tree, fetch_texture(texture_files[diffuse_ix])
            )
            setup.send(diffuse_node)

        # Normal map
        if normal_ix is None:
            setup.send(None)
        else:
            normal_node = bnf.normal_setup(
                node_tree, fetch_texture(texture_files[normal_ix])
            )
            setup.send(normal_node)

        # Specular map
        if specular_ix is None:
            setup.send(None)
        else:
            specular_node = bnf.specular_setup(
                node_tree, fetch_texture(texture_files[specular_ix])
            )
            setup.send(specular_node)

        bnf.finish_setup(node_tree, next(setup))


def find_all_textures(path):
    """
    Find all texture files in the directory hierarchy around a model file.

    Search order:
    1. Parent directory of the model
    2. Child directories (sorted alphabetically)
    3. Sibling directories (sorted alphabetically)

    :param str path: Path to the model file.
    :return: List of texture file paths.
    :rtype: list[str]
    """
    model_path = Path(path)
    in_children = [
        f
        for f in model_path.parents[1].glob("**/*")
        if f.is_dir() and f > model_path.parent
    ]
    in_parents = [
        f
        for f in model_path.parents[1].glob("**/*")
        if f.is_dir() and f < model_path.parent
    ]
    directories = [
        model_path.parent,
        *sorted(in_children),
        *sorted(in_parents),
    ]
    output = []
    for directory in directories:
        current = sorted(list(directory.rglob("*.png")))
        output.extend(file.resolve().as_posix() for file in current)
    return output


def search_textures(path, ix):
    """
    Find a specific texture by index from the available textures.

    :param str path: Initial file path (used for texture discovery).
    :param int ix: Texture index to retrieve.
    :return: Path to the texture file.
    :rtype: str
    :raises IndexError: If the index exceeds available textures.
    """
    textures = find_all_textures(path)
    if ix >= len(textures):
        raise IndexError(
            f"Requested texture {ix}, but only {len(textures)} were detected!"
        )
    return textures[ix]


def get_texture(path, local_index):
    """
    Load a specific texture by index.

    :param str path: Path to look for the texture.
    :param int local_index: Texture index.
    :return: Loaded Blender image.
    :rtype: bpy.types.Image
    """
    filepath = search_textures(path, local_index)
    return fetch_texture(filepath)


def fetch_texture(filepath):
    """
    Load a texture from the file system.

    :param str filepath: Path to the texture file.
    :return: Loaded Blender image.
    :rtype: bpy.types.Image
    :raises FileNotFoundError: If the file does not exist.
    """
    if os.path.exists(filepath):
        return bpy.data.images.load(filepath)
    raise FileNotFoundError("File %s not found" % filepath)


def assign_texture(mesh_object, texture_data):
    """
    Assign a texture to all UV layers of a mesh (Blender 2.7x style).

    Note: This function is for legacy Blender versions that use uv_textures.

    :param bpy.types.Object mesh_object: Object to assign texture to.
    :param bpy.types.Image texture_data: Texture image to assign.
    """
    for uv_layer in mesh_object.data.uv_textures:
        for uv_tex_face in uv_layer.data:
            uv_tex_face.image = texture_data
    mesh_object.data.update()
