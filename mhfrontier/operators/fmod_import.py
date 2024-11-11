"""
Importer operator for FMOD file.

Created on Wed Mar  6 14:09:29 2019

@author: AsteriskAmpersand
"""

import bpy
import bpy_extras

from ..fmod import fmod_importer_layer


class ImportFMOD(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
    """Addon an operator to import a FMOD (Frontier Model) file."""

    bl_idname = "custom_import.import_mhf_fmod"
    bl_label = "Load MHF FMOD file (.fmod)"
    bl_options = {"REGISTER", "PRESET", "UNDO"}

    # ImportHelper mixin class uses this
    filename_ext = ".fmod"
    filter_glob = bpy.props.StringProperty(
        default="*.fmod", options={"HIDDEN"}, maxlen=255
    )

    clear_scene = bpy.props.BoolProperty(
        name="Clear scene before import.",
        description="Clears all contents before importing",
        default=True,
    )
    import_textures = bpy.props.BoolProperty(
        name="Import Textures.",
        description="Imports textures with a greedy search algorithm.",
        default=True,
    )

    def execute(self, _context):
        """Import the model to the scene."""
        try:
            bpy.ops.object.mode_set(mode="OBJECT")
        except RuntimeError as error:
            print(error)
        bpy.ops.object.select_all(action="DESELECT")

        if self.clear_scene:
            fmod_importer_layer.clear_scene()
        fmod_importer_layer.import_model(self.properties.filepath, self.import_textures)
        return {"FINISHED"}


def menu_func_import(self, _context):
    """Add the operator."""
    self.layout.operator(ImportFMOD.bl_idname, text="MHF FMOD (.fmod)")
