# -*- coding: utf-8 -*-
"""
Abstraction layer for the import of FSKL file.

Converts parsed skeleton data to Blender empty object hierarchies.
"""

from typing import Any, Dict, Optional

from ..config import AXIS_REMAP, IMPORT_SCALE
from ..blender.builders import Builders, get_builders
from ..fmod import fskl


def import_skeleton(
    fskl_path: str,
    builders: Optional[Builders] = None,
) -> Any:
    """
    Import an FSKL (Frontier SKeLeton) file to Blender.

    The skeleton will be a hierarchy of empty objects, not an armature.

    :param fskl_path: File path.
    :param builders: Optional builders (defaults to Blender implementation).
    :return: The root armature object.
    """
    if builders is None:
        builders = get_builders()

    skeleton = fskl.get_frontier_skeleton(fskl_path)
    armature_object = builders.object.create_object("FSKL Tree", None)
    builders.object.link_to_scene(armature_object)

    current_skeleton: Dict[str, Any] = {"Root": armature_object}
    for bone in skeleton.values():
        import_bone(bone, current_skeleton, skeleton, builders)

    return armature_object


def deserialize_pose_vector(
    vec4: tuple,
    builders: Optional[Builders] = None,
) -> Any:
    """
    Pose vector to matrix with units conversions.

    Applies IMPORT_SCALE and AXIS_REMAP from config to convert
    Frontier coordinates to Blender coordinate system.

    :param vec4: 4-element pose vector.
    :param builders: Optional builders (defaults to Blender implementation).
    :return: Transform matrix.
    """
    if builders is None:
        builders = get_builders()

    transform = builders.matrix.identity(4)
    for i in range(4):
        j = AXIS_REMAP[i]
        transform[i][3] = vec4[j] * IMPORT_SCALE
    return transform


def import_bone(
    bone: Any,
    skeleton: Dict[str, Any],
    skeleton_structure: Dict[int, Any],
    builders: Optional[Builders] = None,
) -> None:
    """
    Import a single bone as an object.

    Recursively iterate through skeleton_structure to create bones in skeleton.

    :param bone: Blender object representing the bone (FBone).
    :param skeleton: Incomplete skeleton containing bones.
    :param skeleton_structure: Skeleton to build.
    :param builders: Optional builders (defaults to Blender implementation).
    """
    if builders is None:
        builders = get_builders()

    bone_name = "Bone.%03d" % bone.nodeID
    # Bone already exists -> skip
    if bone_name in skeleton:
        return

    bone_object = builders.object.create_object(bone_name, None)
    skeleton[bone_name] = bone_object
    builders.object.link_to_scene(bone_object)

    # Check if parent exists, if not create it
    parent_name = "Root" if bone.parentID == -1 else "Bone.%03d" % bone.parentID
    if parent_name not in skeleton:
        import_bone(
            skeleton_structure[bone.parentID],
            skeleton,
            skeleton_structure,
            builders,
        )

    # Edit the bone properties
    builders.object.set_custom_property(bone_object, "id", bone.nodeID)
    builders.object.set_parent(bone_object, skeleton[parent_name])
    builders.object.set_matrix_local(
        bone_object, deserialize_pose_vector(bone.posVec, builders)
    )
    builders.object.set_display_properties(
        bone_object,
        show_wire=True,
        show_in_front=True,
        show_bounds=True,
    )
