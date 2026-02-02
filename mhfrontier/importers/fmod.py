# -*- coding: utf-8 -*-
"""
FMOD import orchestration layer.

Coordinates the import of MHF model files (.fmod) into Blender:
1. Load model data (meshes, materials)
2. Create Blender materials
3. Import mesh geometry
4. Optionally import textures
"""

from typing import Any, Dict, Optional

from ..fmod import fmod as fmod_parser
from ..blender.builders import Builders, get_builders
from .mesh import import_mesh
from .material import import_textures


def import_model(
    fmod_path: str,
    import_textures_prop: bool,
    builders: Optional[Builders] = None,
) -> None:
    """
    Import an FMOD model into Blender.

    :param fmod_path: Path to the FMOD file.
    :param import_textures_prop: True to import textures.
    :param builders: Optional builders (defaults to Blender implementation).
    """
    if builders is None:
        builders = get_builders()

    builders.scene.set_render_engine("CYCLES")
    meshes, materials = fmod_parser.load_fmod_file(fmod_path)

    # Create new materials
    blender_materials: Dict[int, Any] = {}
    for mesh in meshes:
        for mat_id in mesh.material_list:
            if mat_id not in blender_materials:
                blender_materials[mat_id] = builders.material.create_material(
                    name="FrontierMaterial-%03d" % mat_id
                )

    # Create meshes
    for ix, mesh in enumerate(meshes):
        import_mesh(ix, mesh, blender_materials, builders)

    # Import textures
    if import_textures_prop:
        import_textures(materials, fmod_path, blender_materials, builders)


def clear_scene(builders: Optional[Builders] = None) -> None:
    """
    Delete all objects in the scene.

    :param builders: Optional builders (defaults to Blender implementation).
    """
    if builders is None:
        builders = get_builders()

    builders.scene.clear_scene()
