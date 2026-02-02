# -*- coding: utf-8 -*-
"""
FMOD import orchestration layer.

Coordinates the import of MHF model files (.fmod) into Blender:
1. Load model data (meshes, materials)
2. Create Blender materials
3. Import mesh geometry
4. Optionally import textures

Created on Sat Apr  6 02:55:27 2019

@author: AsteriskAmpersand
"""

from typing import Any, Dict, Optional

from . import fmod
from .mesh_importer import import_mesh
from .material_importer import import_textures
from ..blender.api import SceneManager, MaterialBuilder


def _get_default_builders():
    """Get default Blender builders (lazy import to avoid Blender dependency at import time)."""
    from ..blender.blender_impl import get_scene_manager, get_material_builder

    return get_scene_manager(), get_material_builder()


def import_model(
    fmod_path: str,
    import_textures_prop: bool,
    scene_manager: Optional[SceneManager] = None,
    material_builder: Optional[MaterialBuilder] = None,
) -> None:
    """
    Import an FMOD model into Blender.

    :param fmod_path: Path to the FMOD file.
    :param import_textures_prop: True to import textures.
    :param scene_manager: Optional scene manager (defaults to Blender implementation).
    :param material_builder: Optional material builder (defaults to Blender implementation).
    """
    if scene_manager is None or material_builder is None:
        default_scene, default_mat = _get_default_builders()
        scene_manager = scene_manager or default_scene
        material_builder = material_builder or default_mat

    scene_manager.set_render_engine("CYCLES")
    meshes, materials = fmod.load_fmod_file(fmod_path)

    # Create new materials
    blender_materials: Dict[int, Any] = {}
    for mesh in meshes:
        for mat_id in mesh.material_list:
            if mat_id not in blender_materials:
                blender_materials[mat_id] = material_builder.create_material(
                    name="FrontierMaterial-%03d" % mat_id
                )

    # Create meshes
    for ix, mesh in enumerate(meshes):
        import_mesh(ix, mesh, blender_materials)

    # Import textures
    if import_textures_prop:
        import_textures(materials, fmod_path, blender_materials)


def clear_scene(scene_manager: Optional[SceneManager] = None) -> None:
    """
    Delete all objects in the scene.

    :param scene_manager: Optional scene manager (defaults to Blender implementation).
    """
    if scene_manager is None:
        scene_manager, _ = _get_default_builders()

    scene_manager.clear_scene()
