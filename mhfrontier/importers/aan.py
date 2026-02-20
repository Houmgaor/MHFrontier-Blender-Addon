# -*- coding: utf-8 -*-
"""
AAN animation import orchestration for Blender.

Converts parsed AAN data to Blender Actions with FCurves.
Supports both monster (multi-part composite) and player (upper/lower body split)
animation modes.
"""

from typing import Any, Dict, List, Optional, Tuple

from ..config import IMPORT_SCALE
from ..blender.builders import Builders, get_builders
from ..logging_config import get_logger
from ..fmod import faan
from ..fmod.faan import AANChannelFlag, AANData, AANKeyframe

from .motion import _calculate_bezier_handles, _set_bone_rotation_mode

_logger = get_logger("aan_importer")


def _aan_channel_to_property_info(
    channel_flag: int,
) -> Tuple[Optional[str], int, str]:
    """Map AAN channel flag to Blender property info.

    Coordinate conversion (MHF Y-up -> Blender Z-up):
    - MHF X -> Blender X (index 0)
    - MHF Y -> Blender Z (index 2)
    - MHF Z -> Blender Y (index 1)

    :param channel_flag: AAN channel flag.
    :return: Tuple of (property_name, array_index, transform_type).
    """
    if channel_flag == AANChannelFlag.LOCATION_X:
        return "location", 0, "location"
    elif channel_flag == AANChannelFlag.LOCATION_Y:
        return "location", 2, "location"
    elif channel_flag == AANChannelFlag.LOCATION_Z:
        return "location", 1, "location"
    elif channel_flag == AANChannelFlag.ROTATION_X:
        return "rotation_euler", 0, "rotation"
    elif channel_flag == AANChannelFlag.ROTATION_Y:
        return "rotation_euler", 2, "rotation"
    elif channel_flag == AANChannelFlag.ROTATION_Z:
        return "rotation_euler", 1, "rotation"
    elif channel_flag == AANChannelFlag.SCALE_X:
        return "scale", 0, "scale"
    elif channel_flag == AANChannelFlag.SCALE_Y:
        return "scale", 2, "scale"
    elif channel_flag == AANChannelFlag.SCALE_Z:
        return "scale", 1, "scale"

    return None, 0, "unknown"


def _should_negate_aan_rotation(channel_flag: int) -> bool:
    """Check if an AAN rotation channel must be negated for coordinate conversion.

    Y-up to Z-up conversion:
    - MHF X rotation -> negate
    - MHF Y rotation -> negate
    - MHF Z rotation -> no negation

    :param channel_flag: AAN channel flag.
    :return: True if the rotation should be negated.
    """
    if channel_flag == AANChannelFlag.ROTATION_X:
        return True
    if channel_flag == AANChannelFlag.ROTATION_Y:
        return True
    return False


def _transform_aan_value(
    value: float,
    transform_type: str,
    negate: bool = False,
) -> float:
    """Transform an AAN keyframe value from Frontier to Blender.

    AAN rotation values are already in radians after parsing (short values
    were scaled by AAN_SHORT_ROTATION_SCALE, float values are stored as radians).

    :param value: Parsed value (already decoded from raw format).
    :param transform_type: Type of transform ('location', 'rotation', 'scale').
    :param negate: If True, negate the result.
    :return: Transformed value for Blender.
    """
    if transform_type == "location":
        return value * IMPORT_SCALE
    elif transform_type == "rotation":
        return -value if negate else value
    elif transform_type == "scale":
        return value
    return value


def _transform_aan_tangent(
    tangent: float,
    transform_type: str,
    negate: bool = False,
) -> float:
    """Transform an AAN tangent value.

    :param tangent: Parsed tangent (already decoded from raw format).
    :param transform_type: Type of transform.
    :param negate: If True, negate the result.
    :return: Transformed tangent for Blender.
    """
    if transform_type == "location":
        return tangent * IMPORT_SCALE
    elif transform_type == "rotation":
        return -tangent if negate else tangent
    elif transform_type == "scale":
        return tangent
    return tangent


def _get_bone_buckets(armature: Any) -> Dict[int, List[str]]:
    """Build bone buckets from armature part_id custom properties.

    Groups bones by their part_id, preserving bone index order within each bucket.
    Falls back to putting all bones in bucket 0 if no part_id properties exist.

    :param armature: Blender armature object.
    :return: Dict mapping bucket_id to ordered list of bone names.
    """
    buckets: Dict[int, List[str]] = {}

    if armature is None:
        return buckets

    pose = getattr(armature, "pose", None)
    if pose is None:
        return buckets
    bones = getattr(pose, "bones", None)
    if bones is None:
        return buckets

    # Try to get bone names in order
    bone_list = []
    if hasattr(bones, "keys"):
        bone_list = list(bones.keys())
    elif hasattr(bones, "__iter__"):
        bone_list = [b.name if hasattr(b, "name") else str(b) for b in bones]

    has_part_ids = False
    for bone_name in bone_list:
        bone = bones[bone_name] if hasattr(bones, "__getitem__") else None
        if bone is None:
            continue

        # Check for part_id custom property
        part_id = None
        bone_obj = getattr(bone, "bone", bone)
        if hasattr(bone_obj, "get"):
            part_id = bone_obj.get("part_id")
        elif hasattr(bone_obj, "custom_properties"):
            part_id = bone_obj.custom_properties.get("part_id")

        if part_id is not None:
            has_part_ids = True
            bucket_id = int(part_id)
        else:
            bucket_id = 0

        if bucket_id not in buckets:
            buckets[bucket_id] = []
        buckets[bucket_id].append(bone_name)

    if not has_part_ids and bone_list:
        # Fallback: all bones in bucket 0
        buckets[0] = bone_list

    return buckets


def _apply_tracks_to_action(
    tracks,
    bone_names: List[str],
    action: Any,
    builders: Builders,
    armature: Any,
) -> None:
    """Apply bone tracks to an action for a list of bone names.

    :param tracks: List of AANBoneTrack objects.
    :param bone_names: Bone names to map tracks to (same order as tracks).
    :param action: Blender Action to add FCurves to.
    :param builders: Builder interfaces.
    :param armature: Blender armature object (for rotation mode setting).
    """
    for track_idx, track in enumerate(tracks):
        if track_idx >= len(bone_names):
            break

        bone_name = bone_names[track_idx]
        has_rotation = False

        for channel in track.channels:
            prop_name, index, transform_type = _aan_channel_to_property_info(
                channel.channel_flag
            )

            if prop_name is None:
                continue

            if transform_type == "rotation":
                has_rotation = True

            negate = _should_negate_aan_rotation(channel.channel_flag)

            data_path = f'pose.bones["{bone_name}"].{prop_name}'
            fcurve = builders.animation.create_fcurve(action, data_path, index)

            for kf in channel.keyframes:
                value = _transform_aan_value(kf.value, transform_type, negate)

                handle_left = None
                handle_right = None

                if kf.interpolation == "BEZIER" and (
                    kf.tangent_in != 0 or kf.tangent_out != 0
                ):
                    tan_in = _transform_aan_tangent(
                        kf.tangent_in, transform_type, negate
                    )
                    tan_out = _transform_aan_tangent(
                        kf.tangent_out, transform_type, negate
                    )
                    handle_left, handle_right = _calculate_bezier_handles(
                        float(kf.frame),
                        value,
                        tan_in,
                        tan_out,
                        transform_type,
                        negate=False,  # Already negated above
                    )

                builders.animation.add_keyframe(
                    fcurve,
                    float(kf.frame),
                    value,
                    interpolation=kf.interpolation,
                    handle_left=handle_left,
                    handle_right=handle_right,
                )

        if has_rotation:
            _set_bone_rotation_mode(armature, bone_name, "XZY")


def import_aan_monster(
    filepath: str,
    armature: Any,
    motion_index: int = 0,
    builders: Optional[Builders] = None,
) -> Any:
    """Import an AAN file in monster mode.

    Composites all parts for a given motion slot into one Action.
    Bone tracks are mapped to skeleton bones via part-based bone buckets:
    AAN parts 0,1 -> bucket 0; parts 2,3 -> bucket 1; etc.

    :param filepath: Path to .aan file.
    :param armature: Blender armature object.
    :param motion_index: Index of the motion to import from each part.
    :param builders: Optional builders (defaults to Blender implementation).
    :return: Created Action, or None if import failed.
    """
    if builders is None:
        builders = get_builders()

    aan_data = faan.load_aan_file(filepath)

    if not aan_data.parts:
        _logger.warning(f"No parts found in {filepath}")
        return None

    action_name = aan_data.name or "MHF_AAN_Monster"
    action = builders.animation.create_action(f"{action_name}_m{motion_index}")

    buckets = _get_bone_buckets(armature)

    max_frame = 0

    for part_idx, part in enumerate(aan_data.parts):
        if motion_index >= len(part.motions):
            continue

        motion = part.motions[motion_index]
        if not motion.bone_tracks:
            continue

        # Map part index to bucket: parts 0,1 -> bucket 0; 2,3 -> bucket 1
        bucket_id = part_idx // 2
        bone_names = buckets.get(bucket_id, [])

        if not bone_names:
            # Fallback: sequential bone naming
            start_bone = 0
            for b in range(bucket_id):
                bone_names_b = buckets.get(b, [])
                start_bone += len(bone_names_b) if bone_names_b else 0
            bone_names = [
                f"Bone.{start_bone + i:03d}"
                for i in range(len(motion.bone_tracks))
            ]

        _apply_tracks_to_action(
            motion.bone_tracks, bone_names, action, builders, armature
        )

        if motion.frame_count > max_frame:
            max_frame = motion.frame_count

    if max_frame > 0:
        builders.animation.set_action_frame_range(action, 0, max_frame - 1)

    if armature is not None:
        builders.animation.assign_action_to_object(armature, action)

    _logger.info(
        f"Imported AAN monster animation '{action.name}' with "
        f"{len(aan_data.parts)} parts, motion index {motion_index}"
    )

    return action


def import_aan_player(
    filepath: str,
    armature: Any,
    motion_index: int = 0,
    builders: Optional[Builders] = None,
) -> Any:
    """Import an AAN file in player mode.

    Even-indexed parts map to upper body (bucket 0),
    odd-indexed parts map to lower body (bucket 1).

    :param filepath: Path to .aan file.
    :param armature: Blender armature object.
    :param motion_index: Index of the motion to import from each part.
    :param builders: Optional builders (defaults to Blender implementation).
    :return: Created Action, or None if import failed.
    """
    if builders is None:
        builders = get_builders()

    aan_data = faan.load_aan_file(filepath)

    if not aan_data.parts:
        _logger.warning(f"No parts found in {filepath}")
        return None

    action_name = aan_data.name or "MHF_AAN_Player"
    action = builders.animation.create_action(f"{action_name}_m{motion_index}")

    buckets = _get_bone_buckets(armature)

    max_frame = 0

    for part_idx, part in enumerate(aan_data.parts):
        if motion_index >= len(part.motions):
            continue

        motion = part.motions[motion_index]
        if not motion.bone_tracks:
            continue

        # Player mode: even parts = upper body (bucket 0),
        # odd parts = lower body (bucket 1)
        bucket_id = 0 if part_idx % 2 == 0 else 1
        bone_names = buckets.get(bucket_id, [])

        if not bone_names:
            bone_names = [
                f"Bone.{i:03d}" for i in range(len(motion.bone_tracks))
            ]

        _apply_tracks_to_action(
            motion.bone_tracks, bone_names, action, builders, armature
        )

        if motion.frame_count > max_frame:
            max_frame = motion.frame_count

    if max_frame > 0:
        builders.animation.set_action_frame_range(action, 0, max_frame - 1)

    if armature is not None:
        builders.animation.assign_action_to_object(armature, action)

    _logger.info(
        f"Imported AAN player animation '{action.name}' with "
        f"{len(aan_data.parts)} parts, motion index {motion_index}"
    )

    return action


def import_aan(
    filepath: str,
    armature: Any,
    mode: str = "monster",
    motion_index: int = 0,
    builders: Optional[Builders] = None,
) -> Any:
    """Import an AAN animation file.

    Dispatcher that selects monster or player import mode.

    :param filepath: Path to .aan file.
    :param armature: Blender armature object.
    :param mode: Animation mode ('monster' or 'player').
    :param motion_index: Index of the motion slot to import.
    :param builders: Optional builders (defaults to Blender implementation).
    :return: Created Action, or None if import failed.
    """
    if mode == "player":
        return import_aan_player(filepath, armature, motion_index, builders)
    else:
        return import_aan_monster(filepath, armature, motion_index, builders)
