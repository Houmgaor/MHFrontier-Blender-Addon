# -*- coding: utf-8 -*-
"""
Abstraction layer for importing motion files to Blender animations.

Converts parsed motion data to Blender Actions with FCurves.
"""

from typing import Any, Dict, Optional, Tuple

from ..config import IMPORT_SCALE, ROTATION_SCALE, AXIS_REMAP_3D
from ..blender.api import AnimationBuilder
from ..logging_config import get_logger
from . import fmot
from .fmot import ChannelType, MotionData

_logger = get_logger("fmot_importer")


def _get_default_builder() -> AnimationBuilder:
    """Get default Blender animation builder (lazy import)."""
    from ..blender.blender_impl import get_animation_builder

    return get_animation_builder()


def _channel_to_property_info(channel_type: int) -> Tuple[str, int, str]:
    """
    Map channel type to Blender property info.

    :param channel_type: Motion file channel type.
    :return: Tuple of (property_name, array_index, transform_type).
             transform_type is 'position', 'rotation', or 'scale'.
    """
    # Position channels - need axis remap
    if channel_type == ChannelType.POSITION_X:
        # Frontier X -> Blender X (index 0)
        return "location", 0, "position"
    elif channel_type == ChannelType.POSITION_Y:
        # Frontier Y -> Blender Z (index 2) due to Y-up to Z-up
        return "location", 2, "position"
    elif channel_type == ChannelType.POSITION_Z:
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


def import_motion(
    filepath: str,
    armature: Any,
    animation_builder: Optional[AnimationBuilder] = None,
) -> Any:
    """
    Import a motion file and create a Blender Action.

    :param filepath: Path to .mot file.
    :param armature: Blender armature object to apply animation to.
    :param animation_builder: Optional animation builder (defaults to Blender impl).
    :return: Created Action, or None if import failed.
    """
    if animation_builder is None:
        animation_builder = _get_default_builder()

    # Load motion data
    motion_data = fmot.load_motion_file(filepath)

    if not motion_data.bone_animations:
        _logger.warning(f"No bone animations found in {filepath}")
        return None

    # Create action
    action_name = motion_data.name or "MHF_Motion"
    action = animation_builder.create_action(action_name)

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

        # Process each channel
        for channel_type, channel_anim in bone_anim.channels.items():
            prop_name, index, transform_type = _channel_to_property_info(channel_type)

            if prop_name is None:
                _logger.debug(f"Unknown channel type {channel_type:#x}, skipping")
                continue

            # Build data path for pose bone
            data_path = f'pose.bones["{bone_name}"].{prop_name}'

            # Create FCurve
            fcurve = animation_builder.create_fcurve(action, data_path, index)

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
                animation_builder.add_keyframe(
                    fcurve,
                    float(kf.frame),
                    value,
                    interpolation="BEZIER",
                    handle_left=handle_left,
                    handle_right=handle_right,
                )

    # Set frame range
    if motion_data.frame_count > 0:
        animation_builder.set_action_frame_range(action, 0, motion_data.frame_count - 1)

    # Assign action to armature
    if armature is not None:
        animation_builder.assign_action_to_object(armature, action)

    _logger.info(
        f"Imported motion '{action_name}' with {len(motion_data.bone_animations)} bones, "
        f"{motion_data.frame_count} frames"
    )

    return action


def import_motion_from_bytes(
    data: bytes,
    armature: Any,
    name: str = "MHF_Motion",
    animation_builder: Optional[AnimationBuilder] = None,
) -> Any:
    """
    Import motion data from bytes and create a Blender Action.

    :param data: Raw motion file bytes.
    :param armature: Blender armature object to apply animation to.
    :param name: Name for the created action.
    :param animation_builder: Optional animation builder.
    :return: Created Action, or None if import failed.
    """
    if animation_builder is None:
        animation_builder = _get_default_builder()

    # Load motion data from bytes
    motion_data = fmot.load_motion_from_bytes(data)
    motion_data.name = name

    if not motion_data.bone_animations:
        _logger.warning("No bone animations found in data")
        return None

    # Use the same import logic
    action = animation_builder.create_action(name)

    for bone_id, bone_anim in motion_data.bone_animations.items():
        bone_name = f"Bone.{bone_id:03d}"

        for channel_type, channel_anim in bone_anim.channels.items():
            prop_name, index, transform_type = _channel_to_property_info(channel_type)

            if prop_name is None:
                continue

            data_path = f'pose.bones["{bone_name}"].{prop_name}'
            fcurve = animation_builder.create_fcurve(action, data_path, index)

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

                animation_builder.add_keyframe(
                    fcurve,
                    float(kf.frame),
                    value,
                    interpolation="BEZIER",
                    handle_left=handle_left,
                    handle_right=handle_right,
                )

    if motion_data.frame_count > 0:
        animation_builder.set_action_frame_range(action, 0, motion_data.frame_count - 1)

    if armature is not None:
        animation_builder.assign_action_to_object(armature, action)

    return action
