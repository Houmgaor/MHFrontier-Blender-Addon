"""
Definition of importer operator for FSKL file.

Created on Mon Dec 30 01:10:11 2019

@author: AsteriskAmpersand
"""

import bpy
import bpy_extras

from ..importers import import_skeleton
from ..logging_config import get_logger

_logger = get_logger("operators")


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
            _logger.debug(f"Mode switch warning: {error}")
        bpy.ops.object.select_all(action="DESELECT")
        import_skeleton(self.properties.filepath)
        return {"FINISHED"}


def menu_func_import(self, _context):
    """Add the operator."""
    self.layout.operator(ImportFSKL.bl_idname, text="MHF FSKL (.fskl)")
