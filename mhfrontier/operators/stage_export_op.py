"""
Exporter operator for stage container files (.pac).

Provides File > Export > MHF Stage Container menu entry.
"""

import bpy
import bpy_extras

from ..export.stage_export import export_stage, StageExportOptions
from ..stage.jkr_decompress import CompressionType
from ..logging_config import get_logger

_logger = get_logger("operators")


class ExportStage(bpy.types.Operator, bpy_extras.io_utils.ExportHelper):
    """Export collection to MHF Stage Container file format."""

    bl_idname = "custom_export.export_mhf_stage"
    bl_label = "Export MHF Stage Container (.pac)"
    bl_options = {"REGISTER", "PRESET"}

    # ExportHelper mixin class uses this
    filename_ext = ".pac"
    filter_glob: bpy.props.StringProperty(
        default="*.pac",
        options={"HIDDEN"},
        maxlen=255,
    )

    export_collection: bpy.props.StringProperty(
        name="Collection",
        description="Name of collection to export (leave empty for active collection)",
        default="",
    )

    compress_segments: bpy.props.BoolProperty(
        name="Compress Segments",
        description="Apply JKR compression to FMOD segments",
        default=True,
    )

    compression_type: bpy.props.EnumProperty(
        name="Compression Type",
        description="JKR compression algorithm to use",
        items=[
            ("RW", "Raw (No Compression)", "No compression, just JKR header wrapper"),
            ("HFI", "HFI (Recommended)", "Huffman + LZ77 compression (best ratio)"),
            ("LZ", "LZ77 Only", "LZ77 compression without Huffman"),
            ("HFIRW", "Huffman Only", "Huffman compression without LZ77"),
        ],
        default="HFI",
    )

    include_textures: bpy.props.BoolProperty(
        name="Include Textures",
        description="Export texture segments (if available)",
        default=True,
    )

    include_audio: bpy.props.BoolProperty(
        name="Include Audio",
        description="Export audio segments (if available)",
        default=True,
    )

    apply_modifiers: bpy.props.BoolProperty(
        name="Apply Modifiers",
        description="Apply modifiers before exporting meshes",
        default=True,
    )

    def execute(self, context):
        """Export the stage container to file."""
        # Get collection to export
        if self.export_collection:
            collection = bpy.data.collections.get(self.export_collection)
            if collection is None:
                self.report({"ERROR"}, f"Collection '{self.export_collection}' not found")
                return {"CANCELLED"}
        else:
            # Use active collection or scene collection
            collection = context.view_layer.active_layer_collection.collection

        if collection is None:
            self.report({"ERROR"}, "No collection selected for export")
            return {"CANCELLED"}

        # Count mesh objects
        mesh_count = sum(1 for obj in collection.all_objects if obj.type == "MESH")
        if mesh_count == 0:
            self.report({"WARNING"}, f"No mesh objects in collection '{collection.name}'")

        # Map compression type string to enum
        compression_map = {
            "RW": CompressionType.RW,
            "HFI": CompressionType.HFI,
            "LZ": CompressionType.LZ,
            "HFIRW": CompressionType.HFIRW,
        }
        compression = compression_map.get(self.compression_type, CompressionType.HFI)

        # Build export options
        options = StageExportOptions(
            compress_segments=self.compress_segments,
            compression_type=compression,
            include_textures=self.include_textures,
            include_audio=self.include_audio,
            apply_modifiers=self.apply_modifiers,
        )

        # Get dependency graph
        depsgraph = context.evaluated_depsgraph_get()

        try:
            export_stage(self.filepath, collection, depsgraph, options)
            self.report(
                {"INFO"},
                f"Exported collection '{collection.name}' ({mesh_count} meshes) to {self.filepath}",
            )
        except Exception as e:
            _logger.exception("Stage export failed")
            self.report({"ERROR"}, f"Export failed: {e}")
            return {"CANCELLED"}

        return {"FINISHED"}

    def draw(self, context):
        """Draw the export options panel."""
        layout = self.layout

        # Collection selection
        layout.prop_search(
            self,
            "export_collection",
            bpy.data,
            "collections",
            text="Collection",
        )

        layout.separator()

        # Compression options
        box = layout.box()
        box.label(text="Compression")
        box.prop(self, "compress_segments")
        if self.compress_segments:
            box.prop(self, "compression_type")

        layout.separator()

        # Content options
        box = layout.box()
        box.label(text="Content")
        box.prop(self, "include_textures")
        box.prop(self, "include_audio")

        layout.separator()

        # Mesh options
        box = layout.box()
        box.label(text="Mesh Options")
        box.prop(self, "apply_modifiers")


def menu_func_export(self, _context):
    """Add the operator to the export menu."""
    self.layout.operator(ExportStage.bl_idname, text="MHF Stage Container (.pac)")
