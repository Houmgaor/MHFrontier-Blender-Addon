# -*- coding: utf-8 -*-
"""
Created on Wed Mar  6 13:38:47 2019

@author: AsteriskAmpersand
"""
import bpy

from .operators import fmodimport
from .operators import fsklimport
from .operators import fsklConverter

content = bytes("", "UTF-8")
bl_info = {
    "name": "MHFrontier Model Importer",
    "category": "Import-Export",
    "author": "AsteriskAmpersand (Code) & Vuze (Structure) & Houmgaor (Update)",
    "location": "File > Import-Export > FMod/MHF and Object > Create Armature from FSKL Tree",
    "version": (2, 0, 0),
    "blender": (2, 80, 0),
}


def register():
    """
    Register the add-on to Blender.

    It adds two new options for File Import: Import FMOD and Import FSKL.
    You will also get a new feature "Convert FSKL to Armature".
    """
    # Register the FMOD (Frontier Model) file import
    bpy.utils.register_class(fmodimport.ImportFMOD)
    # New structure since Blender 2.8x
    if bpy.app.version >= (2, 8):
        bpy.types.TOPBAR_MT_file_import.append(fmodimport.menu_func_import)
    else:
        bpy.types.INFO_MT_file_import.append(fmodimport.menu_func_import)

    # Register the FSKL (Frontier Skeleton) file import
    bpy.utils.register_class(fsklimport.ImportFSKL)
    if bpy.app.version >= (2, 8):
        bpy.types.TOPBAR_MT_file_import.append(fsklimport.menu_func_import)
    else:
        bpy.types.INFO_MT_file_import.append(fsklimport.menu_func_import)

    # Register the creation of the Blender Armature
    bpy.utils.register_class(fsklConverter.ConvertFSKL)
    bpy.types.VIEW3D_MT_object.append(fsklConverter.menu_func)


def unregister():
    """Remove the FMOD/FSKL add-on."""
    bpy.utils.unregister_class(fmodimport.ImportFMOD)
    # New structure since Blender 2.8x
    if bpy.app.version >= (2, 8):
        bpy.types.TOPBAR_MT_file_import.remove(fmodimport.menu_func_import)
    else:
        bpy.types.INFO_MT_file_import.remove(fmodimport.menu_func_import)

    # Frontier Skeleton import
    bpy.utils.unregister_class(fsklimport.ImportFSKL)
    if bpy.app.version >= (2, 8):
        bpy.types.TOPBAR_MT_file_import.remove(fsklimport.menu_func_import)
    else:
        bpy.types.INFO_MT_file_import.remove(fsklimport.menu_func_import)

    # Unregister Armature creation
    bpy.utils.unregister_class(fsklConverter.ConvertFSKL)
    bpy.types.VIEW3D_MT_object.remove(fsklConverter.menu_func)


if __name__ == "__main__":
    try:
        unregister()
    except Exception as err:
        print("Cannot unregister: ", err)
    finally:
        register()
