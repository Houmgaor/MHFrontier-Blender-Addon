# -*- coding: utf-8 -*-
"""
Concrete Blender implementations of abstract interfaces.

These classes wrap real Blender APIs and handle version compatibility.
"""

import array
from typing import Any, List, Tuple, Union

import bpy
import bmesh
from mathutils import Matrix

from .api import (
    MeshBuilder,
    ObjectBuilder,
    MaterialBuilder,
    ImageLoader,
    SceneManager,
    MatrixFactory,
    AnimationBuilder,
)


class BlenderMeshBuilder(MeshBuilder):
    """Concrete mesh builder using Blender APIs."""

    def create_mesh(
        self,
        name: str,
        vertices: List[Tuple[float, float, float]],
        faces: List[List[int]],
    ) -> bpy.types.Mesh:
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        return mesh

    def set_normals(self, mesh: bpy.types.Mesh, normals: List[List[float]]) -> None:
        mesh.update(calc_edges=True)

        cl_normals = array.array("f", [0.0] * (len(mesh.loops) * 3))
        mesh.loops.foreach_get("normal", cl_normals)
        mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))

        mesh.normals_split_custom_set_from_vertices(normals)

        # use_auto_smooth removed in Blender 4.1+
        if bpy.app.version < (4, 1):
            mesh.use_auto_smooth = True

        # Setting is True by default on Blender 2.8+
        if bpy.app.version < (2, 8):
            mesh.show_edge_sharp = True

    def create_uv_layer(self, mesh: bpy.types.Mesh, name: str) -> Any:
        if bpy.app.version >= (2, 8):
            return mesh.uv_layers.new(name=name)
        else:
            return mesh.uv_textures.new(name)

    def set_uvs(
        self,
        mesh: bpy.types.Mesh,
        uvs: List[List[float]],
        face_materials: List[int],
    ) -> None:
        mesh.update()

        blender_b_mesh = bmesh.new()
        blender_b_mesh.from_mesh(mesh)

        uv_layer = blender_b_mesh.loops.layers.uv["UV0"]
        blender_b_mesh.faces.ensure_lookup_table()
        for face in blender_b_mesh.faces:
            for loop in face.loops:
                loop[uv_layer].uv = uvs[loop.vert.index]
            face.material_index = face_materials[face.index]
        blender_b_mesh.to_mesh(mesh)
        mesh.update()

    def add_material(self, mesh: bpy.types.Mesh, material: bpy.types.Material) -> None:
        mesh.materials.append(material)

    def update_mesh(self, mesh: bpy.types.Mesh) -> None:
        mesh.update()

    def get_polygon_count(self, mesh: bpy.types.Mesh) -> int:
        return len(mesh.polygons)


class BlenderObjectBuilder(ObjectBuilder):
    """Concrete object builder using Blender APIs."""

    def create_object(self, name: str, data: Any) -> bpy.types.Object:
        return bpy.data.objects.new(name, data)

    def link_to_scene(self, obj: bpy.types.Object) -> None:
        if bpy.app.version >= (2, 8):
            bpy.context.collection.objects.link(obj)
        else:
            bpy.context.scene.objects.link(obj)

    def set_parent(self, child: bpy.types.Object, parent: bpy.types.Object) -> None:
        child.parent = parent

    def set_matrix_local(self, obj: bpy.types.Object, matrix: Matrix) -> None:
        obj.matrix_local = matrix

    def set_custom_property(
        self, obj: bpy.types.Object, key: str, value: Any
    ) -> None:
        obj[key] = value

    def set_display_properties(
        self,
        obj: bpy.types.Object,
        show_wire: bool = False,
        show_in_front: bool = False,
        show_bounds: bool = False,
    ) -> None:
        obj.show_wire = show_wire
        obj.show_bounds = show_bounds
        if bpy.app.version >= (2, 8):
            obj.show_in_front = show_in_front
        else:
            obj.show_x_ray = show_in_front

    def create_vertex_group(self, obj: bpy.types.Object, name: str) -> Any:
        return obj.vertex_groups.new(name=name)

    def add_vertex_weight(
        self,
        obj: bpy.types.Object,
        group_name: str,
        vertex_id: int,
        weight: float,
    ) -> None:
        if group_name not in obj.vertex_groups:
            obj.vertex_groups.new(name=group_name)
        obj.vertex_groups[group_name].add([vertex_id], weight, "ADD")

    def deselect_all(self) -> None:
        bpy.ops.object.select_all(action="DESELECT")


class BlenderMaterialBuilder(MaterialBuilder):
    """Concrete material builder using Blender APIs."""

    def create_material(self, name: str) -> bpy.types.Material:
        return bpy.data.materials.new(name=name)

    def enable_nodes(self, material: bpy.types.Material) -> Any:
        material.use_nodes = True
        return material.node_tree

    def clear_nodes(self, node_tree: bpy.types.NodeTree) -> None:
        nodes = node_tree.nodes
        for node in nodes:
            nodes.remove(node)

    def create_principled_bsdf(self, node_tree: bpy.types.NodeTree) -> Any:
        node = node_tree.nodes.new(type="ShaderNodeBsdfPrincipled")
        node.name = "Principled BSDF"
        return node

    def create_texture_node(
        self,
        node_tree: bpy.types.NodeTree,
        texture: bpy.types.Image,
        name: str,
        is_data: bool = False,
    ) -> Any:
        node = node_tree.nodes.new(type="ShaderNodeTexImage")
        if bpy.app.version >= (2, 8):
            node.image = texture
            node.image.colorspace_settings.is_data = is_data
        else:
            node.color_space = "NONE" if is_data else "COLOR"
            node.image = texture
        node.name = name
        return node

    def create_normal_map_node(self, node_tree: bpy.types.NodeTree) -> Any:
        node = node_tree.nodes.new(type="ShaderNodeNormalMap")
        node.name = "Normal Map"
        return node

    def create_transparent_node(self, node_tree: bpy.types.NodeTree) -> Any:
        return node_tree.nodes.new(type="ShaderNodeBsdfTransparent")

    def create_mix_shader_node(self, node_tree: bpy.types.NodeTree) -> Any:
        return node_tree.nodes.new(type="ShaderNodeMixShader")

    def create_output_node(self, node_tree: bpy.types.NodeTree) -> Any:
        return node_tree.nodes.new(type="ShaderNodeOutputMaterial")

    def create_rgb_curve_node(self, node_tree: bpy.types.NodeTree) -> Any:
        node = node_tree.nodes.new(type="ShaderNodeRGBCurve")
        node.name = "RGB Curve"
        return node

    def link_nodes(
        self,
        node_tree: bpy.types.NodeTree,
        from_node: Any,
        from_output: int,
        to_node: Any,
        to_input: Union[int, str],
    ) -> None:
        node_tree.links.new(from_node.outputs[from_output], to_node.inputs[to_input])

    def set_node_location(self, node: Any, x: float, y: float) -> None:
        node.location = (x, y)


class BlenderImageLoader(ImageLoader):
    """Concrete image loader using Blender APIs."""

    def load_image(self, filepath: str) -> bpy.types.Image:
        import os

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File {filepath} not found")
        return bpy.data.images.load(filepath)


class BlenderSceneManager(SceneManager):
    """Concrete scene manager using Blender APIs."""

    def set_render_engine(self, engine: str) -> None:
        bpy.context.scene.render.engine = engine

    def create_collection(self, name: str) -> bpy.types.Collection:
        return bpy.data.collections.new(name)

    def link_collection_to_scene(self, collection: bpy.types.Collection) -> None:
        bpy.context.scene.collection.children.link(collection)

    def link_object_to_collection(
        self, obj: bpy.types.Object, collection: bpy.types.Collection
    ) -> None:
        collection.objects.link(obj)

    def unlink_object_from_collections(self, obj: bpy.types.Object) -> None:
        for coll in obj.users_collection:
            coll.objects.unlink(obj)

    def clear_scene(self) -> None:
        # Delete scene custom properties
        for key in list(bpy.context.scene.keys()):
            del bpy.context.scene[key]
        # Select all and delete
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete()
        # Remove all images
        for img_name in list(bpy.data.images.keys()):
            bpy.data.images.remove(bpy.data.images[img_name])

    def load_sound(self, filepath: str) -> bpy.types.Sound:
        return bpy.data.sounds.load(filepath)

    def pack_sound(self, sound: bpy.types.Sound) -> None:
        sound.pack()

    def set_sound_name(self, sound: bpy.types.Sound, name: str) -> None:
        sound.name = name


class BlenderMatrixFactory(MatrixFactory):
    """Concrete matrix factory using mathutils."""

    def identity(self, size: int = 4) -> Matrix:
        return Matrix.Identity(size)

    def from_values(self, values: List[List[float]]) -> Matrix:
        return Matrix(values)


class BlenderAnimationBuilder(AnimationBuilder):
    """Concrete animation builder using Blender APIs."""

    def create_action(self, name: str) -> bpy.types.Action:
        return bpy.data.actions.new(name=name)

    def create_fcurve(
        self,
        action: bpy.types.Action,
        data_path: str,
        index: int = 0,
    ) -> bpy.types.FCurve:
        return action.fcurves.new(data_path=data_path, index=index)

    def add_keyframe(
        self,
        fcurve: bpy.types.FCurve,
        frame: float,
        value: float,
        interpolation: str = "BEZIER",
        handle_left: Tuple[float, float] = None,
        handle_right: Tuple[float, float] = None,
    ) -> bpy.types.Keyframe:
        kf = fcurve.keyframe_points.insert(frame, value)
        kf.interpolation = interpolation

        if handle_left is not None:
            kf.handle_left_type = "FREE"
            kf.handle_left = handle_left

        if handle_right is not None:
            kf.handle_right_type = "FREE"
            kf.handle_right = handle_right

        return kf

    def set_action_frame_range(
        self,
        action: bpy.types.Action,
        frame_start: int,
        frame_end: int,
    ) -> None:
        action.frame_start = frame_start
        action.frame_end = frame_end
        # Also set use_frame_range for Blender 3.0+
        if hasattr(action, "use_frame_range"):
            action.use_frame_range = True

    def assign_action_to_object(
        self,
        obj: bpy.types.Object,
        action: bpy.types.Action,
    ) -> None:
        if obj.animation_data is None:
            obj.animation_data_create()
        obj.animation_data.action = action


# Singleton instances for convenience
_mesh_builder: BlenderMeshBuilder | None = None
_object_builder: BlenderObjectBuilder | None = None
_material_builder: BlenderMaterialBuilder | None = None
_image_loader: BlenderImageLoader | None = None
_scene_manager: BlenderSceneManager | None = None
_matrix_factory: BlenderMatrixFactory | None = None
_animation_builder: BlenderAnimationBuilder | None = None


def get_mesh_builder() -> BlenderMeshBuilder:
    """Get the singleton mesh builder instance."""
    global _mesh_builder
    if _mesh_builder is None:
        _mesh_builder = BlenderMeshBuilder()
    return _mesh_builder


def get_object_builder() -> BlenderObjectBuilder:
    """Get the singleton object builder instance."""
    global _object_builder
    if _object_builder is None:
        _object_builder = BlenderObjectBuilder()
    return _object_builder


def get_material_builder() -> BlenderMaterialBuilder:
    """Get the singleton material builder instance."""
    global _material_builder
    if _material_builder is None:
        _material_builder = BlenderMaterialBuilder()
    return _material_builder


def get_image_loader() -> BlenderImageLoader:
    """Get the singleton image loader instance."""
    global _image_loader
    if _image_loader is None:
        _image_loader = BlenderImageLoader()
    return _image_loader


def get_scene_manager() -> BlenderSceneManager:
    """Get the singleton scene manager instance."""
    global _scene_manager
    if _scene_manager is None:
        _scene_manager = BlenderSceneManager()
    return _scene_manager


def get_matrix_factory() -> BlenderMatrixFactory:
    """Get the singleton matrix factory instance."""
    global _matrix_factory
    if _matrix_factory is None:
        _matrix_factory = BlenderMatrixFactory()
    return _matrix_factory


def get_animation_builder() -> BlenderAnimationBuilder:
    """Get the singleton animation builder instance."""
    global _animation_builder
    if _animation_builder is None:
        _animation_builder = BlenderAnimationBuilder()
    return _animation_builder
