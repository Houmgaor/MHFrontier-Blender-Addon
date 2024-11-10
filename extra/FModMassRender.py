"""Renderer for multiple files at once."""

from pathlib import Path

from bpy_extras import bpy, bmesh
from mathutils import Vector, Matrix


def set_viewport(space, ctx, position):
    """Set the viewport for a file rendering."""
    rv3d = space.region_3d
    rv3d.view_matrix = position
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.view3d.view_selected(ctx)
    bpy.ops.object.select_all(action="DESELECT")


def render_file(filepath):
    """Render a single file."""
    filepath = filepath.resolve().as_posix()
    bpy.ops.custom_import.import_mhf_fmod(filepath=filepath)
    space, area = next(
        (
            (space, area)
            for area in bpy.context.screen.areas
            if area.type == "VIEW_3D"
            for space in area.spaces
            if space.type == "VIEW_3D"
        )
    )
    ctx = bpy.context.copy()
    ctx["area"] = area
    ctx["region"] = area.regions[-1]
    space.viewport_shade = "TEXTURED"
    for ix, position in enumerate(
        [
            Matrix.Rotation(i, 4, "Z")
            * Matrix.Rotation(j, 4, "Y")
            * Matrix.Rotation(k, 4, "X")
            for i in range(-45, 46, 45)
            for j in range(-45, 46, 45)
            for k in range(-45, 46, 45)
        ]
    ):
        # Y is axis of weapons and armour
        set_viewport(space, ctx, position)
        bpy.context.scene.render.image_settings.file_format = "PNG"
        bpy.context.scene.render.alpha_mode = "TRANSPARENT"
        bpy.context.scene.render.resolution_percentage = 100
        bpy.context.scene.render.filepath = filepath[:-4] + "-Angle %d" % ix + ".JPEG"
        bpy.ops.render.opengl(write_still=True)


frontier = r"G:\Frontier"
map(render_file, Path(frontier).rglob("*.fmod"))
