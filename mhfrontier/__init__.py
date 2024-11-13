# -*- coding: utf-8 -*-
"""
Main entry point for the Blender add-on definition.

Created on Wed Mar  6 13:38:47 2019

@author: AsteriskAmpersand
"""
import bpy

from .operators import (
    fmod_import,
    fskl_import,
    fskl_convert,
)


content = bytes("", "UTF-8")
bl_info = {
    "name": "MHFrontier Model Importer",
    "description": "Import Monster Hunter Frontier model files to Blender.",
    "author": "AsteriskAmpersand (Code), Vuze (Structure), Houmgaor (Update)",
    "version": (2, 1, 1),
    "blender": (2, 80, 0),
    "location": "File > Import-Export > FMod/MHF and Object > Create Armature from FSKL Tree",
    "doc_url": "https://github.com/Houmgaor/MHFrontier-Blender-Addon",
    "tracker_url": "https://github.com/Houmgaor/MHFrontier-Blender-Addon/issues",
    "category": "Import-Export",
}


def register():
    """
    Register the add-on to Blender.

    It adds two new options for File Import: Import FMOD and Import FSKL.
    You will also get a new feature "Convert FSKL to Armature".
    """
    # Register the FMOD (Frontier Model) file import
    bpy.utils.register_class(fmod_import.ImportFMOD)
    # New structure since Blender 2.8x
    if bpy.app.version >= (2, 8):
        bpy.types.TOPBAR_MT_file_import.append(fmod_import.menu_func_import)
    else:
        bpy.types.INFO_MT_file_import.append(fmod_import.menu_func_import)

    # Register the FSKL (Frontier Skeleton) file import
    bpy.utils.register_class(fskl_import.ImportFSKL)
    if bpy.app.version >= (2, 8):
        bpy.types.TOPBAR_MT_file_import.append(fskl_import.menu_func_import)
    else:
        bpy.types.INFO_MT_file_import.append(fskl_import.menu_func_import)

    # Register the creation of the Blender Armature
    bpy.utils.register_class(fskl_convert.ConvertFSKL)
    bpy.types.VIEW3D_MT_object.append(fskl_convert.menu_func)


def unregister():
    """Remove the FMOD/FSKL add-on."""
    bpy.utils.unregister_class(fmod_import.ImportFMOD)
    # New structure since Blender 2.8x
    if bpy.app.version >= (2, 8):
        bpy.types.TOPBAR_MT_file_import.remove(fmod_import.menu_func_import)
    else:
        bpy.types.INFO_MT_file_import.remove(fmod_import.menu_func_import)

    # Frontier Skeleton import
    bpy.utils.unregister_class(fskl_import.ImportFSKL)
    if bpy.app.version >= (2, 8):
        bpy.types.TOPBAR_MT_file_import.remove(fskl_import.menu_func_import)
    else:
        bpy.types.INFO_MT_file_import.remove(fskl_import.menu_func_import)

    # Unregister Armature creation
    bpy.utils.unregister_class(fskl_convert.ConvertFSKL)
    bpy.types.VIEW3D_MT_object.remove(fskl_convert.menu_func)


if __name__ == "__main__":
    try:
        unregister()
    except Exception as err:
        print("Cannot unregister: ", err)
    finally:
        register()
