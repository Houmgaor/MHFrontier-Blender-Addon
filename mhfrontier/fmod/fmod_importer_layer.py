# -*- coding: utf-8 -*-
"""
Created on Sat Apr  6 02:55:27 2019

@author: AsteriskAmpersand
"""

import os
import array
from pathlib import Path

import bpy
import bmesh

from ..blender import blender_nodes_functions as bnf
from ..fmod.fmod import FModel


class FModImporter:
    """Prepare a Blender operator for 3D models import."""

    @staticmethod
    def execute(fmod_path, import_textures):
        bpy.context.scene.render.engine = "CYCLES"
        fmod = FModel(fmod_path)
        meshes = fmod.traditional_mesh_structure()
        materials = fmod.materials
        blender_materials = {}
        for ix, mesh in enumerate(meshes):
            FModImporter.import_mesh(ix, mesh, blender_materials)
        if import_textures:
            FModImporter.import_textures(materials, fmod_path, blender_materials)

    @staticmethod
    def import_mesh(index, mesh, blender_materials):
        """
        Import the mesh.

        :param int index: Mesh index
        :param dict mesh: fmesh with standard structure
        :param blender_materials: Materials associated with the mesh.
        """
        mesh_objects = []
        bpy.ops.object.select_all(action="DESELECT")

        # Geometry
        blender_mesh, blender_object = FModImporter.create_mesh(
            "FModMeshpart %03d" % (index,), mesh["vertices"], mesh["faces"]
        )
        # Normals Handling
        FModImporter.set_normals(mesh["normals"], blender_mesh)
        # UVs
        if bpy.app.version >= (2, 8):
            blender_object.data.uv_layers.new(name="UV0")
        FModImporter.create_texture_layer(
            blender_mesh,
            mesh["uvs"],
            mesh["materials"],
            mesh["faceMaterial"],
            blender_materials,
        )

        # Weights
        FModImporter.set_weights(mesh["weights"], mesh["boneRemap"], blender_object)
        blender_mesh.update()
        mesh_objects.append(blender_object)

    @staticmethod
    def create_mesh(name, vertices, faces):
        """
        Create a new mesh.

        :param str name: Name for the mesh
        :param vertices: Vertices to assign, the scale will be changed
        :type vertices: list[tuple[float, float, float]]
        :param list[tuple] faces: List of faces

        :return: Mesh and associated object.
        :rtype: tuple[bpy.types.Mesh, bpy.types.Object]
        """
        blender_mesh = bpy.data.meshes.new(name)
        # Change scale and axes
        transformed_vertices = [tuple() for _ in vertices]
        for i, vertex in enumerate(vertices):
            scaled = tuple(i / 100 for i in vertex)
            transformed_vertices[i] = scaled[0], scaled[2], scaled[1]
        blender_mesh.from_pydata(transformed_vertices, [], faces)
        blender_mesh.update()
        blender_object = bpy.data.objects.new(name, blender_mesh)
        # Blender 2.8+
        if bpy.app.version >= (2, 8):
            bpy.context.collection.objects.link(blender_object)
        else:
            # Blender <2.8
            bpy.context.scene.objects.link(blender_object)
        return blender_mesh, blender_object

    @staticmethod
    def create_texture_layer(
        blender_mesh, uv, material_list, face_materials, blender_materials
    ):
        """
        Assign a texture and UV map.

        :param bmesh blender_mesh: bmesh to use.
        :param list uv: Object UV maps
        :param list[int] material_list: List of materials indices
        :param list[int] face_materials: List of face material indices
        :param list[int] blender_materials: Blender materials already existing.
        """
        # Add the material to the list
        for material in material_list:
            if material not in blender_materials:
                material_name = "FrontierMaterial-%03d" % material
                blender_materials[material] = bpy.data.materials.new(name=material_name)
            blender_mesh.materials.append(blender_materials[material])
        if bpy.app.version < (2, 8):
            blender_mesh.uv_textures.new("UV0")
        blender_mesh.update()
        blender_b_mesh = bmesh.new()
        blender_b_mesh.from_mesh(blender_mesh)

        # Assign UVs
        uv_layer = blender_b_mesh.loops.layers.uv["UV0"]
        blender_b_mesh.faces.ensure_lookup_table()
        for face in blender_b_mesh.faces:
            for loop in face.loops:
                loop[uv_layer].uv = uv[loop.vert.index]
            face.material_index = face_materials[face.index]
        blender_b_mesh.to_mesh(blender_mesh)
        blender_mesh.update()

    @staticmethod
    def set_normals(normals, mesh_part):
        mesh_part.update(calc_edges=True)

        cl_normals = array.array("f", [0.0] * (len(mesh_part.loops) * 3))
        mesh_part.loops.foreach_get("normal", cl_normals)
        mesh_part.polygons.foreach_set("use_smooth", [True] * len(mesh_part.polygons))

        mesh_part.normals_split_custom_set_from_vertices(normals)

        # Disappears in Blender 4.1+
        if bpy.app.version < (4, 1):
            mesh_part.use_auto_smooth = True

        # Setting is True by default on Blender 2.8+
        if bpy.app.version < (2, 8):
            # Blender 2.7x
            mesh_part.show_edge_sharp = True

    @staticmethod
    def set_weights(weights, remap, mesh_obj):
        for meshBoneIx, group in weights.items():
            group_ix = remap[meshBoneIx]
            group_id = "%03d" % group_ix if isinstance(group_ix, int) else str(group_ix)
            group_name = "Bone.%s" % str(group_id)
            for vertex, weight in group:
                if group_name not in mesh_obj.vertex_groups:
                    mesh_obj.vertex_groups.new(name=group_name)  # blenderObject Maybe?
                mesh_obj.vertex_groups[group_name].add([vertex], weight, "ADD")

    @staticmethod
    def maximize_clipping():
        for a in bpy.context.screen.areas:
            if a.type == "VIEW_3D":
                for s in a.spaces:
                    if s.type == "VIEW_3D":
                        s.clip_end = 10**4

    @staticmethod
    def clear_scene():
        for key in list(bpy.context.scene.keys()):
            del bpy.context.scene[key]
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete()
        for i in bpy.data.images.keys():
            bpy.data.images.remove(bpy.data.images[i])
        return

    @staticmethod
    def import_textures(materials, path, blender_materials):
        def get_texture(local_index):
            filepath = FModImporter.search_textures(path, local_index)
            print(local_index)
            print(filepath)
            return FModImporter.fetch_texture(filepath)

        for ix, mat in blender_materials.items():
            # Setup
            mat.use_nodes = True
            node_tree = mat.node_tree
            nodes = node_tree.nodes
            for node in nodes:
                nodes.remove(node)
            # Preamble
            diffuse_ix = materials[ix].get_diffuse()
            normal_ix = materials[ix].get_normal()
            specular_ix = materials[ix].get_specular()
            # Construction
            setup = bnf.principled_setup(node_tree)
            next(setup)
            if diffuse_ix is not None:
                diffuse_node = bnf.diffuse_setup(node_tree, get_texture(diffuse_ix))
                setup.send(diffuse_node)
            else:
                setup.send(None)

            if normal_ix is not None:
                normal_node = bnf.normal_setup(node_tree, get_texture(normal_ix))
                setup.send(normal_node)
            else:
                setup.send(None)
            if specular_ix is not None:
                specular_node = bnf.specular_setup(node_tree, get_texture(specular_ix))
                setup.send(specular_node)
            else:
                setup.send(None)
            bnf.finish_setup(node_tree, next(setup))
            # Assign texture: FModImporter.assignTexture(mesh, textureData)

    @staticmethod
    def assign_texture(mesh_object, texture_data):
        for uvLayer in mesh_object.data.uv_textures:
            for uv_tex_face in uvLayer.data:
                uv_tex_face.image = texture_data
        mesh_object.data.update()

    @staticmethod
    def fetch_texture(filepath):
        if os.path.exists(filepath):
            return bpy.data.images.load(filepath)
        raise FileNotFoundError("File %s not found" % filepath)

    @staticmethod
    def search_textures(path, ix):
        """Search for textures in the folder."""
        model_path = Path(path)
        in_children = [
            f
            for f in model_path.parents[1].glob("**/*")
            if f.is_dir() and f > model_path.parent
        ]
        in_parents = [
            f
            for f in model_path.parents[1].glob("**/*")
            if f.is_dir() and f < model_path.parent
        ]
        candidates = [
            model_path.parent,
            *sorted(in_children),
            *sorted(in_parents),
        ]
        for directory in candidates:
            current = sorted(list(directory.rglob("*.png")))
            if current:
                current.sort()
                return current[min(ix, len(current))].resolve().as_posix()
