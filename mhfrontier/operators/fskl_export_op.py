"""
Exporter operator for FSKL (Frontier Skeleton) files.

Provides File > Export > MHF FSKL menu entry.
"""

import bpy
import bpy_extras

from ..export.blender_extractor import SkeletonExtractor
from ..export.fskl_export import export_fskl
from ..logging_config import get_logger

_logger = get_logger("operators")


class ExportFSKL(bpy.types.Operator, bpy_extras.io_utils.ExportHelper):
    """Export skeleton to MHF FSKL file format."""

    bl_idname = "custom_export.export_mhf_fskl"
    bl_label = "Export MHF FSKL file (.fskl)"
    bl_options = {"REGISTER", "PRESET"}

    # ExportHelper mixin class uses this
    filename_ext = ".fskl"
    filter_glob: bpy.props.StringProperty(
        default="*.fskl",
        options={"HIDDEN"},
        maxlen=255,
    )

    source_type: bpy.props.EnumProperty(
        name="Source Type",
        description="Type of object to export as skeleton",
        items=[
            ("EMPTIES", "Empty Hierarchy", "Export from empty object hierarchy (from FSKL import)"),
            ("ARMATURE", "Armature", "Export from Blender armature"),
        ],
        default="EMPTIES",
    )

    def execute(self, context):
        """Export the skeleton to file."""
        # Find the source object
        obj = context.active_object
        if obj is None:
            self.report({"ERROR"}, "No active object selected")
            return {"CANCELLED"}

        extractor = SkeletonExtractor()

        if self.source_type == "EMPTIES":
            # Find the root of the empty hierarchy
            root = obj
            while root.parent is not None:
                root = root.parent

            bones = extractor.extract_from_empties(root)

            if not bones:
                self.report({"ERROR"}, "No bones found in empty hierarchy")
                return {"CANCELLED"}

        elif self.source_type == "ARMATURE":
            if obj.type != "ARMATURE":
                self.report({"ERROR"}, "Selected object is not an armature")
                return {"CANCELLED"}

            bones = extractor.extract_from_armature(obj)

            if not bones:
                self.report({"ERROR"}, "No bones found in armature")
                return {"CANCELLED"}

        else:
            self.report({"ERROR"}, f"Unknown source type: {self.source_type}")
            return {"CANCELLED"}

        try:
            export_fskl(self.filepath, bones)
            self.report({"INFO"}, f"Exported {len(bones)} bones to {self.filepath}")
        except Exception as e:
            _logger.exception("FSKL export failed")
            self.report({"ERROR"}, f"Export failed: {e}")
            return {"CANCELLED"}

        return {"FINISHED"}

    def draw(self, context):
        """Draw the export options panel."""
        layout = self.layout
        layout.prop(self, "source_type")


def menu_func_export(self, _context):
    """Add the operator to the export menu."""
    self.layout.operator(ExportFSKL.bl_idname, text="MHF FSKL (.fskl)")
