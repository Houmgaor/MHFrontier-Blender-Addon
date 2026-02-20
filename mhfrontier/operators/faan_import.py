# -*- coding: utf-8 -*-
"""
Definition of importer operator for AAN (animation package) files.

Imports Monster Hunter Frontier AAN animation files and applies them
to the active armature as Blender Actions.
"""

import bpy
import bpy_extras

from ..importers.aan import import_aan
from ..logging_config import get_logger

_logger = get_logger("operators")


class ImportFAAN(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
    """Import a Monster Hunter Frontier AAN animation file (.aan)."""

    bl_idname = "import_scene.mhf_faan"
    bl_label = "Import MHF AAN Animation (.aan)"
    bl_options = {"REGISTER", "PRESET", "UNDO"}

    filename_ext = ".aan"
    filter_glob: bpy.props.StringProperty(
        default="*.aan",
        options={"HIDDEN"},
        maxlen=255,
    )

    animation_mode: bpy.props.EnumProperty(
        name="Animation Mode",
        description="How to interpret AAN parts for bone mapping",
        items=[
            ("monster", "Monster", "Multi-part composite (parts map to body region buckets)"),
            ("player", "Player", "Upper/lower body split (even=upper, odd=lower)"),
        ],
        default="monster",
    )

    motion_index: bpy.props.IntProperty(
        name="Motion Index",
        description="Index of the motion slot to import from each part",
        default=0,
        min=0,
    )

    def execute(self, context):
        """Import the AAN file and apply to active armature."""
        armature = context.active_object

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

        try:
            bpy.ops.object.mode_set(mode="OBJECT")
        except RuntimeError as error:
            _logger.debug(f"Mode switch warning: {error}")

        filepath = self.properties.filepath

        try:
            action = import_aan(
                filepath,
                armature,
                mode=self.animation_mode,
                motion_index=self.motion_index,
            )

            if action is None:
                self.report({"WARNING"}, "No animation data found in AAN file.")
                return {"CANCELLED"}

            self.report(
                {"INFO"},
                f"Imported AAN animation '{action.name}' to armature '{armature.name}'",
            )
            return {"FINISHED"}

        except FileNotFoundError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        except ValueError as e:
            self.report({"ERROR"}, f"Failed to parse AAN file: {e}")
            return {"CANCELLED"}
        except Exception as e:
            _logger.exception("Unexpected error importing AAN")
            self.report({"ERROR"}, f"Import failed: {e}")
            return {"CANCELLED"}


def menu_func_import(self, _context):
    """Add the operator to the import menu."""
    self.layout.operator(ImportFAAN.bl_idname, text="MHF AAN Animation (.aan)")
