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

import bpy

from . import fmod
from .mesh_importer import (
    import_mesh,
    create_mesh,
    create_blender_object,
    create_texture_layer,
    set_normals,
    set_weights,
)
from .material_importer import (
    import_textures,
    find_all_textures,
    search_textures,
    get_texture,
    fetch_texture,
    assign_texture,
)


def import_model(fmod_path, import_textures_prop):
    """
    Import an FMOD model into Blender.

    :param str fmod_path: Path to the FMOD file.
    :param bool import_textures_prop: True to import textures.
    """
    bpy.context.scene.render.engine = "CYCLES"
    meshes, materials = fmod.load_fmod_file(fmod_path)

    # Create new materials
    blender_materials = {}
    for mesh in meshes:
        for mat_id in mesh.material_list:
            if mat_id not in blender_materials:
                blender_materials[mat_id] = bpy.data.materials.new(
                    name="FrontierMaterial-%03d" % mat_id
                )

    # Create meshes
    for ix, mesh in enumerate(meshes):
        import_mesh(ix, mesh, blender_materials)

    # Import textures
    if import_textures_prop:
        import_textures(materials, fmod_path, blender_materials)


def clear_scene():
    """Delete all objects in the scene."""
    for key in list(bpy.context.scene.keys()):
        del bpy.context.scene[key]
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for i in bpy.data.images.keys():
        bpy.data.images.remove(bpy.data.images[i])
