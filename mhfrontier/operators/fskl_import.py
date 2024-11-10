"""
Definition of importer operator for FSKL file.

Created on Mon Dec 30 01:10:11 2019

@author: AsteriskAmpersand
"""

import bpy
import bpy_extras

from ..fmod import fskl_importer_layer


class ImportFSKL(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
    """Add an operator to import a FSKL file."""

    bl_idname = "custom_import.import_mhf_fskl"
    bl_label = "Load MHF FSKL file (.fskl)"
    bl_options = {"REGISTER", "PRESET", "UNDO"}

    # ImportHelper mixin class uses this
    filename_ext = ".fskl"
    filter_glob = bpy.props.StringProperty(
        default="*.fskl", options={"HIDDEN"}, maxlen=255
    )

    def execute(self, _context):
        """Create a new Frontier Skeleton (FSKL) tree to the hierarchy."""
        try:
            bpy.ops.object.mode_set(mode="OBJECT")
        except RuntimeError as error:
            print(error)
        bpy.ops.object.select_all(action="DESELECT")
        importer = fskl_importer_layer.FSklImporter()
        importer.execute(self.properties.filepath)
        return {"FINISHED"}


def menu_func_import(self, _context):
    """Add the operator."""
    self.layout.operator(ImportFSKL.bl_idname, text="MHF FSKL (.fskl)")
