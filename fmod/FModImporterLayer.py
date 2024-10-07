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

from ..blender.BlenderNodesFunctions import (
    principled_setup,
    diffuse_setup,
    normal_setup,
    specular_setup,
    finish_setup
)
from ..fmod.FMod import FModel


class FModImporter:
    @staticmethod
    def execute(fmodPath, import_textures):
        bpy.context.scene.render.engine = 'CYCLES'
        fmod = FModel(fmodPath)
        meshes = fmod.traditional_mesh_structure()
        materials = fmod.Materials
        blender_materials = {}
        for ix, mesh in enumerate(meshes):
            FModImporter.importMesh(ix, mesh, blender_materials)
        if import_textures:
            FModImporter.importTextures(materials, fmodPath, blender_materials)

    @staticmethod
    def importMesh(ix, mesh, bmats):
        mesh_objects = []
        bpy.ops.object.select_all(action='DESELECT')

        # Geometry
        blender_mesh, blender_object = FModImporter.create_mesh("FModMeshpart %03d" % (ix,), mesh)
        # Normals Handling
        FModImporter.setNormals(mesh["normals"], blender_mesh)
        # UVs
        if bpy.app.version >= (2, 8):
            # Blender 2.8+
            FModImporter.createTextureLayerFromObj(
                blender_object, blender_mesh, mesh["uvs"], mesh["materials"], mesh["faceMaterial"], bmats
            )
        else:
            # Blender <2.8
            FModImporter.createTextureLayer(
                blender_mesh, mesh["uvs"], mesh["materials"], mesh["faceMaterial"], bmats
            )

        # Weights
        FModImporter.setWeights(mesh["weights"], mesh["boneRemap"], blender_object)
        blender_mesh.update()
        mesh_objects.append(blender_object)

    @staticmethod
    def create_mesh(name, meshpart):
        blender_mesh = bpy.data.meshes.new("%s" % (name,))
        blender_mesh.from_pydata(meshpart["vertices"], [], meshpart["faces"])
        blender_mesh.update()
        blender_object = bpy.data.objects.new("%s" % (name,), blender_mesh)
        # Blender 2.8+
        if bpy.app.version >= (2, 8):
            bpy.context.collection.objects.link(blender_object)
        else:
            # Blender <2.8
            bpy.context.scene.objects.link(blender_object)
        return blender_mesh, blender_object

    @staticmethod
    def createTextureLayerFromObj(
        blenderObj, blenderMesh, uv, materialList, faceMaterials, bmats
    ):
        """General function to create texture, for Blender 2.8+."""
        for material in materialList:
            matname = "FrontierMaterial-%03d" % material
            if material not in bmats:
                mat = bpy.data.materials.new(name=matname)
                bmats[material] = mat
            mat = bmats[material]
            blenderMesh.materials.append(mat)
        blenderObj.data.uv_layers.new(name="UV0")
        blenderMesh.update()
        blender_b_mesh = bmesh.new()
        blender_b_mesh.from_mesh(blenderMesh)
        uv_layer = blender_b_mesh.loops.layers.UV["UV0"]
        blender_b_mesh.faces.ensure_lookup_table()
        for face in blender_b_mesh.faces:
            for loop in face.loops:
                loop[uv_layer].UV = uv[loop.vert.index]
            face.material_index = faceMaterials[face.index]
        blender_b_mesh.to_mesh(blenderMesh)
        blenderMesh.update()
        return

    @staticmethod
    def createTextureLayer(blenderMesh, uv, materialList, faceMaterials, bmats):
        for material in materialList:
            material_name = "FrontierMaterial-%03d" % material
            if material not in bmats:
                mat = bpy.data.materials.new(name=material_name)
                bmats[material] = mat
            mat = bmats[material]
            blenderMesh.materials.append(mat)
        blenderMesh.uv_textures.new("UV0")
        blenderMesh.update()
        blender_b_mesh = bmesh.new()
        blender_b_mesh.from_mesh(blenderMesh)
        uv_layer = blender_b_mesh.loops.layers.UV["UV0"]
        blender_b_mesh.faces.ensure_lookup_table()
        for face in blender_b_mesh.faces:
            for loop in face.loops:
                loop[uv_layer].UV = uv[loop.vert.index]
            face.material_index = faceMaterials[face.index]
        blender_b_mesh.to_mesh(blenderMesh)
        blenderMesh.update()

    @staticmethod
    def setNormals(normals, meshpart):
        meshpart.update(calc_edges=True)

        cl_normals = array.array('f', [0.0] * (len(meshpart.loops) * 3))
        meshpart.loops.foreach_get("normal", cl_normals)
        meshpart.polygons.foreach_set("use_smooth", [True] * len(meshpart.polygons))

        meshpart.normals_split_custom_set_from_vertices(normals)

        # Disappears in Blender 4.1+
        if bpy.app.version < (4, 1):
            meshpart.use_auto_smooth = True

        # Setting is True by default on Blender 2.8+
        if bpy.app.version < (2, 8):
            # Blender 2.7x
            meshpart.show_edge_sharp = True

    @staticmethod
    def setWeights(weights, remap, meshObj):
        for meshBoneIx, group in weights.items():
            groupIx = remap[meshBoneIx]
            groupId = "%03d" % groupIx if isinstance(groupIx, int) else str(groupIx)
            groupName = "Bone.%s" % str(groupId)
            for vertex, weight in group:
                if groupName not in meshObj.vertex_groups:
                    meshObj.vertex_groups.new(name=groupName)  #blenderObject Maybe?
                meshObj.vertex_groups[groupName].add([vertex], weight, 'ADD')

    @staticmethod
    def maximizeClipping():
        for a in bpy.context.screen.areas:
            if a.type == 'VIEW_3D':
                for s in a.spaces:
                    if s.type == 'VIEW_3D':
                        s.clip_end = 10 ** 4

    @staticmethod
    def clearScene():
        for key in list(bpy.context.scene.keys()):
            del bpy.context.scene[key]
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete()
        for i in bpy.data.images.keys():
            bpy.data.images.remove(bpy.data.images[i])
        return

    @staticmethod
    def importTextures(materials, path, bmats):
        def getTexture(ix):
            filepath = FModImporter.search_textures(path, ix)
            print(ix)
            print(filepath)
            return FModImporter.fetchTexture(filepath)

        for ix, mat in bmats.items():
            # Setup
            mat.use_nodes = True
            nodeTree = mat.node_tree
            nodes = nodeTree.nodes
            for node in nodes:
                nodes.remove(node)
            # Preamble
            #ix = int(mat.name.split("-")[1])
            diffuseIx = materials[ix].get_diffuse()
            normalIx = materials[ix].get_normal()
            specularIx = materials[ix].get_specular()
            # Construction        
            setup = principled_setup(nodeTree)
            next(setup)
            if diffuseIx is not None:
                diffuseNode = diffuse_setup(nodeTree, getTexture(diffuseIx))
                setup.send(diffuseNode)
            else:
                setup.send(None)
            #setup.send(None)
            if normalIx is not None:
                normalNode = normal_setup(nodeTree, getTexture(normalIx))
                setup.send(normalNode)
            else:
                setup.send(None)
            if specularIx is not None:
                specularNode = specular_setup(nodeTree, getTexture(specularIx))
                setup.send(specularNode)
            else:
                setup.send(None)
            finish_setup(nodeTree, next(setup))
            #FModImporter.assignTexture(mesh, textureData)
            #except:
            #    pass            

    @staticmethod
    def assignTexture(meshObject, textureData):
        for uvLayer in meshObject.data.uv_textures:
            for uv_tex_face in uvLayer.data:
                uv_tex_face.image = textureData
        meshObject.data.update()

    @staticmethod
    def fetchTexture(filepath):
        if os.path.exists(filepath):
            return bpy.data.images.load(filepath)
        else:
            raise FileNotFoundError("File %s not found" % filepath)

    @staticmethod
    def search_textures(path, ix):
        model_path = Path(path)
        candidates = [
            model_path.parent,
            *sorted([f for f in model_path.parents[1].glob('**/*') if f.is_dir() and f > model_path.parent]),
            *sorted([f for f in model_path.parents[1].glob('**/*') if f.is_dir() and f < model_path.parent])
        ]
        for directory in candidates:
            current = sorted(list(directory.rglob("*.png")))
            if current:
                current.sort()
                return current[min(ix, len(current))].resolve().as_posix()
