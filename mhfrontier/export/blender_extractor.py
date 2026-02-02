"""
Extract mesh and skeleton data from Blender objects.

Provides classes to extract geometry, materials, and bone data from
Blender objects for export to Frontier file formats.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..config import (
    EXPORT_SCALE,
    reverse_transform_vertex,
    reverse_transform_vector4,
    reverse_transform_uv,
)
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
