# -*- coding: utf-8 -*-
"""
Material and texture import utilities for Blender.

Handles texture discovery, loading, and material setup with shader nodes.
This module uses the centralized Builders for Blender operations.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ..blender.builders import Builders, get_builders

if TYPE_CHECKING:
    from ..fmod.fmat import FMat


def import_textures(
    materials: List["FMat"],
    path: str,
    blender_materials: Dict[int, Any],
    builders: Optional[Builders] = None,
) -> None:
    """
    Import textures from the file system and assign to materials.

    Performs a greedy search for texture files in the directory hierarchy
    around the model file.

    :param materials: Materials data with texture IDs.
    :param path: Path to the FMOD file (for texture search).
    :param blender_materials: Dictionary of Blender materials by ID.
    :param builders: Optional builders (defaults to Blender implementation).
    """
    if builders is None:
        builders = get_builders()

    for ix, mat in blender_materials.items():
        # Setup material for nodes
        node_tree = builders.material.enable_nodes(mat)
        builders.material.clear_nodes(node_tree)

        # Get texture indices from material data
        diffuse_ix = materials[ix].diffuse_id
        normal_ix = materials[ix].normal_id
        specular_ix = materials[ix].specular_id

        # Find all available texture files
        texture_files = find_all_textures(path)

        # Build shader node tree using abstracted setup
        _setup_principled_shader(
            node_tree,
            texture_files,
            diffuse_ix,
            normal_ix,
            specular_ix,
            builders,
        )


def _setup_principled_shader(
    node_tree: Any,
    texture_files: List[str],
    diffuse_ix: Optional[int],
    normal_ix: Optional[int],
    specular_ix: Optional[int],
    builders: Builders,
) -> None:
    """
    Set up a Principled BSDF shader with textures.

    :param node_tree: Node tree to build shader in.
    :param texture_files: Available texture file paths.
    :param diffuse_ix: Index of diffuse texture, or None.
    :param normal_ix: Index of normal texture, or None.
    :param specular_ix: Index of specular texture, or None.
    :param builders: Builders for node operations.
    """
    # Create main BSDF node
    bsdf_node = builders.material.create_principled_bsdf(node_tree)
    builders.material.set_node_location(bsdf_node, 600, 0)
    end_node = bsdf_node

    # Diffuse texture setup
    if diffuse_ix is not None and diffuse_ix < len(texture_files):
        texture = builders.image.load_image(texture_files[diffuse_ix])
        diffuse_tex_node = builders.material.create_texture_node(
            node_tree, texture, "Diffuse Texture", is_data=False
        )
        builders.material.set_node_location(diffuse_tex_node, 0, 0)

        # Link diffuse to BSDF base color
        builders.material.link_nodes(node_tree, diffuse_tex_node, 0, bsdf_node, 0)

        # Setup alpha transparency
        transparent_node = builders.material.create_transparent_node(node_tree)
        builders.material.set_node_location(transparent_node, 600, 700)

        alpha_mixer_node = builders.material.create_mix_shader_node(node_tree)
        builders.material.set_node_location(alpha_mixer_node, 1000, 100)

        # Link alpha channel to mixer factor
        builders.material.link_nodes(node_tree, diffuse_tex_node, 1, alpha_mixer_node, 0)
        builders.material.link_nodes(node_tree, transparent_node, 0, alpha_mixer_node, 1)
        builders.material.link_nodes(node_tree, bsdf_node, 0, alpha_mixer_node, 2)

        end_node = alpha_mixer_node

    # Normal map setup
    if normal_ix is not None and normal_ix < len(texture_files):
        texture = builders.image.load_image(texture_files[normal_ix])
        normal_tex_node = builders.material.create_texture_node(
            node_tree, texture, "Normal Texture", is_data=True
        )
        builders.material.set_node_location(normal_tex_node, 0, 600)

        normal_map_node = builders.material.create_normal_map_node(node_tree)
        builders.material.set_node_location(normal_map_node, 400, 600)

        builders.material.link_nodes(node_tree, normal_tex_node, 0, normal_map_node, 1)
        builders.material.link_nodes(node_tree, normal_map_node, 0, bsdf_node, "Normal")

    # Specular map setup
    if specular_ix is not None and specular_ix < len(texture_files):
        texture = builders.image.load_image(texture_files[specular_ix])
        specular_tex_node = builders.material.create_texture_node(
            node_tree, texture, "Specular Texture", is_data=True
        )
        builders.material.set_node_location(specular_tex_node, 0, 300)

        curve_node = builders.material.create_rgb_curve_node(node_tree)
        builders.material.set_node_location(curve_node, 200, 100)

        builders.material.link_nodes(node_tree, specular_tex_node, 0, curve_node, 0)
        # Try "Specular IOR Level" first (Blender 4.0+), fall back to "Specular"
        try:
            builders.material.link_nodes(
                node_tree, curve_node, 0, bsdf_node, "Specular IOR Level"
            )
        except (KeyError, TypeError):
            builders.material.link_nodes(
                node_tree, curve_node, 0, bsdf_node, "Specular"
            )

    # Create output node
    output_node = builders.material.create_output_node(node_tree)
    builders.material.set_node_location(output_node, 1400, 0)
    builders.material.link_nodes(node_tree, end_node, 0, output_node, 0)


def find_all_textures(path: str) -> List[str]:
    """
    Find all texture files in the directory hierarchy around a model file.

    Search order:
    1. Parent directory of the model
    2. Child directories (sorted alphabetically)
    3. Sibling directories (sorted alphabetically)

    :param path: Path to the model file.
    :return: List of texture file paths as strings.
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
    output: List[str] = []
    for directory in directories:
        current = sorted(list(directory.rglob("*.png")))
        output.extend(file.resolve().as_posix() for file in current)
    return output


def search_textures(path: str, ix: int) -> str:
    """
    Find a specific texture by index from the available textures.

    :param path: Initial file path (used for texture discovery).
    :param ix: Texture index to retrieve.
    :return: Path to the texture file.
    :raises IndexError: If the index exceeds available textures.
    """
    textures = find_all_textures(path)
    if ix >= len(textures):
        raise IndexError(
            f"Requested texture {ix}, but only {len(textures)} were detected!"
        )
    return textures[ix]


def get_texture(
    path: str,
    local_index: int,
    builders: Optional[Builders] = None,
) -> Any:
    """
    Load a specific texture by index.

    :param path: Path to look for the texture.
    :param local_index: Texture index.
    :param builders: Optional builders (defaults to Blender implementation).
    :return: Loaded Blender image.
    """
    if builders is None:
        builders = get_builders()

    filepath = search_textures(path, local_index)
    return fetch_texture(filepath, builders)


def fetch_texture(
    filepath: str,
    builders: Optional[Builders] = None,
) -> Any:
    """
    Load a texture from the file system.

    :param filepath: Path to the texture file.
    :param builders: Optional builders (defaults to Blender implementation).
    :return: Loaded Blender image.
    :raises FileNotFoundError: If the file does not exist.
    """
    if builders is None:
        builders = get_builders()

    if not os.path.exists(filepath):
        raise FileNotFoundError("File %s not found" % filepath)
    return builders.image.load_image(filepath)


def assign_texture(
    mesh_object: Any,
    texture_data: Any,
) -> None:
    """
    Assign a texture to all UV layers of a mesh (Blender 2.7x style).

    Note: This function is for legacy Blender versions that use uv_textures.
    It still uses direct Blender APIs as it's only used in legacy code paths.

    :param mesh_object: Object to assign texture to.
    :param texture_data: Texture image to assign.
    """
    # This function is kept for legacy compatibility and still uses direct APIs
    # It's only called from legacy Blender 2.7x code paths
    for uv_layer in mesh_object.data.uv_textures:
        for uv_tex_face in uv_layer.data:
            uv_tex_face.image = texture_data
    mesh_object.data.update()
