# -*- coding: utf-8 -*-
"""
Created on Tue Aug 18 22:47:34 2020

@author: AsteriskAmpersand
"""
import bpy
from mathutils import Vector, Matrix
from bpy.types import Operator

MACHINE_EPSILON = 2 ** -8


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
    """
    bone = armature.edit_bones.new(anchor.name)
    bone.head = Vector([0, 0, 0])
    bone.tail = Vector([0, MACHINE_EPSILON, 0])  # Vector([0, 1, 0])
    if not parent_bone:
        parent_bone = DummyBone()  # matrix = Identity(4), #boneTail = 0,0,0, boneHead = 0,1,0
    if bpy.app.version[0] >= 2 and bpy.app.version[1] >= 80:
        bone.matrix = parent_bone.matrix @ anchor.matrix_local
    else:
        bone.matrix = parent_bone.matrix * anchor.matrix_local
    for child in anchor.children:
        new_bone = create_bone_tree(armature, child, bone)
        new_bone.parent = bone
    if "id" in anchor:
        bone["id"] = anchor["id"]
    return bone


def create_armature():
    """Create armature from skeleton and parent to model."""
    bone_anchors = [
        o for o in bpy.context.scene.objects if o.type == "EMPTY" and o.parent is None
    ]
    bpy.ops.object.select_all(action='DESELECT')
    blender_armature = bpy.data.armatures.new('Armature')
    arm_ob = bpy.data.objects.new('Armature', blender_armature)
    if bpy.app.version[0] >= 2 and bpy.app.version[1] >= 80:
        bpy.context.collection.objects.link(arm_ob)
        bpy.context.view_layer.update()
        arm_ob.select_set(True)
        arm_ob.show_in_front = True
        bpy.context.view_layer.objects.active = arm_ob
        blender_armature.display_type = 'STICK'
    else:
        bpy.context.scene.objects.link(arm_ob)
        bpy.context.scene.update()
        arm_ob.select = True
        arm_ob.show_x_ray = True
        bpy.context.scene.objects.active = arm_ob
        blender_armature.draw_type = 'STICK'
    bpy.ops.object.mode_set(mode='EDIT')

    # Now add the new bones to the armature
    root_bone = create_root_bone(blender_armature)
    for anchor in bone_anchors:
        bone = create_bone_tree(blender_armature, anchor)
        bone.parent = root_bone
        # arm.pose.bones[ix].matrix

    # Add the armature to the mesh if possible
    bpy.ops.object.editmode_toggle()
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH":
            modifier = obj.modifiers.new("Armature", "ARMATURE")
            modifier.object = arm_ob


class ConvertFSKL(Operator):
    """Register the operator"""
    bl_idname = "frontier_tools.convert_fskl"
    bl_label = "Convert FSKL to Armature"
    bl_options = {'REGISTER', 'PRESET', 'UNDO'}

    @staticmethod
    def execute(self, _context):
        create_armature()
        return {'FINISHED'}
