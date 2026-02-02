# -*- coding: utf-8 -*-
"""
Mock implementations of Blender interfaces for testing.

These classes store data in plain Python objects, allowing unit tests
to run without requiring Blender to be installed.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

from .api import (
    MeshBuilder,
    ObjectBuilder,
    MaterialBuilder,
    ImageLoader,
    SceneManager,
    MatrixFactory,
)


@dataclass
class MockMesh:
    """Mock mesh data structure."""

    name: str
    vertices: List[Tuple[float, float, float]] = field(default_factory=list)
    faces: List[List[int]] = field(default_factory=list)
    normals: List[List[float]] = field(default_factory=list)
    uv_layers: Dict[str, Any] = field(default_factory=dict)
    uvs: List[List[float]] = field(default_factory=list)
    face_materials: List[int] = field(default_factory=list)
    materials: List[Any] = field(default_factory=list)
    updated: bool = False


@dataclass
class MockObject:
    """Mock Blender object data structure."""

    name: str
    data: Any = None
    parent: Optional["MockObject"] = None
    matrix_local: Any = None
    custom_properties: Dict[str, Any] = field(default_factory=dict)
    vertex_groups: Dict[str, "MockVertexGroup"] = field(default_factory=dict)
    show_wire: bool = False
    show_in_front: bool = False
    show_bounds: bool = False
    linked_to_scene: bool = False


@dataclass
class MockVertexGroup:
    """Mock vertex group data structure."""

    name: str
    weights: Dict[int, float] = field(default_factory=dict)


@dataclass
class MockMaterial:
    """Mock material data structure."""

    name: str
    use_nodes: bool = False
    node_tree: Optional["MockNodeTree"] = None


@dataclass
class MockNodeTree:
    """Mock shader node tree."""

    nodes: Dict[str, "MockNode"] = field(default_factory=dict)
    links: List[Tuple[str, int, str, Any]] = field(default_factory=list)
    _node_counter: int = 0


@dataclass
class MockNode:
    """Mock shader node."""

    type: str
    name: str = ""
    location: Tuple[float, float] = (0, 0)
    image: Any = None
    inputs: Dict[Any, Any] = field(default_factory=dict)
    outputs: Dict[int, Any] = field(default_factory=dict)


@dataclass
class MockImage:
    """Mock image data structure."""

    filepath: str
    name: str = ""


@dataclass
class MockCollection:
    """Mock collection data structure."""

    name: str
    objects: List[MockObject] = field(default_factory=list)


@dataclass
class MockMatrix:
    """Mock 4x4 transformation matrix."""

    values: List[List[float]] = field(default_factory=list)

    def __post_init__(self):
        if not self.values:
            # Initialize as identity matrix
            self.values = [
                [1, 0, 0, 0],
                [0, 1, 0, 0],
                [0, 0, 1, 0],
                [0, 0, 0, 1],
            ]

    def __getitem__(self, index: int) -> List[float]:
        return self.values[index]

    def __setitem__(self, index: int, value: List[float]) -> None:
        self.values[index] = value


class MockMeshBuilder(MeshBuilder):
    """Mock mesh builder for testing."""

    def __init__(self):
        self.created_meshes: List[MockMesh] = []

    def create_mesh(
        self,
        name: str,
        vertices: List[Tuple[float, float, float]],
        faces: List[List[int]],
    ) -> MockMesh:
        mesh = MockMesh(name=name, vertices=list(vertices), faces=list(faces))
        self.created_meshes.append(mesh)
        return mesh

    def set_normals(self, mesh: MockMesh, normals: List[List[float]]) -> None:
        mesh.normals = list(normals)

    def create_uv_layer(self, mesh: MockMesh, name: str) -> str:
        mesh.uv_layers[name] = True
        return name

    def set_uvs(
        self,
        mesh: MockMesh,
        uvs: List[List[float]],
        face_materials: List[int],
    ) -> None:
        mesh.uvs = list(uvs)
        mesh.face_materials = list(face_materials)

    def add_material(self, mesh: MockMesh, material: MockMaterial) -> None:
        mesh.materials.append(material)

    def update_mesh(self, mesh: MockMesh) -> None:
        mesh.updated = True


class MockObjectBuilder(ObjectBuilder):
    """Mock object builder for testing."""

    def __init__(self):
        self.created_objects: List[MockObject] = []
        self.deselect_calls: int = 0

    def create_object(self, name: str, data: Any) -> MockObject:
        obj = MockObject(name=name, data=data)
        self.created_objects.append(obj)
        return obj

    def link_to_scene(self, obj: MockObject) -> None:
        obj.linked_to_scene = True

    def set_parent(self, child: MockObject, parent: MockObject) -> None:
        child.parent = parent

    def set_matrix_local(self, obj: MockObject, matrix: Any) -> None:
        obj.matrix_local = matrix

    def set_custom_property(self, obj: MockObject, key: str, value: Any) -> None:
        obj.custom_properties[key] = value

    def set_display_properties(
        self,
        obj: MockObject,
        show_wire: bool = False,
        show_in_front: bool = False,
        show_bounds: bool = False,
    ) -> None:
        obj.show_wire = show_wire
        obj.show_in_front = show_in_front
        obj.show_bounds = show_bounds

    def create_vertex_group(self, obj: MockObject, name: str) -> MockVertexGroup:
        group = MockVertexGroup(name=name)
        obj.vertex_groups[name] = group
        return group

    def add_vertex_weight(
        self,
        obj: MockObject,
        group_name: str,
        vertex_id: int,
        weight: float,
    ) -> None:
        if group_name not in obj.vertex_groups:
            obj.vertex_groups[group_name] = MockVertexGroup(name=group_name)
        obj.vertex_groups[group_name].weights[vertex_id] = weight

    def deselect_all(self) -> None:
        self.deselect_calls += 1


class MockMaterialBuilder(MaterialBuilder):
    """Mock material builder for testing."""

    def __init__(self):
        self.created_materials: List[MockMaterial] = []
        self.created_nodes: List[MockNode] = []

    def create_material(self, name: str) -> MockMaterial:
        material = MockMaterial(name=name)
        self.created_materials.append(material)
        return material

    def enable_nodes(self, material: MockMaterial) -> MockNodeTree:
        material.use_nodes = True
        material.node_tree = MockNodeTree()
        return material.node_tree

    def clear_nodes(self, node_tree: MockNodeTree) -> None:
        node_tree.nodes.clear()

    def create_principled_bsdf(self, node_tree: MockNodeTree) -> MockNode:
        node = MockNode(type="ShaderNodeBsdfPrincipled", name="Principled BSDF")
        node_tree._node_counter += 1
        node_tree.nodes[f"principled_{node_tree._node_counter}"] = node
        self.created_nodes.append(node)
        return node

    def create_texture_node(
        self,
        node_tree: MockNodeTree,
        texture: MockImage,
        name: str,
        is_data: bool = False,
    ) -> MockNode:
        node = MockNode(type="ShaderNodeTexImage", name=name, image=texture)
        node_tree._node_counter += 1
        node_tree.nodes[f"texture_{node_tree._node_counter}"] = node
        self.created_nodes.append(node)
        return node

    def create_normal_map_node(self, node_tree: MockNodeTree) -> MockNode:
        node = MockNode(type="ShaderNodeNormalMap", name="Normal Map")
        node_tree._node_counter += 1
        node_tree.nodes[f"normal_map_{node_tree._node_counter}"] = node
        self.created_nodes.append(node)
        return node

    def create_transparent_node(self, node_tree: MockNodeTree) -> MockNode:
        node = MockNode(type="ShaderNodeBsdfTransparent")
        node_tree._node_counter += 1
        node_tree.nodes[f"transparent_{node_tree._node_counter}"] = node
        self.created_nodes.append(node)
        return node

    def create_mix_shader_node(self, node_tree: MockNodeTree) -> MockNode:
        node = MockNode(type="ShaderNodeMixShader")
        node_tree._node_counter += 1
        node_tree.nodes[f"mix_shader_{node_tree._node_counter}"] = node
        self.created_nodes.append(node)
        return node

    def create_output_node(self, node_tree: MockNodeTree) -> MockNode:
        node = MockNode(type="ShaderNodeOutputMaterial")
        node_tree._node_counter += 1
        node_tree.nodes[f"output_{node_tree._node_counter}"] = node
        self.created_nodes.append(node)
        return node

    def create_rgb_curve_node(self, node_tree: MockNodeTree) -> MockNode:
        node = MockNode(type="ShaderNodeRGBCurve", name="RGB Curve")
        node_tree._node_counter += 1
        node_tree.nodes[f"rgb_curve_{node_tree._node_counter}"] = node
        self.created_nodes.append(node)
        return node

    def link_nodes(
        self,
        node_tree: MockNodeTree,
        from_node: MockNode,
        from_output: int,
        to_node: MockNode,
        to_input: Union[int, str],
    ) -> None:
        node_tree.links.append((from_node.name, from_output, to_node.name, to_input))

    def set_node_location(self, node: MockNode, x: float, y: float) -> None:
        node.location = (x, y)


class MockImageLoader(ImageLoader):
    """Mock image loader for testing."""

    def __init__(self, available_files: Optional[Dict[str, Any]] = None):
        """
        Initialize with optional pre-loaded files.

        :param available_files: Dict mapping filepath to mock data.
        """
        self.available_files = available_files or {}
        self.loaded_images: List[MockImage] = []

    def load_image(self, filepath: str) -> MockImage:
        if self.available_files and filepath not in self.available_files:
            raise FileNotFoundError(f"File {filepath} not found")
        image = MockImage(filepath=filepath, name=filepath.split("/")[-1])
        self.loaded_images.append(image)
        return image


class MockSceneManager(SceneManager):
    """Mock scene manager for testing."""

    def __init__(self):
        self.render_engine: str = ""
        self.collections: List[MockCollection] = []
        self.scene_collections: List[MockCollection] = []

    def set_render_engine(self, engine: str) -> None:
        self.render_engine = engine

    def create_collection(self, name: str) -> MockCollection:
        collection = MockCollection(name=name)
        self.collections.append(collection)
        return collection

    def link_collection_to_scene(self, collection: MockCollection) -> None:
        self.scene_collections.append(collection)

    def link_object_to_collection(
        self, obj: MockObject, collection: MockCollection
    ) -> None:
        collection.objects.append(obj)


class MockMatrixFactory(MatrixFactory):
    """Mock matrix factory for testing."""

    def identity(self, size: int = 4) -> MockMatrix:
        values = [[1 if i == j else 0 for j in range(size)] for i in range(size)]
        return MockMatrix(values=values)

    def from_values(self, values: List[List[float]]) -> MockMatrix:
        return MockMatrix(values=[list(row) for row in values])
