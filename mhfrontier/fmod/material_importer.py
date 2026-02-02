# -*- coding: utf-8 -*-
"""
Material and texture import utilities for Blender.

Handles texture discovery, loading, and material setup with shader nodes.
This module uses an abstraction layer for Blender operations to enable testing.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ..blender.api import MaterialBuilder, ImageLoader

if TYPE_CHECKING:
    from .fmat import FMat


def _get_default_builders() -> tuple[MaterialBuilder, ImageLoader]:
    """Get default Blender builders (lazy import to avoid Blender dependency at import time)."""
    from ..blender.blender_impl import get_material_builder, get_image_loader

    return get_material_builder(), get_image_loader()


def import_textures(
    materials: List["FMat"],
    path: str,
    blender_materials: Dict[int, Any],
    material_builder: Optional[MaterialBuilder] = None,
    image_loader: Optional[ImageLoader] = None,
) -> None:
    """
    Import textures from the file system and assign to materials.

    Performs a greedy search for texture files in the directory hierarchy
    around the model file.

    :param materials: Materials data with texture IDs.
    :param path: Path to the FMOD file (for texture search).
    :param blender_materials: Dictionary of Blender materials by ID.
    :param material_builder: Optional material builder (defaults to Blender implementation).
    :param image_loader: Optional image loader (defaults to Blender implementation).
    """
    if material_builder is None or image_loader is None:
        default_mat, default_img = _get_default_builders()
        material_builder = material_builder or default_mat
        image_loader = image_loader or default_img

    for ix, mat in blender_materials.items():
        # Setup material for nodes
        node_tree = material_builder.enable_nodes(mat)
        material_builder.clear_nodes(node_tree)

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
            material_builder,
            image_loader,
        )


def _setup_principled_shader(
    node_tree: Any,
    texture_files: List[str],
    diffuse_ix: Optional[int],
    normal_ix: Optional[int],
    specular_ix: Optional[int],
    material_builder: MaterialBuilder,
    image_loader: ImageLoader,
) -> None:
    """
    Set up a Principled BSDF shader with textures.

    :param node_tree: Node tree to build shader in.
    :param texture_files: Available texture file paths.
    :param diffuse_ix: Index of diffuse texture, or None.
    :param normal_ix: Index of normal texture, or None.
    :param specular_ix: Index of specular texture, or None.
    :param material_builder: Material builder for node operations.
    :param image_loader: Image loader for textures.
    """
    # Create main BSDF node
    bsdf_node = material_builder.create_principled_bsdf(node_tree)
    material_builder.set_node_location(bsdf_node, 600, 0)
    end_node = bsdf_node

    # Diffuse texture setup
    if diffuse_ix is not None and diffuse_ix < len(texture_files):
        texture = image_loader.load_image(texture_files[diffuse_ix])
        diffuse_tex_node = material_builder.create_texture_node(
            node_tree, texture, "Diffuse Texture", is_data=False
        )
        material_builder.set_node_location(diffuse_tex_node, 0, 0)

        # Link diffuse to BSDF base color
        material_builder.link_nodes(node_tree, diffuse_tex_node, 0, bsdf_node, 0)

        # Setup alpha transparency
        transparent_node = material_builder.create_transparent_node(node_tree)
        material_builder.set_node_location(transparent_node, 600, 700)

        alpha_mixer_node = material_builder.create_mix_shader_node(node_tree)
        material_builder.set_node_location(alpha_mixer_node, 1000, 100)

        # Link alpha channel to mixer factor
        material_builder.link_nodes(node_tree, diffuse_tex_node, 1, alpha_mixer_node, 0)
        material_builder.link_nodes(node_tree, transparent_node, 0, alpha_mixer_node, 1)
        material_builder.link_nodes(node_tree, bsdf_node, 0, alpha_mixer_node, 2)

        end_node = alpha_mixer_node

    # Normal map setup
    if normal_ix is not None and normal_ix < len(texture_files):
        texture = image_loader.load_image(texture_files[normal_ix])
        normal_tex_node = material_builder.create_texture_node(
            node_tree, texture, "Normal Texture", is_data=True
        )
        material_builder.set_node_location(normal_tex_node, 0, 600)

        normal_map_node = material_builder.create_normal_map_node(node_tree)
        material_builder.set_node_location(normal_map_node, 400, 600)

        material_builder.link_nodes(node_tree, normal_tex_node, 0, normal_map_node, 1)
        material_builder.link_nodes(node_tree, normal_map_node, 0, bsdf_node, "Normal")

    # Specular map setup
    if specular_ix is not None and specular_ix < len(texture_files):
        texture = image_loader.load_image(texture_files[specular_ix])
        specular_tex_node = material_builder.create_texture_node(
            node_tree, texture, "Specular Texture", is_data=True
        )
        material_builder.set_node_location(specular_tex_node, 0, 300)

        curve_node = material_builder.create_rgb_curve_node(node_tree)
        material_builder.set_node_location(curve_node, 200, 100)

        material_builder.link_nodes(node_tree, specular_tex_node, 0, curve_node, 0)
        # Try "Specular IOR Level" first (Blender 4.0+), fall back to "Specular"
        try:
            material_builder.link_nodes(
                node_tree, curve_node, 0, bsdf_node, "Specular IOR Level"
            )
        except (KeyError, TypeError):
            material_builder.link_nodes(
                node_tree, curve_node, 0, bsdf_node, "Specular"
            )

    # Create output node
    output_node = material_builder.create_output_node(node_tree)
    material_builder.set_node_location(output_node, 1400, 0)
    material_builder.link_nodes(node_tree, end_node, 0, output_node, 0)


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
    image_loader: Optional[ImageLoader] = None,
) -> Any:
    """
    Load a specific texture by index.

    :param path: Path to look for the texture.
    :param local_index: Texture index.
    :param image_loader: Optional image loader (defaults to Blender implementation).
    :return: Loaded Blender image.
    """
    if image_loader is None:
        _, image_loader = _get_default_builders()

    filepath = search_textures(path, local_index)
    return fetch_texture(filepath, image_loader)


def fetch_texture(filepath: str, image_loader: Optional[ImageLoader] = None) -> Any:
    """
    Load a texture from the file system.

    :param filepath: Path to the texture file.
    :param image_loader: Optional image loader (defaults to Blender implementation).
    :return: Loaded Blender image.
    :raises FileNotFoundError: If the file does not exist.
    """
    if image_loader is None:
        _, image_loader = _get_default_builders()

    if not os.path.exists(filepath):
        raise FileNotFoundError("File %s not found" % filepath)
    return image_loader.load_image(filepath)


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
