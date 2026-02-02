"""
Exporter operator for FMOT (Frontier Motion) files.

Provides File > Export > MHF FMOT menu entry.
"""

import bpy
import bpy_extras

from ..export.blender_extractor import MotionExtractor
from ..export.fmot_export import export_fmot
from ..logging_config import get_logger

_logger = get_logger("operators")


class ExportFMOT(bpy.types.Operator, bpy_extras.io_utils.ExportHelper):
    """Export animation to MHF FMOT file format."""

    bl_idname = "custom_export.export_mhf_fmot"
    bl_label = "Export MHF FMOT file (.mot)"
    bl_options = {"REGISTER", "PRESET"}

    # ExportHelper mixin class uses this
    filename_ext = ".mot"
    filter_glob: bpy.props.StringProperty(
        default="*.mot",
        options={"HIDDEN"},
        maxlen=255,
    )

    def execute(self, context):
        """Export the animation to file."""
        # Find the active armature
        obj = context.active_object

        if obj is None:
            self.report({"ERROR"}, "No active object selected")
            return {"CANCELLED"}

        if obj.type != "ARMATURE":
            self.report({"ERROR"}, "Selected object is not an armature")
            return {"CANCELLED"}

        # Get the action from the armature
        if obj.animation_data is None or obj.animation_data.action is None:
            self.report({"ERROR"}, "Armature has no animation action")
            return {"CANCELLED"}

        action = obj.animation_data.action

        # Extract motion data
        extractor = MotionExtractor()
        motion = extractor.extract_from_action(action, obj)

        if not motion.bone_animations:
            self.report({"ERROR"}, "No bone animations found in action")
            return {"CANCELLED"}

        try:
            export_fmot(self.filepath, motion)

            bone_count = len(motion.bone_animations)
            channel_count = sum(
                len(ba.channels) for ba in motion.bone_animations.values()
            )
            self.report(
                {"INFO"},
                f"Exported {bone_count} bones, {channel_count} channels to {self.filepath}",
            )

        except Exception as e:
            _logger.exception("FMOT export failed")
            self.report({"ERROR"}, f"Export failed: {e}")
            return {"CANCELLED"}

        return {"FINISHED"}


def menu_func_export(self, _context):
    """Add the operator to the export menu."""
    self.layout.operator(ExportFMOT.bl_idname, text="MHF FMOT (.mot)")
