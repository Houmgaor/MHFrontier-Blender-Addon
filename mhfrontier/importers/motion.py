# -*- coding: utf-8 -*-
"""
Abstraction layer for importing motion files to Blender animations.

Converts parsed motion data to Blender Actions with FCurves.
"""

from typing import Any, Dict, Optional, Tuple

from ..config import IMPORT_SCALE, ROTATION_SCALE
from ..blender.builders import Builders, get_builders
from ..logging_config import get_logger
from ..fmod import fmot
from ..fmod.fmot import ChannelType, MotionData

_logger = get_logger("motion_importer")


def _channel_to_property_info(channel_type: int, bone_id: int = 0) -> Tuple[Optional[str], int, str]:
    """
    Map channel type to Blender property info.

    Note: Position animation is only applied to bone 0 (root) because
    MHF animation position values appear to be absolute/world positions,
    not local bone offsets. Applying them to child bones causes distortion.

    :param channel_type: Motion file channel type.
    :param bone_id: Bone ID (used to filter position animation).
    :return: Tuple of (property_name, array_index, transform_type).
             transform_type is 'position', 'rotation', or 'scale'.
    """
    # Position channels - only apply to root bone (bone 0)
    # Other bones' position data appears to be IK targets or world positions
    if channel_type == ChannelType.POSITION_X:
        if bone_id != 0:
            return None, 0, "position"  # Skip non-root position
        return "location", 0, "position"
    elif channel_type == ChannelType.POSITION_Y:
        if bone_id != 0:
            return None, 0, "position"
        # Frontier Y -> Blender Z (index 2) due to Y-up to Z-up
        return "location", 2, "position"
    elif channel_type == ChannelType.POSITION_Z:
        if bone_id != 0:
            return None, 0, "position"
        # Frontier Z -> Blender Y (index 1) due to Y-up to Z-up
        return "location", 1, "position"

    # Rotation channels - need axis remap
    elif channel_type == ChannelType.ROTATION_X:
        # Frontier X -> Blender X (index 0)
        return "rotation_euler", 0, "rotation"
    elif channel_type == ChannelType.ROTATION_Y:
        # Frontier Y -> Blender Z (index 2)
        return "rotation_euler", 2, "rotation"
    elif channel_type == ChannelType.ROTATION_Z:
        # Frontier Z -> Blender Y (index 1)
        return "rotation_euler", 1, "rotation"

    # Scale channels
    elif channel_type == ChannelType.SCALE_X:
        return "scale", 0, "scale"
    elif channel_type == ChannelType.SCALE_Y:
        return "scale", 2, "scale"  # Y/Z swap
    elif channel_type == ChannelType.SCALE_Z:
        return "scale", 1, "scale"  # Y/Z swap

    # Unknown channel
    return None, 0, "unknown"


def _transform_value(
    value: float,
    transform_type: str,
    channel_type: int,
) -> float:
    """
    Transform a keyframe value from Frontier to Blender.

    :param value: Raw value from motion file.
    :param transform_type: Type of transform ('position', 'rotation', 'scale').
    :param channel_type: Original channel type.
    :return: Transformed value for Blender.
    """
    if transform_type == "position":
        # Scale positions
        return value * IMPORT_SCALE

    elif transform_type == "rotation":
        # Convert to radians
        return value * ROTATION_SCALE

    elif transform_type == "scale":
        # Scale is typically a multiplier, may need adjustment
        # If stored as fixed-point, divide accordingly
        # For now assume 1.0 = no scale change
        if value == 0:
            return 1.0
        return value / 32768.0 if abs(value) > 10 else value

    return value


def _transform_tangent(
    tangent: float,
    transform_type: str,
) -> float:
    """
    Transform a Bezier tangent value.

    :param tangent: Raw tangent from motion file.
    :param transform_type: Type of transform.
    :return: Transformed tangent.
    """
    if transform_type == "position":
        return tangent * IMPORT_SCALE
    elif transform_type == "rotation":
        return tangent * ROTATION_SCALE
    elif transform_type == "scale":
        return tangent / 32768.0 if abs(tangent) > 10 else tangent
    return tangent


def _calculate_bezier_handles(
    frame: float,
    value: float,
    tangent_in: float,
    tangent_out: float,
    transform_type: str,
) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    """
    Calculate Bezier handle positions from tangent values.

    Tangent values represent the slope of the curve at the keyframe.
    We convert these to handle offsets for Blender.

    :param frame: Keyframe frame number.
    :param value: Keyframe value.
    :param tangent_in: Incoming tangent (slope).
    :param tangent_out: Outgoing tangent (slope).
    :param transform_type: Transform type for scaling.
    :return: Tuple of (handle_left, handle_right) positions.
    """
    # Handle offset distance (in frames)
    handle_distance = 1.0 / 3.0

    # Transform tangents
    tan_in = _transform_tangent(tangent_in, transform_type)
    tan_out = _transform_tangent(tangent_out, transform_type)

    # Calculate handle positions
    # Left handle: go backwards in time, down/up by tangent
    handle_left = (
        frame - handle_distance,
        value - tan_in * handle_distance,
    )

    # Right handle: go forwards in time, down/up by tangent
    handle_right = (
        frame + handle_distance,
        value + tan_out * handle_distance,
    )

    return handle_left, handle_right


def _set_bone_rotation_mode(armature: Any, bone_name: str, mode: str = "XYZ") -> None:
    """
    Set the rotation mode for a pose bone.

    Blender bones default to QUATERNION rotation, but MHF animations use
    Euler rotations. This must be set before animation data is applied.

    :param armature: Blender armature object.
    :param bone_name: Name of the bone.
    :param mode: Rotation mode ('XYZ', 'QUATERNION', etc.).
    """
    if armature is None:
        return
    pose = getattr(armature, "pose", None)
    if pose is None:
        return
    bones = getattr(pose, "bones", None)
    if bones is None:
        return
    if bone_name in bones:
        bones[bone_name].rotation_mode = mode


def import_motion(
    filepath: str,
    armature: Any,
    builders: Optional[Builders] = None,
) -> Any:
    """
    Import a motion file and create a Blender Action.

    :param filepath: Path to .mot file.
    :param armature: Blender armature object to apply animation to.
    :param builders: Optional builders (defaults to Blender implementation).
    :return: Created Action, or None if import failed.
    """
    if builders is None:
        builders = get_builders()

    # Load motion data
    motion_data = fmot.load_motion_file(filepath)

    if not motion_data.bone_animations:
        _logger.warning(f"No bone animations found in {filepath}")
        return None

    # Create action
    action_name = motion_data.name or "MHF_Motion"
    action = builders.animation.create_action(action_name)

    # Process each bone's animations
    for bone_id, bone_anim in motion_data.bone_animations.items():
        bone_name = f"Bone.{bone_id:03d}"

        # Check if bone exists in armature
        if armature is not None:
            pose_bones = getattr(armature, "pose", None)
            if pose_bones is not None:
                bones = getattr(pose_bones, "bones", {})
                if bone_name not in bones:
                    _logger.debug(f"Bone {bone_name} not in armature, skipping")
                    continue
                # Set rotation mode to Euler for animation compatibility
                _set_bone_rotation_mode(armature, bone_name, "XYZ")

        # Process each channel
        for channel_type, channel_anim in bone_anim.channels.items():
            prop_name, index, transform_type = _channel_to_property_info(channel_type, bone_id)

            if prop_name is None:
                # Skip this channel (e.g., position on non-root bones)
                continue

            # Build data path for pose bone
            data_path = f'pose.bones["{bone_name}"].{prop_name}'

            # Create FCurve
            fcurve = builders.animation.create_fcurve(action, data_path, index)

            # Add keyframes
            for kf in channel_anim.keyframes:
                # Transform value
                value = _transform_value(kf.value, transform_type, channel_type)

                # Calculate handles if tangents are non-zero
                handle_left = None
                handle_right = None

                if kf.tangent_in != 0 or kf.tangent_out != 0:
                    handle_left, handle_right = _calculate_bezier_handles(
                        float(kf.frame),
                        value,
                        kf.tangent_in,
                        kf.tangent_out,
                        transform_type,
                    )

                # Add keyframe
                builders.animation.add_keyframe(
                    fcurve,
                    float(kf.frame),
                    value,
                    interpolation="BEZIER",
                    handle_left=handle_left,
                    handle_right=handle_right,
                )

    # Set frame range
    if motion_data.frame_count > 0:
        builders.animation.set_action_frame_range(action, 0, motion_data.frame_count - 1)

    # Assign action to armature
    if armature is not None:
        builders.animation.assign_action_to_object(armature, action)

    _logger.info(
        f"Imported motion '{action_name}' with {len(motion_data.bone_animations)} bones, "
        f"{motion_data.frame_count} frames"
    )

    return action


def import_motion_from_bytes(
    data: bytes,
    armature: Any,
    name: str = "MHF_Motion",
    builders: Optional[Builders] = None,
) -> Any:
    """
    Import motion data from bytes and create a Blender Action.

    :param data: Raw motion file bytes.
    :param armature: Blender armature object to apply animation to.
    :param name: Name for the created action.
    :param builders: Optional builders (defaults to Blender implementation).
    :return: Created Action, or None if import failed.
    """
    if builders is None:
        builders = get_builders()

    # Load motion data from bytes
    motion_data = fmot.load_motion_from_bytes(data)
    motion_data.name = name

    if not motion_data.bone_animations:
        _logger.warning("No bone animations found in data")
        return None

    # Use the same import logic
    action = builders.animation.create_action(name)

    for bone_id, bone_anim in motion_data.bone_animations.items():
        bone_name = f"Bone.{bone_id:03d}"

        # Set rotation mode to Euler for animation compatibility
        _set_bone_rotation_mode(armature, bone_name, "XYZ")

        for channel_type, channel_anim in bone_anim.channels.items():
            prop_name, index, transform_type = _channel_to_property_info(channel_type, bone_id)

            if prop_name is None:
                continue

            data_path = f'pose.bones["{bone_name}"].{prop_name}'
            fcurve = builders.animation.create_fcurve(action, data_path, index)

            for kf in channel_anim.keyframes:
                value = _transform_value(kf.value, transform_type, channel_type)

                handle_left = None
                handle_right = None

                if kf.tangent_in != 0 or kf.tangent_out != 0:
                    handle_left, handle_right = _calculate_bezier_handles(
                        float(kf.frame),
                        value,
                        kf.tangent_in,
                        kf.tangent_out,
                        transform_type,
                    )

                builders.animation.add_keyframe(
                    fcurve,
                    float(kf.frame),
                    value,
                    interpolation="BEZIER",
                    handle_left=handle_left,
                    handle_right=handle_right,
                )

    if motion_data.frame_count > 0:
        builders.animation.set_action_frame_range(action, 0, motion_data.frame_count - 1)

    if armature is not None:
        builders.animation.assign_action_to_object(armature, action)

    return action
