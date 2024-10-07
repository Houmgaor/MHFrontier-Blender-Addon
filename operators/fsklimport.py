# -*- coding: utf-8 -*-
"""
Created on Mon Dec 30 01:10:11 2019

@author: AsteriskAmpersand
"""
import bpy
from bpy_extras.io_utils import ImportHelper

from ..fmod import FSklImporterLayer


class ImportFSKL(bpy.types.Operator, ImportHelper):
    bl_idname = "custom_import.import_mhf_fskl"
    bl_label = "Load MHF FSKL file (.fskl)"
    bl_options = {'REGISTER', 'PRESET', 'UNDO'}
 
    # ImportHelper mixin class uses this
    filename_ext = ".fskl"
    filter_glob = bpy.props.StringProperty(default="*.fskl", options={'HIDDEN'}, maxlen=255)

    def execute(self, _context):
        """Create a new Frontier Skeleton (FSKL) tree to the hierarchy."""
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except RuntimeError as error:
            print(error)
        bpy.ops.object.select_all(action='DESELECT')
        importer = FSklImporterLayer.FSklImporter()
        importer.execute(self.properties.filepath)
        return {'FINISHED'}
    
    
def menu_func_import(self, _context):
    self.layout.operator(ImportFSKL.bl_idname, text="MHF FSKL (.fskl)")
