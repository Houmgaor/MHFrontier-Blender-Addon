"""
Abstraction layer for the import of FSKL file.

Created on Mon Dec 30 01:17:01 2019

@author: AsteriskAmpersand
"""

import bpy
from mathutils import Vector, Matrix

from ..config import AXIS_REMAP, IMPORT_SCALE
from ..fmod import fskl


def import_skeleton(fskl_path):
    """
    Import an FSKL (Frontier SKeLeton) file to Blender.

    The skeleton will be a hierarchy of empty objects, not an armature.

    :param str fskl_path: File path.
    """

    skeleton = fskl.get_frontier_skeleton(fskl_path)
    armature_object = bpy.data.objects.new("FSKL Tree", None)
    if bpy.app.version >= (2, 8):
        # Blender 2.8+
        bpy.context.collection.objects.link(armature_object)
    else:
        # Blender <2.8
        bpy.context.scene.objects.link(armature_object)
    current_skeleton = {"Root": armature_object}
    for bone in skeleton.values():
        import_bone(bone, current_skeleton, skeleton)


def deserialize_pose_vector(vec4):
    """
    Pose vector to matrix with units conversions.

    Applies IMPORT_SCALE and AXIS_REMAP from config to convert
    Frontier coordinates to Blender coordinate system.

    :return mathutils.Matrix: transform matrix
    """
    transform = Matrix.Identity(4)
    for i in range(4):
        j = AXIS_REMAP[i]
        transform[i][3] = vec4[j] * IMPORT_SCALE
    return transform


def import_bone(bone, skeleton, skeleton_structure):
    """
    Import a single bone as an object.

    Recursively iterate through skeleton_structure to create bones in skeleton.

    :param bone: Blender object representing the bone.
    :type bone: mhfrontier.fmod.fskl.FBone
    :param dict skeleton: Incomplete skeleton containing bones.
    :param skeleton_structure: Skeleton to build.
    :type skeleton_structure: dict[mhfrontier.fmod.fskl.FBone]
    """

    bone_name = "Bone.%03d" % bone.nodeID
    # Bone already exists -> skip
    if bone_name in skeleton:
        return
    bone_object = bpy.data.objects.new(bone_name, None)
    skeleton[bone_name] = bone_object
    if bpy.app.version >= (2, 8):
        # Blender 2.8+
        bpy.context.collection.objects.link(bone_object)
    else:
        # Blender <2.8
        bpy.context.scene.objects.link(bone_object)

    # Check if parent exists, if not create it
    parent_name = "Root" if bone.parentID == -1 else "Bone.%03d" % bone.parentID
    if parent_name not in skeleton:
        import_bone(skeleton_structure[bone.parentID], skeleton, skeleton_structure)

    # Edit the bone properties
    bone_object["id"] = bone.nodeID
    bone_object.parent = skeleton[parent_name]
    bone_object.matrix_local = deserialize_pose_vector(bone.posVec)
    bone_object.show_wire = True
    if bpy.app.version >= (2, 8):
        # Blender 2.8+
        bone_object.show_in_front = True
    else:
        # Blender <2.8
        bone_object.show_x_ray = True
    bone_object.show_bounds = True
