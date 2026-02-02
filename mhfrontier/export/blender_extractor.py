"""
Extract mesh and skeleton data from Blender objects.

Provides classes to extract geometry, materials, and bone data from
Blender objects for export to Frontier file formats.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..config import (
    EXPORT_SCALE,
    ROTATION_EXPORT_SCALE,
    reverse_transform_vertex,
    reverse_transform_vector4,
    reverse_transform_uv,
)
from ..fmod.fmot import ChannelType
from ..logging_config import get_logger

_logger = get_logger("export.blender_extractor")


@dataclass
class ExtractedMesh:
    """Extracted mesh data ready for FMOD export."""

    name: str
    vertices: List[Tuple[float, float, float]]
    faces: List[Tuple[int, int, int]]
    normals: List[Tuple[float, float, float]]
    uvs: Optional[List[Tuple[float, float]]] = None
    vertex_colors: Optional[List[Tuple[float, float, float, float]]] = None
    weights: Optional[Dict[int, List[Tuple[int, float]]]] = None
    bone_remap: Optional[List[int]] = None
    material_indices: Optional[List[int]] = None
    material_list: List[int] = field(default_factory=list)


@dataclass
class ExtractedBone:
    """Extracted bone data ready for FSKL export."""

    node_id: int
    parent_id: int
    left_child: int = -1
    right_sibling: int = -1
    scale: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    rotation: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)
    position: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)
    chain_id: int = 0


@dataclass
class ExtractedMaterial:
    """Extracted material data ready for FMOD export."""

    name: str
    ambient_color: Tuple[float, float, float] = (0.5, 0.5, 0.5)
    opacity: float = 1.0
    diffuse_color: Tuple[float, float, float] = (0.8, 0.8, 0.8)
    specular_color: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    material_flags: int = 0
    shininess: float = 30.0
    texture_ids: List[int] = field(default_factory=list)


class MeshExtractor:
    """
    Extract mesh data from Blender mesh objects.

    Handles coordinate transformation from Blender to Frontier format.
    """

    def __init__(self, apply_modifiers: bool = True) -> None:
        """
        Create a mesh extractor.

        :param apply_modifiers: Whether to apply modifiers before extraction.
        """
        self.apply_modifiers = apply_modifiers

    def extract(self, obj: Any, depsgraph: Optional[Any] = None) -> ExtractedMesh:
        """
        Extract mesh data from a Blender object.

        :param obj: Blender mesh object.
        :param depsgraph: Dependency graph for evaluated mesh (optional).
        :return: Extracted mesh data.
        """
        # Get the mesh data (with modifiers applied if requested)
        if self.apply_modifiers and depsgraph is not None:
            eval_obj = obj.evaluated_get(depsgraph)
            mesh = eval_obj.to_mesh()
        else:
            mesh = obj.data

        # Ensure we have triangulated faces
        mesh.calc_loop_triangles()

        # Extract vertices with coordinate transform
        vertices = [
            reverse_transform_vertex((v.co.x, v.co.y, v.co.z))
            for v in mesh.vertices
        ]

        # Extract faces (triangles)
        faces = [
            (tri.vertices[0], tri.vertices[1], tri.vertices[2])
            for tri in mesh.loop_triangles
        ]

        # Extract normals with coordinate transform
        normals = [
            reverse_transform_vertex((v.normal.x, v.normal.y, v.normal.z), scale=1.0)
            for v in mesh.vertices
        ]

        # Extract UVs if available
        uvs = None
        if mesh.uv_layers.active:
            uv_layer = mesh.uv_layers.active.data
            uvs = [None] * len(mesh.vertices)
            for loop_idx, loop in enumerate(mesh.loops):
                vert_idx = loop.vertex_index
                if uvs[vert_idx] is None:
                    uv = uv_layer[loop_idx].uv
                    uvs[vert_idx] = reverse_transform_uv((uv.x, uv.y))
            # Fill any missing UVs with default
            uvs = [uv if uv is not None else (0.0, 0.0) for uv in uvs]

        # Extract vertex colors if available
        vertex_colors = None
        if mesh.color_attributes:
            color_attr = mesh.color_attributes.active_color
            if color_attr is not None:
                vertex_colors = [None] * len(mesh.vertices)
                for i, color in enumerate(color_attr.data):
                    if i < len(mesh.vertices):
                        vertex_colors[i] = (
                            color.color[0],
                            color.color[1],
                            color.color[2],
                            color.color[3] if len(color.color) > 3 else 1.0,
                        )
                vertex_colors = [
                    vc if vc is not None else (1.0, 1.0, 1.0, 1.0)
                    for vc in vertex_colors
                ]

        # Extract vertex weights
        weights = None
        bone_remap = None
        if obj.vertex_groups:
            weights = {}
            bone_names = set()
            for vg in obj.vertex_groups:
                bone_names.add(vg.name)

            for vert in mesh.vertices:
                for group in vert.groups:
                    vg = obj.vertex_groups[group.group]
                    bone_id = group.group
                    weight_value = group.weight * 100.0  # Frontier uses 0-100 range
                    if bone_id not in weights:
                        weights[bone_id] = []
                    weights[bone_id].append((vert.index, weight_value))

            # Create bone remap from vertex group indices
            bone_remap = list(range(len(obj.vertex_groups)))

        # Extract material indices per face
        material_indices = None
        material_list = []
        if mesh.materials:
            material_indices = [tri.material_index for tri in mesh.loop_triangles]
            material_list = list(range(len(mesh.materials)))

        # Clean up evaluated mesh if we created one
        if self.apply_modifiers and depsgraph is not None:
            eval_obj.to_mesh_clear()

        return ExtractedMesh(
            name=obj.name,
            vertices=vertices,
            faces=faces,
            normals=normals,
            uvs=uvs,
            vertex_colors=vertex_colors,
            weights=weights,
            bone_remap=bone_remap,
            material_indices=material_indices,
            material_list=material_list,
        )


class SkeletonExtractor:
    """
    Extract skeleton data from Blender empties or armatures.

    Supports both:
    - Empty object hierarchies (from FSKL import)
    - Blender armatures
    """

    def extract_from_empties(self, root_empty: Any) -> List[ExtractedBone]:
        """
        Extract bones from empty object hierarchy.

        :param root_empty: Root empty object of the skeleton tree.
        :return: List of extracted bones.
        """
        bones = []
        bone_map: Dict[str, int] = {}

        # First pass: collect all bones and assign IDs
        def collect_bones(obj: Any, parent_id: int = -1) -> None:
            # Check if this is a bone empty (has "id" custom property or "Bone." prefix)
            is_bone = (
                "id" in obj
                or obj.name.startswith("Bone.")
                or (obj.parent is not None and obj.parent.name in bone_map)
            )

            if is_bone:
                # Extract bone ID from custom property or name
                if "id" in obj:
                    node_id = int(obj["id"])
                elif obj.name.startswith("Bone."):
                    try:
                        node_id = int(obj.name.split(".")[1])
                    except (IndexError, ValueError):
                        node_id = len(bones)
                else:
                    node_id = len(bones)

                bone_map[obj.name] = node_id

                # Get local position from matrix
                local_matrix = obj.matrix_local
                position = (
                    local_matrix[0][3] * EXPORT_SCALE,
                    local_matrix[2][3] * EXPORT_SCALE,
                    local_matrix[1][3] * EXPORT_SCALE,
                    1.0,
                )

                bones.append(ExtractedBone(
                    node_id=node_id,
                    parent_id=parent_id,
                    position=position,
                ))

                # Process children
                current_id = node_id
            else:
                current_id = parent_id

            for child in obj.children:
                collect_bones(child, current_id)

        collect_bones(root_empty)

        # Second pass: compute left_child and right_sibling relationships
        self._compute_bone_tree_structure(bones)

        return bones

    def extract_from_armature(self, armature_obj: Any) -> List[ExtractedBone]:
        """
        Extract bones from a Blender armature.

        :param armature_obj: Blender armature object.
        :return: List of extracted bones.
        """
        armature = armature_obj.data
        bones = []
        bone_map: Dict[str, int] = {}

        # Create mapping from bone names to IDs
        for i, bone in enumerate(armature.bones):
            bone_map[bone.name] = i

        for i, bone in enumerate(armature.bones):
            parent_id = bone_map[bone.parent.name] if bone.parent else -1

            # Get bone position (head in armature space)
            head = bone.head_local
            position = (
                head.x * EXPORT_SCALE,
                head.z * EXPORT_SCALE,
                head.y * EXPORT_SCALE,
                1.0,
            )

            bones.append(ExtractedBone(
                node_id=i,
                parent_id=parent_id,
                position=position,
            ))

        # Compute tree structure
        self._compute_bone_tree_structure(bones)

        return bones

    def _compute_bone_tree_structure(self, bones: List[ExtractedBone]) -> None:
        """
        Compute left_child and right_sibling for bone tree structure.

        Frontier uses a left-child right-sibling tree representation.

        :param bones: List of bones to update in place.
        """
        # Group bones by parent
        children_by_parent: Dict[int, List[int]] = {}
        for bone in bones:
            parent = bone.parent_id
            if parent not in children_by_parent:
                children_by_parent[parent] = []
            children_by_parent[parent].append(bone.node_id)

        # Build bone lookup
        bone_lookup: Dict[int, ExtractedBone] = {b.node_id: b for b in bones}

        # Assign left_child and right_sibling
        for parent_id, children in children_by_parent.items():
            if not children:
                continue

            # First child becomes left_child of parent
            if parent_id >= 0 and parent_id in bone_lookup:
                bone_lookup[parent_id].left_child = children[0]

            # Link siblings
            for i, child_id in enumerate(children[:-1]):
                bone_lookup[child_id].right_sibling = children[i + 1]


class MaterialExtractor:
    """Extract material data from Blender materials."""

    def extract(self, material: Any) -> ExtractedMaterial:
        """
        Extract material properties from a Blender material.

        :param material: Blender material.
        :return: Extracted material data.
        """
        if material is None:
            return ExtractedMaterial(name="Default")

        # Default values
        diffuse = (0.8, 0.8, 0.8)
        ambient = (0.5, 0.5, 0.5)
        specular = (1.0, 1.0, 1.0, 1.0)
        opacity = 1.0
        shininess = 30.0
        texture_ids = []

        # Try to extract from node tree
        if material.use_nodes and material.node_tree:
            for node in material.node_tree.nodes:
                if node.type == "BSDF_PRINCIPLED":
                    # Get base color
                    base_color = node.inputs.get("Base Color")
                    if base_color:
                        color = base_color.default_value
                        diffuse = (color[0], color[1], color[2])

                    # Get roughness as inverse of shininess
                    roughness = node.inputs.get("Roughness")
                    if roughness:
                        shininess = (1.0 - roughness.default_value) * 100.0

                    # Get alpha
                    alpha = node.inputs.get("Alpha")
                    if alpha:
                        opacity = alpha.default_value

                    break

        return ExtractedMaterial(
            name=material.name,
            ambient_color=ambient,
            opacity=opacity,
            diffuse_color=diffuse,
            specular_color=specular,
            material_flags=0,
            shininess=shininess,
            texture_ids=texture_ids,
        )


# =============================================================================
# Motion/Animation Extraction
# =============================================================================


@dataclass
class ExtractedKeyframe:
    """Extracted keyframe data ready for FMOT export."""
    frame: int
    value: float
    tangent_in: float = 0.0
    tangent_out: float = 0.0


@dataclass
class ExtractedChannel:
    """Extracted animation channel (e.g., position X)."""
    channel_type: int
    keyframes: List[ExtractedKeyframe] = field(default_factory=list)


@dataclass
class ExtractedBoneAnimation:
    """Extracted animation data for a single bone."""
    bone_id: int
    channels: Dict[int, ExtractedChannel] = field(default_factory=dict)


@dataclass
class ExtractedMotion:
    """Complete extracted motion/animation data."""
    name: str
    frame_count: int
    bone_animations: Dict[int, ExtractedBoneAnimation] = field(default_factory=dict)


# Mapping from Blender FCurve (data_path, index) to Frontier channel type
# Note: Y/Z are swapped between Blender (Z-up) and Frontier (Y-up)
BLENDER_TO_FRONTIER_CHANNEL: Dict[Tuple[str, int], int] = {
    ("location", 0): ChannelType.POSITION_X,
    ("location", 1): ChannelType.POSITION_Z,  # Blender Y -> Frontier Z
    ("location", 2): ChannelType.POSITION_Y,  # Blender Z -> Frontier Y
    ("rotation_euler", 0): ChannelType.ROTATION_X,
    ("rotation_euler", 1): ChannelType.ROTATION_Z,  # Blender Y -> Frontier Z
    ("rotation_euler", 2): ChannelType.ROTATION_Y,  # Blender Z -> Frontier Y
    ("scale", 0): ChannelType.SCALE_X,
    ("scale", 1): ChannelType.SCALE_Z,  # Blender Y -> Frontier Z
    ("scale", 2): ChannelType.SCALE_Y,  # Blender Z -> Frontier Y
}


class MotionExtractor:
    """
    Extract motion/animation data from Blender Actions.

    Converts Blender FCurves to Frontier keyframe format with appropriate
    coordinate and value transformations.
    """

    def __init__(self) -> None:
        """Create a motion extractor."""
        self._logger = get_logger("export.motion_extractor")

    def extract_from_action(
        self,
        action: Any,
        armature: Any,
    ) -> ExtractedMotion:
        """
        Extract motion data from a Blender Action.

        :param action: Blender Action containing animation data.
        :param armature: Blender armature the action is associated with.
        :return: Extracted motion data.
        """
        motion = ExtractedMotion(
            name=action.name if action else "Unknown",
            frame_count=0,
            bone_animations={},
        )

        if action is None:
            return motion

        # Get frame range
        frame_start, frame_end = action.frame_range
        motion.frame_count = int(frame_end - frame_start) + 1

        # Process each FCurve
        for fcurve in action.fcurves:
            self._process_fcurve(fcurve, motion)

        return motion

    def _process_fcurve(self, fcurve: Any, motion: ExtractedMotion) -> None:
        """
        Process a single FCurve and add to motion data.

        :param fcurve: Blender FCurve.
        :param motion: Motion data to add to.
        """
        data_path = fcurve.data_path
        array_index = fcurve.array_index

        # Parse bone name from data path (e.g., 'pose.bones["Bone.001"].location')
        bone_id = self._extract_bone_id(data_path)
        if bone_id is None:
            self._logger.debug(f"Skipping non-bone FCurve: {data_path}")
            return

        # Extract property name (location, rotation_euler, scale)
        prop_name = self._extract_property_name(data_path)
        if prop_name is None:
            self._logger.debug(f"Unknown property in FCurve: {data_path}")
            return

        # Map to Frontier channel type
        channel_key = (prop_name, array_index)
        if channel_key not in BLENDER_TO_FRONTIER_CHANNEL:
            self._logger.debug(f"Unknown channel mapping: {channel_key}")
            return

        channel_type = BLENDER_TO_FRONTIER_CHANNEL[channel_key]

        # Get or create bone animation
        if bone_id not in motion.bone_animations:
            motion.bone_animations[bone_id] = ExtractedBoneAnimation(
                bone_id=bone_id,
                channels={},
            )

        bone_anim = motion.bone_animations[bone_id]

        # Get or create channel
        if channel_type not in bone_anim.channels:
            bone_anim.channels[channel_type] = ExtractedChannel(
                channel_type=channel_type,
                keyframes=[],
            )

        channel = bone_anim.channels[channel_type]

        # Determine transform type for value conversion
        transform_type = self._get_transform_type(prop_name)

        # Extract keyframes
        for kp in fcurve.keyframe_points:
            keyframe = self._extract_keyframe(kp, transform_type)
            channel.keyframes.append(keyframe)

        # Sort keyframes by frame
        channel.keyframes.sort(key=lambda kf: kf.frame)

    def _extract_bone_id(self, data_path: str) -> Optional[int]:
        """
        Extract bone ID from FCurve data path.

        Handles paths like 'pose.bones["Bone.001"].location'.

        :param data_path: FCurve data path.
        :return: Bone ID or None if not a bone path.
        """
        import re

        # Match 'pose.bones["Bone.XXX"]' pattern
        match = re.search(r'pose\.bones\["Bone\.(\d+)"\]', data_path)
        if match:
            return int(match.group(1))

        # Also try matching just a numeric bone name
        match = re.search(r'pose\.bones\["(\d+)"\]', data_path)
        if match:
            return int(match.group(1))

        return None

    def _extract_property_name(self, data_path: str) -> Optional[str]:
        """
        Extract the property name from a data path.

        :param data_path: FCurve data path.
        :return: Property name (location, rotation_euler, scale) or None.
        """
        if data_path.endswith(".location"):
            return "location"
        elif data_path.endswith(".rotation_euler"):
            return "rotation_euler"
        elif data_path.endswith(".scale"):
            return "scale"
        return None

    def _get_transform_type(self, prop_name: str) -> str:
        """
        Get transform type from property name.

        :param prop_name: Property name.
        :return: Transform type string.
        """
        if prop_name == "location":
            return "position"
        elif prop_name == "rotation_euler":
            return "rotation"
        elif prop_name == "scale":
            return "scale"
        return "unknown"

    def _extract_keyframe(
        self,
        keyframe_point: Any,
        transform_type: str,
    ) -> ExtractedKeyframe:
        """
        Extract a keyframe from a Blender keyframe point.

        Converts value and tangents from Blender to Frontier format.

        :param keyframe_point: Blender keyframe point.
        :param transform_type: Type of transform (position, rotation, scale).
        :return: Extracted keyframe.
        """
        frame = int(keyframe_point.co[0])
        blender_value = keyframe_point.co[1]

        # Transform value from Blender to Frontier
        value = self._transform_value(blender_value, transform_type)

        # Extract tangents from Bezier handles
        tangent_in = 0.0
        tangent_out = 0.0

        if keyframe_point.interpolation == "BEZIER":
            handle_left = keyframe_point.handle_left
            handle_right = keyframe_point.handle_right

            # Reverse of _calculate_bezier_handles from motion.py
            # handle_distance = 1.0 / 3.0
            # handle_left = (frame - handle_distance, value - tan_in * handle_distance)
            # handle_right = (frame + handle_distance, value + tan_out * handle_distance)
            handle_distance = 1.0 / 3.0

            # Calculate tangent from handle offset
            # Note: We need to use the transformed value for consistency
            tan_in_raw = (blender_value - handle_left[1]) / handle_distance
            tan_out_raw = (handle_right[1] - blender_value) / handle_distance

            # Transform tangents
            tangent_in = self._transform_tangent(tan_in_raw, transform_type)
            tangent_out = self._transform_tangent(tan_out_raw, transform_type)

        return ExtractedKeyframe(
            frame=frame,
            value=value,
            tangent_in=tangent_in,
            tangent_out=tangent_out,
        )

    def _transform_value(self, value: float, transform_type: str) -> float:
        """
        Transform a value from Blender to Frontier format.

        :param value: Blender value.
        :param transform_type: Type of transform.
        :return: Frontier format value.
        """
        if transform_type == "position":
            # Scale positions (Blender → Frontier: multiply by 100)
            return value * EXPORT_SCALE

        elif transform_type == "rotation":
            # Convert radians to int16-compatible value
            return value * ROTATION_EXPORT_SCALE

        elif transform_type == "scale":
            # Scale is stored as offset from 1.0
            # Blender 1.0 = no scale, Frontier 0 = no scale
            return (value - 1.0) * 32768.0

        return value

    def _transform_tangent(self, tangent: float, transform_type: str) -> float:
        """
        Transform a tangent value from Blender to Frontier format.

        :param tangent: Blender tangent value.
        :param transform_type: Type of transform.
        :return: Frontier format tangent.
        """
        if transform_type == "position":
            return tangent * EXPORT_SCALE
        elif transform_type == "rotation":
            return tangent * ROTATION_EXPORT_SCALE
        elif transform_type == "scale":
            return tangent * 32768.0
        return tangent
