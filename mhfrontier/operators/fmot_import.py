# -*- coding: utf-8 -*-
"""
Definition of importer operator for FMOT (motion) files.

Imports Monster Hunter Frontier animation files (.mot) and applies them
to the active armature as Blender Actions.
"""

import bpy
import bpy_extras

from ..fmod import fmot_importer_layer
from ..logging_config import get_logger

_logger = get_logger("operators")


class ImportFMOT(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
    """Import a Monster Hunter Frontier motion file (.mot)."""

    bl_idname = "import_scene.mhf_fmot"
    bl_label = "Import MHF Motion (.mot)"
    bl_options = {"REGISTER", "PRESET", "UNDO"}

    # ImportHelper mixin class uses this
    filename_ext = ".mot"
    filter_glob: bpy.props.StringProperty(
        default="*.mot",
        options={"HIDDEN"},
        maxlen=255,
    )

    def execute(self, context):
        """Import the motion file and apply to active armature."""
        # Get the active object
        armature = context.active_object

        # Validate armature
        if armature is None:
            self.report({"ERROR"}, "No active object. Please select an armature.")
            return {"CANCELLED"}

        if armature.type != "ARMATURE":
            self.report(
                {"ERROR"},
                f"Active object '{armature.name}' is not an armature. "
                "Please select an armature first.",
            )
            return {"CANCELLED"}

        # Switch to object mode if needed
        try:
            bpy.ops.object.mode_set(mode="OBJECT")
        except RuntimeError as error:
            _logger.debug(f"Mode switch warning: {error}")

        # Import the motion
        try:
            action = fmot_importer_layer.import_motion(
                self.properties.filepath,
                armature,
            )

            if action is None:
                self.report({"WARNING"}, "No animation data found in motion file.")
                return {"CANCELLED"}

            self.report(
                {"INFO"},
                f"Imported motion '{action.name}' to armature '{armature.name}'",
            )
            return {"FINISHED"}

        except FileNotFoundError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        except ValueError as e:
            self.report({"ERROR"}, f"Failed to parse motion file: {e}")
            return {"CANCELLED"}
        except Exception as e:
            _logger.exception("Unexpected error importing motion")
            self.report({"ERROR"}, f"Import failed: {e}")
            return {"CANCELLED"}


def menu_func_import(self, _context):
    """Add the operator to the import menu."""
    self.layout.operator(ImportFMOT.bl_idname, text="MHF Motion (.mot)")
