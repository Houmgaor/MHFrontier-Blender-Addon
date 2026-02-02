"""
Exporter operator for FMOD (Frontier Model) files.

Provides File > Export > MHF FMOD menu entry.
"""

import bpy
import bpy_extras

from ..export.blender_extractor import MeshExtractor, MaterialExtractor, ExtractedMaterial
from ..export.fmod_export import export_fmod
from ..logging_config import get_logger

_logger = get_logger("operators")


class ExportFMOD(bpy.types.Operator, bpy_extras.io_utils.ExportHelper):
    """Export 3D model to MHF FMOD file format."""

    bl_idname = "custom_export.export_mhf_fmod"
    bl_label = "Export MHF FMOD file (.fmod)"
    bl_options = {"REGISTER", "PRESET"}

    # ExportHelper mixin class uses this
    filename_ext = ".fmod"
    filter_glob: bpy.props.StringProperty(
        default="*.fmod",
        options={"HIDDEN"},
        maxlen=255,
    )

    export_selected: bpy.props.BoolProperty(
        name="Selected Only",
        description="Export only selected mesh objects",
        default=False,
    )

    apply_modifiers: bpy.props.BoolProperty(
        name="Apply Modifiers",
        description="Apply modifiers before exporting",
        default=True,
    )

    def execute(self, context):
        """Export the model to file."""
        # Get objects to export
        if self.export_selected:
            objects = [obj for obj in context.selected_objects if obj.type == "MESH"]
        else:
            objects = [obj for obj in context.scene.objects if obj.type == "MESH"]

        if not objects:
            self.report({"ERROR"}, "No mesh objects to export")
            return {"CANCELLED"}

        # Extract mesh data
        mesh_extractor = MeshExtractor(apply_modifiers=self.apply_modifiers)
        material_extractor = MaterialExtractor()
        depsgraph = context.evaluated_depsgraph_get()

        meshes = []
        materials_dict = {}  # Track unique materials

        for obj in objects:
            try:
                mesh = mesh_extractor.extract(obj, depsgraph)
                meshes.append(mesh)

                # Collect materials from this object
                if obj.data.materials:
                    for mat in obj.data.materials:
                        if mat and mat.name not in materials_dict:
                            materials_dict[mat.name] = material_extractor.extract(mat)
            except Exception as e:
                _logger.warning("Failed to extract mesh %s: %s", obj.name, e)
                continue

        if not meshes:
            self.report({"ERROR"}, "Failed to extract any meshes")
            return {"CANCELLED"}

        # Convert materials dict to list
        materials = list(materials_dict.values())
        if not materials:
            materials = [ExtractedMaterial(name="Default")]

        try:
            export_fmod(self.filepath, meshes, materials)
            self.report(
                {"INFO"},
                f"Exported {len(meshes)} meshes and {len(materials)} materials to {self.filepath}",
            )
        except Exception as e:
            _logger.exception("FMOD export failed")
            self.report({"ERROR"}, f"Export failed: {e}")
            return {"CANCELLED"}

        return {"FINISHED"}

    def draw(self, context):
        """Draw the export options panel."""
        layout = self.layout
        layout.prop(self, "export_selected")
        layout.prop(self, "apply_modifiers")


def menu_func_export(self, _context):
    """Add the operator to the export menu."""
    self.layout.operator(ExportFMOD.bl_idname, text="MHF FMOD (.fmod)")
