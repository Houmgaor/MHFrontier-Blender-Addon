# -*- coding: utf-8 -*-
"""
Created on Tue Aug 18 22:47:34 2020

@author: AsteriskAmpersand
"""
import bpy
from mathutils import Vector, Matrix

MACHINE_EPSILON = 2**-8


class DummyBone:
    """Dummy for Blender bones."""

    def __init__(self):
        self.matrix = Matrix.Identity(4)
        self.head = Vector([0, -1, 0])
        self.tail = Vector([0, 0, 0])
        self.magnitude = 1


def create_root_bone(armature):
    """Root bone of "null" size."""
    bone = armature.edit_bones.new("Bone.255")
    bone.head = Vector([0, 0, 0])
    bone.tail = Vector([0, MACHINE_EPSILON, 0])
    bone.matrix = Matrix.Identity(4)
    return bone


def create_bone_tree(armature, anchor, parent_bone=None):
    """
    Create a new bone tree to the armature.

    :param armature: Armature to edit.
    :param anchor: Skeleton anchor (Blender object) to use
    :param parent_bone: Specify a parent bone (used for recursion)

    :return: Root of the created bone tree
    """
    bone = armature.edit_bones.new(anchor.name)
    bone.head = Vector([0, 0, 0])
    bone.tail = Vector([0, MACHINE_EPSILON, 0])
    if not parent_bone:
        parent_bone = (
            DummyBone()
        )  # matrix = Identity(4), #boneTail = 0,0,0, boneHead = 0,1,0
    if bpy.app.version >= (2, 8):
        bone.matrix = parent_bone.matrix @ anchor.matrix_local
    else:
        bone.matrix = parent_bone.matrix * anchor.matrix_local
    for child in anchor.children:
        new_bone = create_bone_tree(armature, child, bone)
        new_bone.parent = bone
    if "id" in anchor:
        bone["id"] = anchor["id"]
    return bone


def create_armature(context):
    """Create armature from skeleton and parent to model."""
    bone_anchors = []
    for scene_object in context.scene.objects:
        if scene_object.type == "EMPTY" and scene_object.parent is None:
            bone_anchors.append(scene_object)
    bpy.ops.object.select_all(action="DESELECT")
    blender_armature = bpy.data.armatures.new("Armature")
    arm_ob = bpy.data.objects.new("Armature", blender_armature)
    if bpy.app.version >= (2, 8):
        context.collection.objects.link(arm_ob)
        context.view_layer.update()
        arm_ob.select_set(True)
        arm_ob.show_in_front = True
        context.view_layer.objects.active = arm_ob
        blender_armature.display_type = "STICK"
    else:
        context.scene.objects.link(arm_ob)
        context.scene.update()
        arm_ob.select = True
        arm_ob.show_x_ray = True
        context.scene.objects.active = arm_ob
        blender_armature.draw_type = "STICK"
    bpy.ops.object.mode_set(mode="EDIT")

    # Now add the new bones to the armature
    root_bone = create_root_bone(blender_armature)
    for anchor in bone_anchors:
        bone = create_bone_tree(blender_armature, anchor)
        bone.parent = root_bone

    # Add the armature to the mesh if possible
    bpy.ops.object.editmode_toggle()
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH":
            modifier = obj.modifiers.new("Armature", "ARMATURE")
            modifier.object = arm_ob


class ConvertFSKL(bpy.types.Operator):
    """Operator to convert a Frontier Skeleton to Blender Armature."""

    bl_idname = "object.convert_fskl"
    bl_label = "Create an Armature from FSKL tree"
    bl_options = {"REGISTER", "PRESET", "UNDO"}

    def execute(self, context):
        """Create the armature, _context is not used."""
        create_armature(context)
        return {"FINISHED"}

    def draw(self, _context):
        layout = self.layout
        layout.label(text="Create Armature from FSKL Tree", icon="armature_data")


def menu_func(self, _context):
    """Add armature creation operator to the right click."""
    self.layout.operator(ConvertFSKL.bl_idname)
