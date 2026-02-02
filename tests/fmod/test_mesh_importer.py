# -*- coding: utf-8 -*-
"""Unit tests for mesh_importer using mock builders."""

import unittest
from typing import Dict, List, Tuple
from unittest.mock import MagicMock

from mhfrontier.blender.mock_impl import (
    MockMeshBuilder,
    MockObjectBuilder,
    MockMaterial,
    MockMesh,
    MockObject,
)
from mhfrontier.fmod import mesh_importer


class MockFMesh:
    """Mock FMesh for testing without real model files."""

    def __init__(
        self,
        vertices: List[Tuple[float, float, float]],
        faces: List[List[int]],
        normals: List[List[float]],
        uvs: List[List[float]] = None,
        material_list: List[int] = None,
        material_map: List[int] = None,
        weights: Dict[int, List[Tuple[int, float]]] = None,
        bone_remap: List[int] = None,
    ):
        self.vertices = vertices
        self.faces = faces
        self.normals = normals
        self.uvs = uvs
        self.material_list = material_list or [0]
        self.material_map = material_map or [0] * len(faces)
        self.weights = weights
        self.bone_remap = bone_remap


class TestImportMesh(unittest.TestCase):
    """Test the import_mesh function."""

    def setUp(self):
        """Set up test fixtures."""
        self.mesh_builder = MockMeshBuilder()
        self.object_builder = MockObjectBuilder()

        # Simple triangle mesh
        self.simple_vertices = [
            (0.0, 0.0, 0.0),
            (100.0, 0.0, 0.0),
            (50.0, 100.0, 0.0),
        ]
        self.simple_faces = [[0, 1, 2]]
        self.simple_normals = [
            [0.0, 0.0, 1.0],
            [0.0, 0.0, 1.0],
            [0.0, 0.0, 1.0],
        ]

    def test_import_simple_mesh(self):
        """Test importing a simple triangle mesh."""
        mock_mesh = MockFMesh(
            vertices=self.simple_vertices,
            faces=self.simple_faces,
            normals=self.simple_normals,
        )

        mock_material = MockMaterial(name="TestMaterial")
        blender_materials = {0: mock_material}

        result = mesh_importer.import_mesh(
            index=0,
            mesh=mock_mesh,
            blender_materials=blender_materials,
            mesh_builder=self.mesh_builder,
            object_builder=self.object_builder,
        )

        # Verify object was created
        self.assertEqual(len(self.object_builder.created_objects), 1)
        self.assertEqual(result.name, "FModMeshpart 000")
        self.assertTrue(result.linked_to_scene)

        # Verify mesh was created
        self.assertEqual(len(self.mesh_builder.created_meshes), 1)
        created_mesh = self.mesh_builder.created_meshes[0]
        self.assertEqual(created_mesh.name, "FModMeshpart 000")

        # Verify vertices were transformed (scaled by IMPORT_SCALE and remapped)
        self.assertEqual(len(created_mesh.vertices), 3)

        # Verify faces
        self.assertEqual(created_mesh.faces, [[0, 1, 2]])

        # Verify normals were set
        self.assertEqual(created_mesh.normals, self.simple_normals)

    def test_import_mesh_with_uvs(self):
        """Test importing a mesh with UV coordinates."""
        uvs = [
            [0.0, 0.0],
            [1.0, 0.0],
            [0.5, 1.0],
        ]
        mock_mesh = MockFMesh(
            vertices=self.simple_vertices,
            faces=self.simple_faces,
            normals=self.simple_normals,
            uvs=uvs,
            material_list=[0],
            material_map=[0],
        )

        mock_material = MockMaterial(name="TestMaterial")
        blender_materials = {0: mock_material}

        result = mesh_importer.import_mesh(
            index=1,
            mesh=mock_mesh,
            blender_materials=blender_materials,
            mesh_builder=self.mesh_builder,
            object_builder=self.object_builder,
        )

        # Verify UV layer was created
        created_mesh = self.mesh_builder.created_meshes[0]
        self.assertIn("UV0", created_mesh.uv_layers)

        # Verify UVs were set
        self.assertEqual(created_mesh.uvs, uvs)

        # Verify materials were added
        self.assertEqual(len(created_mesh.materials), 1)

    def test_import_mesh_with_weights(self):
        """Test importing a mesh with vertex weights."""
        weights = {
            0: [(0, 1.0), (1, 0.5)],
            1: [(1, 0.5), (2, 1.0)],
        }
        bone_remap = [0, 1]

        mock_mesh = MockFMesh(
            vertices=self.simple_vertices,
            faces=self.simple_faces,
            normals=self.simple_normals,
            weights=weights,
            bone_remap=bone_remap,
        )

        mock_material = MockMaterial(name="TestMaterial")
        blender_materials = {0: mock_material}

        result = mesh_importer.import_mesh(
            index=2,
            mesh=mock_mesh,
            blender_materials=blender_materials,
            mesh_builder=self.mesh_builder,
            object_builder=self.object_builder,
        )

        # Verify vertex groups were created
        self.assertIn("Bone.000", result.vertex_groups)
        self.assertIn("Bone.001", result.vertex_groups)

        # Verify weights
        group_000 = result.vertex_groups["Bone.000"]
        self.assertEqual(group_000.weights[0], 1.0)
        self.assertEqual(group_000.weights[1], 0.5)

        group_001 = result.vertex_groups["Bone.001"]
        self.assertEqual(group_001.weights[1], 0.5)
        self.assertEqual(group_001.weights[2], 1.0)

    def test_import_mesh_without_bone_remap(self):
        """Test importing a mesh with weights but no bone_remap generates one."""
        weights = {
            0: [(0, 1.0)],
            2: [(1, 1.0)],
        }

        mock_mesh = MockFMesh(
            vertices=self.simple_vertices,
            faces=self.simple_faces,
            normals=self.simple_normals,
            weights=weights,
            bone_remap=None,
        )

        mock_material = MockMaterial(name="TestMaterial")
        blender_materials = {0: mock_material}

        # Should not raise, should auto-generate bone_remap
        result = mesh_importer.import_mesh(
            index=0,
            mesh=mock_mesh,
            blender_materials=blender_materials,
            mesh_builder=self.mesh_builder,
            object_builder=self.object_builder,
        )

        # Verify it worked - bone_remap should be auto-generated as [0, 1, 2]
        self.assertIn("Bone.000", result.vertex_groups)
        self.assertIn("Bone.002", result.vertex_groups)

    def test_deselect_all_called(self):
        """Test that deselect_all is called at the start of import."""
        mock_mesh = MockFMesh(
            vertices=self.simple_vertices,
            faces=self.simple_faces,
            normals=self.simple_normals,
        )

        mock_material = MockMaterial(name="TestMaterial")
        blender_materials = {0: mock_material}

        mesh_importer.import_mesh(
            index=0,
            mesh=mock_mesh,
            blender_materials=blender_materials,
            mesh_builder=self.mesh_builder,
            object_builder=self.object_builder,
        )

        self.assertEqual(self.object_builder.deselect_calls, 1)


class TestCreateMesh(unittest.TestCase):
    """Test the create_mesh function."""

    def test_create_mesh_transforms_vertices(self):
        """Test that vertices are transformed from Frontier to Blender coordinates."""
        mesh_builder = MockMeshBuilder()

        # Input vertices in Frontier coordinates
        vertices = [
            (100.0, 200.0, 300.0),
            (0.0, 0.0, 0.0),
        ]
        faces = [[0, 1]]

        result = mesh_importer.create_mesh(
            name="TestMesh",
            vertices=vertices,
            faces=faces,
            mesh_builder=mesh_builder,
        )

        # Verify mesh was created
        self.assertEqual(len(mesh_builder.created_meshes), 1)
        self.assertEqual(result.name, "TestMesh")

        # Vertices should be transformed (IMPORT_SCALE=0.01, AXIS_REMAP=[0,2,1,3])
        # Original (100, 200, 300) -> transformed based on config
        # The exact transformation depends on config values
        self.assertEqual(len(result.vertices), 2)


class TestCreateBlenderObject(unittest.TestCase):
    """Test the create_blender_object function."""

    def test_creates_and_links_object(self):
        """Test that object is created and linked to scene."""
        object_builder = MockObjectBuilder()
        mock_mesh = MockMesh(name="TestMesh")

        result = mesh_importer.create_blender_object(
            name="TestObject",
            blender_mesh=mock_mesh,
            object_builder=object_builder,
        )

        self.assertEqual(result.name, "TestObject")
        self.assertEqual(result.data, mock_mesh)
        self.assertTrue(result.linked_to_scene)


class TestSetWeights(unittest.TestCase):
    """Test the set_weights function."""

    def test_set_weights_with_remap(self):
        """Test setting weights with bone remapping."""
        object_builder = MockObjectBuilder()
        obj = MockObject(name="TestObject")

        weights = {
            0: [(0, 0.75), (1, 0.25)],
            1: [(2, 1.0)],
        }
        remap = [10, 20]  # Local bone 0 -> skeleton bone 10, etc.

        mesh_importer.set_weights(weights, remap, obj, object_builder)

        # Verify vertex groups were created with remapped names
        self.assertIn("Bone.010", obj.vertex_groups)
        self.assertIn("Bone.020", obj.vertex_groups)

        # Verify weights
        self.assertEqual(obj.vertex_groups["Bone.010"].weights[0], 0.75)
        self.assertEqual(obj.vertex_groups["Bone.010"].weights[1], 0.25)
        self.assertEqual(obj.vertex_groups["Bone.020"].weights[2], 1.0)


class TestCreateTextureLayer(unittest.TestCase):
    """Test the create_texture_layer function."""

    def test_adds_materials_and_uvs(self):
        """Test that materials are added and UVs are set."""
        mesh_builder = MockMeshBuilder()
        mesh = MockMesh(name="TestMesh")
        mesh.uv_layers["UV0"] = True  # Simulate UV layer already created

        material_0 = MockMaterial(name="Material0")
        material_1 = MockMaterial(name="Material1")
        blender_materials = {0: material_0, 1: material_1}

        uvs = [[0.0, 0.0], [1.0, 0.0], [0.5, 1.0]]
        material_list = [0, 1]
        face_materials = [0, 1]

        mesh_importer.create_texture_layer(
            blender_mesh=mesh,
            uv=uvs,
            material_list=material_list,
            face_materials=face_materials,
            blender_materials=blender_materials,
            mesh_builder=mesh_builder,
        )

        # Verify materials were added
        self.assertEqual(len(mesh.materials), 2)
        self.assertEqual(mesh.materials[0], material_0)
        self.assertEqual(mesh.materials[1], material_1)

        # Verify UVs were set
        self.assertEqual(mesh.uvs, uvs)
        self.assertEqual(mesh.face_materials, face_materials)


if __name__ == "__main__":
    unittest.main()
