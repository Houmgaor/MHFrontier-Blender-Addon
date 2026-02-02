# -*- coding: utf-8 -*-
"""
Main entry point for the Blender add-on definition.

Created on Wed Mar  6 13:38:47 2019

@author: AsteriskAmpersand
"""
from .logging_config import get_logger

_logger = get_logger()

# bpy is only available when running inside Blender.
# Guard it to allow importing parsing modules for testing.
try:
    import bpy

    _BLENDER_AVAILABLE = True
except ImportError:
    _BLENDER_AVAILABLE = False

if _BLENDER_AVAILABLE:
    from .operators import (
        fmod_import,
        fskl_import,
        fmot_import,
        fskl_convert,
        stage_import,
        fmod_export_op,
        fskl_export_op,
    )


content = bytes("", "UTF-8")
bl_info = {
    "name": "MHFrontier Model Importer",
    "description": "Import Monster Hunter Frontier model and stage files to Blender.",
    "author": "AsteriskAmpersand (Code), Vuze (Structure), Houmgaor (Update)",
    "version": (2, 3, 0),
    "blender": (2, 80, 0),
    "location": "File > Import-Export > MHF FMOD/FSKL and Object > Create Armature from FSKL Tree",
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

    # Register the FMOT (Frontier Motion) file import
    bpy.utils.register_class(fmot_import.ImportFMOT)
    if bpy.app.version >= (2, 8):
        bpy.types.TOPBAR_MT_file_import.append(fmot_import.menu_func_import)
    else:
        bpy.types.INFO_MT_file_import.append(fmot_import.menu_func_import)

    # Register stage/map import
    bpy.utils.register_class(stage_import.ImportStage)
    bpy.utils.register_class(stage_import.ImportStageDirect)
    if bpy.app.version >= (2, 8):
        bpy.types.TOPBAR_MT_file_import.append(stage_import.menu_func_import)
        bpy.types.TOPBAR_MT_file_import.append(stage_import.menu_func_import_direct)
    else:
        bpy.types.INFO_MT_file_import.append(stage_import.menu_func_import)
        bpy.types.INFO_MT_file_import.append(stage_import.menu_func_import_direct)

    # Register the creation of the Blender Armature
    bpy.utils.register_class(fskl_convert.ConvertFSKL)
    bpy.types.VIEW3D_MT_object.append(fskl_convert.menu_func)

    # Register FMOD export
    bpy.utils.register_class(fmod_export_op.ExportFMOD)
    if bpy.app.version >= (2, 8):
        bpy.types.TOPBAR_MT_file_export.append(fmod_export_op.menu_func_export)
    else:
        bpy.types.INFO_MT_file_export.append(fmod_export_op.menu_func_export)

    # Register FSKL export
    bpy.utils.register_class(fskl_export_op.ExportFSKL)
    if bpy.app.version >= (2, 8):
        bpy.types.TOPBAR_MT_file_export.append(fskl_export_op.menu_func_export)
    else:
        bpy.types.INFO_MT_file_export.append(fskl_export_op.menu_func_export)


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

    # Frontier Motion import
    bpy.utils.unregister_class(fmot_import.ImportFMOT)
    if bpy.app.version >= (2, 8):
        bpy.types.TOPBAR_MT_file_import.remove(fmot_import.menu_func_import)
    else:
        bpy.types.INFO_MT_file_import.remove(fmot_import.menu_func_import)

    # Stage/map import
    bpy.utils.unregister_class(stage_import.ImportStage)
    bpy.utils.unregister_class(stage_import.ImportStageDirect)
    if bpy.app.version >= (2, 8):
        bpy.types.TOPBAR_MT_file_import.remove(stage_import.menu_func_import)
        bpy.types.TOPBAR_MT_file_import.remove(stage_import.menu_func_import_direct)
    else:
        bpy.types.INFO_MT_file_import.remove(stage_import.menu_func_import)
        bpy.types.INFO_MT_file_import.remove(stage_import.menu_func_import_direct)

    # Unregister Armature creation
    bpy.utils.unregister_class(fskl_convert.ConvertFSKL)
    bpy.types.VIEW3D_MT_object.remove(fskl_convert.menu_func)

    # Unregister FMOD export
    bpy.utils.unregister_class(fmod_export_op.ExportFMOD)
    if bpy.app.version >= (2, 8):
        bpy.types.TOPBAR_MT_file_export.remove(fmod_export_op.menu_func_export)
    else:
        bpy.types.INFO_MT_file_export.remove(fmod_export_op.menu_func_export)

    # Unregister FSKL export
    bpy.utils.unregister_class(fskl_export_op.ExportFSKL)
    if bpy.app.version >= (2, 8):
        bpy.types.TOPBAR_MT_file_export.remove(fskl_export_op.menu_func_export)
    else:
        bpy.types.INFO_MT_file_export.remove(fskl_export_op.menu_func_export)


if __name__ == "__main__":
    try:
        unregister()
    except Exception as err:
        _logger.warning(f"Cannot unregister: {err}")
    finally:
        register()
