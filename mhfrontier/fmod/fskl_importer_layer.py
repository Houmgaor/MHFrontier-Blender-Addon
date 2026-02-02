"""
Abstraction layer for the import of FSKL file.

Created on Mon Dec 30 01:17:01 2019

@author: AsteriskAmpersand
"""

from typing import Any, Dict, Optional

from ..config import AXIS_REMAP, IMPORT_SCALE
from ..blender.api import ObjectBuilder, MatrixFactory
from ..fmod import fskl


def _get_default_builders() -> tuple[ObjectBuilder, MatrixFactory]:
    """Get default Blender builders (lazy import to avoid Blender dependency at import time)."""
    from ..blender.blender_impl import get_object_builder, get_matrix_factory

    return get_object_builder(), get_matrix_factory()


def import_skeleton(
    fskl_path: str,
    object_builder: Optional[ObjectBuilder] = None,
    matrix_factory: Optional[MatrixFactory] = None,
) -> Any:
    """
    Import an FSKL (Frontier SKeLeton) file to Blender.

    The skeleton will be a hierarchy of empty objects, not an armature.

    :param fskl_path: File path.
    :param object_builder: Optional object builder (defaults to Blender implementation).
    :param matrix_factory: Optional matrix factory (defaults to Blender implementation).
    :return: The root armature object.
    """
    if object_builder is None or matrix_factory is None:
        default_obj, default_mat = _get_default_builders()
        object_builder = object_builder or default_obj
        matrix_factory = matrix_factory or default_mat

    skeleton = fskl.get_frontier_skeleton(fskl_path)
    armature_object = object_builder.create_object("FSKL Tree", None)
    object_builder.link_to_scene(armature_object)

    current_skeleton: Dict[str, Any] = {"Root": armature_object}
    for bone in skeleton.values():
        import_bone(
            bone, current_skeleton, skeleton, object_builder, matrix_factory
        )

    return armature_object


def deserialize_pose_vector(
    vec4: tuple,
    matrix_factory: Optional[MatrixFactory] = None,
) -> Any:
    """
    Pose vector to matrix with units conversions.

    Applies IMPORT_SCALE and AXIS_REMAP from config to convert
    Frontier coordinates to Blender coordinate system.

    :param vec4: 4-element pose vector.
    :param matrix_factory: Optional matrix factory (defaults to Blender implementation).
    :return: Transform matrix.
    """
    if matrix_factory is None:
        _, matrix_factory = _get_default_builders()

    transform = matrix_factory.identity(4)
    for i in range(4):
        j = AXIS_REMAP[i]
        transform[i][3] = vec4[j] * IMPORT_SCALE
    return transform


def import_bone(
    bone: Any,
    skeleton: Dict[str, Any],
    skeleton_structure: Dict[int, Any],
    object_builder: Optional[ObjectBuilder] = None,
    matrix_factory: Optional[MatrixFactory] = None,
) -> None:
    """
    Import a single bone as an object.

    Recursively iterate through skeleton_structure to create bones in skeleton.

    :param bone: Blender object representing the bone (FBone).
    :param skeleton: Incomplete skeleton containing bones.
    :param skeleton_structure: Skeleton to build.
    :param object_builder: Optional object builder (defaults to Blender implementation).
    :param matrix_factory: Optional matrix factory (defaults to Blender implementation).
    """
    if object_builder is None or matrix_factory is None:
        default_obj, default_mat = _get_default_builders()
        object_builder = object_builder or default_obj
        matrix_factory = matrix_factory or default_mat

    bone_name = "Bone.%03d" % bone.nodeID
    # Bone already exists -> skip
    if bone_name in skeleton:
        return

    bone_object = object_builder.create_object(bone_name, None)
    skeleton[bone_name] = bone_object
    object_builder.link_to_scene(bone_object)

    # Check if parent exists, if not create it
    parent_name = "Root" if bone.parentID == -1 else "Bone.%03d" % bone.parentID
    if parent_name not in skeleton:
        import_bone(
            skeleton_structure[bone.parentID],
            skeleton,
            skeleton_structure,
            object_builder,
            matrix_factory,
        )

    # Edit the bone properties
    object_builder.set_custom_property(bone_object, "id", bone.nodeID)
    object_builder.set_parent(bone_object, skeleton[parent_name])
    object_builder.set_matrix_local(
        bone_object, deserialize_pose_vector(bone.posVec, matrix_factory)
    )
    object_builder.set_display_properties(
        bone_object,
        show_wire=True,
        show_in_front=True,
        show_bounds=True,
    )
