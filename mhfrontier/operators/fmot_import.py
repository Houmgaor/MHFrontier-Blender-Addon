# -*- coding: utf-8 -*-
"""
Definition of importer operator for FMOT (motion) files.

Imports Monster Hunter Frontier animation files (.mot, .bin) and applies them
to the active armature as Blender Actions.
"""

import struct

import bpy
import bpy_extras

from ..importers import import_motion
from ..importers.motion import import_motion_from_bytes
from ..fmod.fmot import BLOCK_ANIMATION_HEADER
from ..logging_config import get_logger

_logger = get_logger("operators")


class ImportFMOT(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
    """Import a Monster Hunter Frontier motion file (.mot or .bin)."""

    bl_idname = "import_scene.mhf_fmot"
    bl_label = "Import MHF Motion (.mot/.bin)"
    bl_options = {"REGISTER", "PRESET", "UNDO"}

    # ImportHelper mixin class uses this
    filename_ext = ".mot"
    filter_glob: bpy.props.StringProperty(
        default="*.mot;*.bin",
        options={"HIDDEN"},
        maxlen=255,
    )

    animation_index: bpy.props.IntProperty(
        name="Animation Index",
        description="Index of animation to import from .bin container (0 = first)",
        default=0,
        min=0,
    )

    def execute(self, context):
        """Import the motion file and apply to active armature."""
        import os

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

        filepath = self.properties.filepath
        _, ext = os.path.splitext(filepath.lower())

        # Import the motion
        try:
            if ext == ".bin":
                # Handle .bin container with multiple animations
                action = self._import_from_bin(filepath, armature)
            else:
                # Handle .mot single animation file
                action = import_motion(filepath, armature)

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

    def _import_from_bin(self, filepath: str, armature) -> any:
        """
        Import animation from a .bin container file.

        .bin files contain multiple animation blocks. This extracts the
        animation at the specified index.

        :param filepath: Path to .bin file.
        :param armature: Blender armature object.
        :return: Created Action, or None.
        """
        import os

        with open(filepath, "rb") as f:
            data = f.read()

        # Find all animation blocks
        blocks = []
        for i in range(0, len(data) - 16, 4):
            val = struct.unpack_from("<I", data, i)[0]
            if val == BLOCK_ANIMATION_HEADER:
                size = struct.unpack_from("<I", data, i + 8)[0]
                blocks.append((i, size))

        if not blocks:
            _logger.warning(f"No animation blocks found in {filepath}")
            return None

        # Get requested animation index
        idx = self.animation_index
        if idx >= len(blocks):
            _logger.warning(
                f"Animation index {idx} out of range (file has {len(blocks)} animations)"
            )
            idx = 0

        offset, size = blocks[idx]
        anim_data = data[offset : offset + size]

        # Generate action name from filename
        basename = os.path.splitext(os.path.basename(filepath))[0]
        action_name = f"{basename}_anim_{idx}"

        return import_motion_from_bytes(anim_data, armature, action_name)


def menu_func_import(self, _context):
    """Add the operator to the import menu."""
    self.layout.operator(ImportFMOT.bl_idname, text="MHF Motion (.mot/.bin)")
