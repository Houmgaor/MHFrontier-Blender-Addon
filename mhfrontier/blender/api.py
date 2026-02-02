# -*- coding: utf-8 -*-
"""
Abstract interfaces for Blender operations.

These interfaces allow import logic to be tested without requiring Blender.
Concrete implementations are provided in blender_impl.py (real Blender) and
mock_impl.py (testing).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class MeshBuilder(ABC):
    """Abstract interface for mesh creation and manipulation."""

    @abstractmethod
    def create_mesh(
        self,
        name: str,
        vertices: List[Tuple[float, float, float]],
        faces: List[List[int]],
    ) -> Any:
        """
        Create a new mesh from vertices and faces.

        :param name: Name for the mesh.
        :param vertices: List of vertex positions (x, y, z).
        :param faces: List of faces as vertex index lists.
        :return: Created mesh object.
        """
        ...

    @abstractmethod
    def set_normals(self, mesh: Any, normals: List[List[float]]) -> None:
        """
        Set custom normals on a mesh.

        :param mesh: Mesh to modify.
        :param normals: Normal vectors per vertex.
        """
        ...

    @abstractmethod
    def create_uv_layer(self, mesh: Any, name: str) -> Any:
        """
        Create a UV layer on a mesh.

        :param mesh: Mesh to add UV layer to.
        :param name: Name for the UV layer.
        :return: Created UV layer.
        """
        ...

    @abstractmethod
    def set_uvs(
        self,
        mesh: Any,
        uvs: List[List[float]],
        face_materials: List[int],
    ) -> None:
        """
        Set UV coordinates and face material indices on a mesh.

        :param mesh: Mesh to modify.
        :param uvs: UV coordinates per vertex.
        :param face_materials: Material index for each face.
        """
        ...

    @abstractmethod
    def add_material(self, mesh: Any, material: Any) -> None:
        """
        Add a material to a mesh's material slots.

        :param mesh: Mesh to add material to.
        :param material: Material to add.
        """
        ...

    @abstractmethod
    def update_mesh(self, mesh: Any) -> None:
        """
        Update mesh data after modifications.

        :param mesh: Mesh to update.
        """
        ...


class ObjectBuilder(ABC):
    """Abstract interface for object creation and scene management."""

    @abstractmethod
    def create_object(self, name: str, data: Any) -> Any:
        """
        Create a new object with the given data.

        :param name: Name for the object.
        :param data: Object data (mesh, None for empty, etc.).
        :return: Created object.
        """
        ...

    @abstractmethod
    def link_to_scene(self, obj: Any) -> None:
        """
        Link an object to the current scene/collection.

        :param obj: Object to link.
        """
        ...

    @abstractmethod
    def set_parent(self, child: Any, parent: Any) -> None:
        """
        Set parent-child relationship between objects.

        :param child: Child object.
        :param parent: Parent object.
        """
        ...

    @abstractmethod
    def set_matrix_local(self, obj: Any, matrix: Any) -> None:
        """
        Set the local transformation matrix of an object.

        :param obj: Object to modify.
        :param matrix: 4x4 transformation matrix.
        """
        ...

    @abstractmethod
    def set_custom_property(self, obj: Any, key: str, value: Any) -> None:
        """
        Set a custom property on an object.

        :param obj: Object to modify.
        :param key: Property name.
        :param value: Property value.
        """
        ...

    @abstractmethod
    def set_display_properties(
        self,
        obj: Any,
        show_wire: bool = False,
        show_in_front: bool = False,
        show_bounds: bool = False,
    ) -> None:
        """
        Set display properties on an object.

        :param obj: Object to modify.
        :param show_wire: Show wireframe.
        :param show_in_front: Show object in front of others.
        :param show_bounds: Show bounding box.
        """
        ...

    @abstractmethod
    def create_vertex_group(self, obj: Any, name: str) -> Any:
        """
        Create a vertex group on an object.

        :param obj: Object to add vertex group to.
        :param name: Name for the vertex group.
        :return: Created vertex group.
        """
        ...

    @abstractmethod
    def add_vertex_weight(
        self,
        obj: Any,
        group_name: str,
        vertex_id: int,
        weight: float,
    ) -> None:
        """
        Add a vertex weight to a vertex group.

        :param obj: Object containing the vertex group.
        :param group_name: Name of the vertex group.
        :param vertex_id: Index of the vertex.
        :param weight: Weight value (0.0-1.0).
        """
        ...

    @abstractmethod
    def deselect_all(self) -> None:
        """Deselect all objects in the scene."""
        ...


class MaterialBuilder(ABC):
    """Abstract interface for material creation and shader setup."""

    @abstractmethod
    def create_material(self, name: str) -> Any:
        """
        Create a new material.

        :param name: Name for the material.
        :return: Created material.
        """
        ...

    @abstractmethod
    def enable_nodes(self, material: Any) -> Any:
        """
        Enable node-based shading on a material.

        :param material: Material to modify.
        :return: Node tree for the material.
        """
        ...

    @abstractmethod
    def clear_nodes(self, node_tree: Any) -> None:
        """
        Remove all nodes from a node tree.

        :param node_tree: Node tree to clear.
        """
        ...

    @abstractmethod
    def create_principled_bsdf(self, node_tree: Any) -> Any:
        """
        Create a Principled BSDF shader node.

        :param node_tree: Node tree to add node to.
        :return: Created BSDF node.
        """
        ...

    @abstractmethod
    def create_texture_node(
        self,
        node_tree: Any,
        texture: Any,
        name: str,
        is_data: bool = False,
    ) -> Any:
        """
        Create a texture image node.

        :param node_tree: Node tree to add node to.
        :param texture: Image texture to use.
        :param name: Name for the node.
        :param is_data: Whether this is non-color data (normal maps, etc.).
        :return: Created texture node.
        """
        ...

    @abstractmethod
    def create_normal_map_node(self, node_tree: Any) -> Any:
        """
        Create a normal map shader node.

        :param node_tree: Node tree to add node to.
        :return: Created normal map node.
        """
        ...

    @abstractmethod
    def create_transparent_node(self, node_tree: Any) -> Any:
        """
        Create a transparent BSDF shader node.

        :param node_tree: Node tree to add node to.
        :return: Created transparent node.
        """
        ...

    @abstractmethod
    def create_mix_shader_node(self, node_tree: Any) -> Any:
        """
        Create a mix shader node.

        :param node_tree: Node tree to add node to.
        :return: Created mix shader node.
        """
        ...

    @abstractmethod
    def create_output_node(self, node_tree: Any) -> Any:
        """
        Create a material output node.

        :param node_tree: Node tree to add node to.
        :return: Created output node.
        """
        ...

    @abstractmethod
    def create_rgb_curve_node(self, node_tree: Any) -> Any:
        """
        Create an RGB curve adjustment node.

        :param node_tree: Node tree to add node to.
        :return: Created curve node.
        """
        ...

    @abstractmethod
    def link_nodes(
        self,
        node_tree: Any,
        from_node: Any,
        from_output: int,
        to_node: Any,
        to_input: Any,
    ) -> None:
        """
        Link two shader nodes together.

        :param node_tree: Node tree containing the nodes.
        :param from_node: Source node.
        :param from_output: Output socket index on source node.
        :param to_node: Destination node.
        :param to_input: Input socket index or name on destination node.
        """
        ...

    @abstractmethod
    def set_node_location(self, node: Any, x: float, y: float) -> None:
        """
        Set the location of a node in the node editor.

        :param node: Node to position.
        :param x: X coordinate.
        :param y: Y coordinate.
        """
        ...


class ImageLoader(ABC):
    """Abstract interface for image loading."""

    @abstractmethod
    def load_image(self, filepath: str) -> Any:
        """
        Load an image from a file.

        :param filepath: Path to the image file.
        :return: Loaded image object.
        :raises FileNotFoundError: If the file does not exist.
        """
        ...


class SceneManager(ABC):
    """Abstract interface for scene-level operations."""

    @abstractmethod
    def set_render_engine(self, engine: str) -> None:
        """
        Set the render engine for the scene.

        :param engine: Render engine name (e.g., "CYCLES", "EEVEE").
        """
        ...

    @abstractmethod
    def create_collection(self, name: str) -> Any:
        """
        Create a new collection.

        :param name: Name for the collection.
        :return: Created collection.
        """
        ...

    @abstractmethod
    def link_collection_to_scene(self, collection: Any) -> None:
        """
        Link a collection to the scene.

        :param collection: Collection to link.
        """
        ...

    @abstractmethod
    def link_object_to_collection(self, obj: Any, collection: Any) -> None:
        """
        Link an object to a collection.

        :param obj: Object to link.
        :param collection: Target collection.
        """
        ...

    @abstractmethod
    def unlink_object_from_collections(self, obj: Any) -> None:
        """
        Unlink an object from all its current collections.

        :param obj: Object to unlink.
        """
        ...

    @abstractmethod
    def clear_scene(self) -> None:
        """
        Clear all objects, images, and custom properties from the scene.

        This is a destructive operation that removes everything.
        """
        ...

    @abstractmethod
    def load_sound(self, filepath: str) -> Any:
        """
        Load a sound file into Blender.

        :param filepath: Path to the sound file.
        :return: Loaded sound object.
        """
        ...

    @abstractmethod
    def pack_sound(self, sound: Any) -> None:
        """
        Pack sound data into the blend file.

        :param sound: Sound object to pack.
        """
        ...

    @abstractmethod
    def set_sound_name(self, sound: Any, name: str) -> None:
        """
        Set the name of a sound object.

        :param sound: Sound object to rename.
        :param name: New name for the sound.
        """
        ...


class MatrixFactory(ABC):
    """Abstract interface for matrix operations."""

    @abstractmethod
    def identity(self, size: int = 4) -> Any:
        """
        Create an identity matrix.

        :param size: Matrix size (default 4 for 4x4).
        :return: Identity matrix.
        """
        ...

    @abstractmethod
    def from_values(self, values: List[List[float]]) -> Any:
        """
        Create a matrix from a list of row values.

        :param values: List of rows, each row is a list of floats.
        :return: Matrix object.
        """
        ...


class AnimationBuilder(ABC):
    """Abstract interface for animation/action creation."""

    @abstractmethod
    def create_action(self, name: str) -> Any:
        """
        Create a new animation action.

        :param name: Name for the action.
        :return: Created action object.
        """
        ...

    @abstractmethod
    def create_fcurve(
        self,
        action: Any,
        data_path: str,
        index: int = 0,
    ) -> Any:
        """
        Create an FCurve (animation curve) in an action.

        :param action: Action to add the curve to.
        :param data_path: Data path for the property being animated
                         (e.g., 'pose.bones["Bone.001"].location').
        :param index: Array index for the property (0=X, 1=Y, 2=Z).
        :return: Created FCurve object.
        """
        ...

    @abstractmethod
    def add_keyframe(
        self,
        fcurve: Any,
        frame: float,
        value: float,
        interpolation: str = "BEZIER",
        handle_left: Optional[Tuple[float, float]] = None,
        handle_right: Optional[Tuple[float, float]] = None,
    ) -> Any:
        """
        Add a keyframe to an FCurve.

        :param fcurve: FCurve to add keyframe to.
        :param frame: Frame number for the keyframe.
        :param value: Value at this keyframe.
        :param interpolation: Interpolation type ('BEZIER', 'LINEAR', 'CONSTANT').
        :param handle_left: Left Bezier handle position (frame, value) or None.
        :param handle_right: Right Bezier handle position (frame, value) or None.
        :return: Created keyframe point.
        """
        ...

    @abstractmethod
    def set_action_frame_range(
        self,
        action: Any,
        frame_start: int,
        frame_end: int,
    ) -> None:
        """
        Set the frame range for an action.

        :param action: Action to modify.
        :param frame_start: First frame of the action.
        :param frame_end: Last frame of the action.
        """
        ...

    @abstractmethod
    def assign_action_to_object(self, obj: Any, action: Any) -> None:
        """
        Assign an action to an object's animation data.

        :param obj: Object (typically an armature) to assign action to.
        :param action: Action to assign.
        """
        ...
