# -*- coding: utf-8 -*-
"""
Created on Wed Mar  6 14:09:29 2019

@author: AsteriskAmpersand
"""
import bpy
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty
from bpy.types import Operator

from ..fmod import FModImporterLayer


class ImportFMOD(Operator, ImportHelper):
    bl_idname = "custom_import.import_mhf_fmod"
    bl_label = "Load MHF FMOD file (.fmod)"
    bl_options = {"REGISTER", "PRESET", "UNDO"}

    # ImportHelper mixin class uses this
    filename_ext = ".fmod"
    filter_glob = StringProperty(default="*.fmod", options={"HIDDEN"}, maxlen=255)

    clear_scene = BoolProperty(
        name="Clear scene before import.",
        description="Clears all contents before importing",
        default=True,
    )
    import_textures = BoolProperty(
        name="Import Textures.",
        description="Imports textures with a greedy search algorithm.",
        default=True,
    )

    def execute(self, _context):
        try:
            bpy.ops.object.mode_set(mode="OBJECT")
        except RuntimeError as error:
            print(error)
        bpy.ops.object.select_all(action="DESELECT")

        importer = FModImporterLayer.FModImporter()
        if self.clear_scene:
            importer.clear_scene()
        importer.maximize_clipping()
        importer.execute(self.properties.filepath, self.import_textures)
        importer.maximize_clipping()
        return {"FINISHED"}


def menu_func_import(self, _context):
    self.layout.operator(ImportFMOD.bl_idname, text="MHF FMOD (.fmod)")
