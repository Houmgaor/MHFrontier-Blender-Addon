# -*- coding: utf-8 -*-
"""
Created on Mon Dec 30 01:17:01 2019

@author: AsteriskAmpersand
"""
import bpy
from mathutils import Vector, Matrix

from ..fmod.fskl import FSkeleton


class FSklImporter:
    """Main importer for FSKL (Frontier SKeLeton) files."""

    @staticmethod
    def execute(fmod_path):
        skeleton = FSkeleton(fmod_path).skeleton_structure()
        armature_object = bpy.data.objects.new("FSKL Tree", None)
        if bpy.app.version >= (2, 8):
            # Blender 2.8+
            bpy.context.collection.objects.link(armature_object)
        else:
            # Blender <2.8
            bpy.context.scene.objects.link(armature_object)
        current_skeleton = {"Root": armature_object}
        for bone in skeleton.values():
            FSklImporter.import_bone(bone, current_skeleton, skeleton)

    @staticmethod
    def deserialize_pose_vector(vec4):
        m = Matrix.Identity(4)
        for i in range(4):
            m[i][3] = vec4[i]
        return m

    @staticmethod
    def import_bone(bone, skeleton, skeleton_structure):
        ix = bone.nodeID
        if "Bone.%03d" % ix in skeleton:
            return
        bone_object = bpy.data.objects.new("Bone.%03d" % ix, None)
        skeleton["Bone.%03d" % ix] = bone_object
        if bpy.app.version >= (2, 8):
            # Blender 2.8+
            bpy.context.collection.objects.link(bone_object)
        else:
            # Blender <2.8
            bpy.context.scene.objects.link(bone_object)
        parent_name = "Root" if bone.parentID == -1 else "Bone.%03d" % bone.parentID
        if parent_name not in skeleton:
            FSklImporter.import_bone(
                skeleton_structure[bone.parentID], skeleton, skeleton_structure
            )
        bone_object["id"] = bone.nodeID
        bone_object.parent = skeleton[parent_name]
        bone_object.matrix_local = FSklImporter.deserialize_pose_vector(bone.posVec)
        bone_object.show_wire = True
        if bpy.app.version >= (2, 8):
            # Blender 2.8+
            bone_object.show_in_front = True
        else:
            # Blender <2.8
            bone_object.show_x_ray = True
        bone_object.show_bounds = True
