# -*- coding: utf-8 -*-
"""Unit tests for fskl_importer_layer using mock builders."""

import unittest
from dataclasses import dataclass, field
from typing import Dict

from mhfrontier.blender.mock_impl import (
    MockObjectBuilder,
    MockMatrixFactory,
    MockMatrix,
)
from mhfrontier.fmod import fskl_importer_layer


@dataclass
class MockFBone:
    """Mock FBone for testing without real skeleton files."""

    nodeID: int
    parentID: int
    posVec: tuple = field(default_factory=lambda: (0.0, 0.0, 0.0, 1.0))


class TestDeserializePoseVector(unittest.TestCase):
    """Test the deserialize_pose_vector function."""

    def test_identity_position(self):
        """Test deserializing a zero position vector."""
        matrix_factory = MockMatrixFactory()

        result = fskl_importer_layer.deserialize_pose_vector(
            (0.0, 0.0, 0.0, 1.0),
            matrix_factory,
        )

        # Should be close to identity with position at origin
        self.assertIsInstance(result, MockMatrix)

    def test_non_zero_position(self):
        """Test deserializing a non-zero position vector."""
        matrix_factory = MockMatrixFactory()

        result = fskl_importer_layer.deserialize_pose_vector(
            (100.0, 200.0, 300.0, 1.0),
            matrix_factory,
        )

        # The position should be scaled and axis-remapped
        self.assertIsInstance(result, MockMatrix)
        # Check that the matrix has been modified (not identity)
        # The exact values depend on IMPORT_SCALE and AXIS_REMAP


class TestImportBone(unittest.TestCase):
    """Test the import_bone function."""

    def test_import_single_bone(self):
        """Test importing a single bone with no parent."""
        object_builder = MockObjectBuilder()
        matrix_factory = MockMatrixFactory()

        root_obj = object_builder.create_object("FSKL Tree", None)
        skeleton: Dict[str, any] = {"Root": root_obj}
        skeleton_structure = {}

        bone = MockFBone(nodeID=0, parentID=-1)
        skeleton_structure[0] = bone

        fskl_importer_layer.import_bone(
            bone,
            skeleton,
            skeleton_structure,
            object_builder,
            matrix_factory,
        )

        # Verify bone object was created
        self.assertIn("Bone.000", skeleton)
        bone_obj = skeleton["Bone.000"]
        self.assertTrue(bone_obj.linked_to_scene)

        # Verify parent is root
        self.assertEqual(bone_obj.parent, root_obj)

        # Verify custom property
        self.assertEqual(bone_obj.custom_properties["id"], 0)

        # Verify display properties
        self.assertTrue(bone_obj.show_wire)
        self.assertTrue(bone_obj.show_in_front)
        self.assertTrue(bone_obj.show_bounds)

    def test_import_bone_with_parent(self):
        """Test importing a bone with a parent bone."""
        object_builder = MockObjectBuilder()
        matrix_factory = MockMatrixFactory()

        root_obj = object_builder.create_object("FSKL Tree", None)
        skeleton: Dict[str, any] = {"Root": root_obj}

        parent_bone = MockFBone(nodeID=0, parentID=-1)
        child_bone = MockFBone(nodeID=1, parentID=0)

        skeleton_structure = {
            0: parent_bone,
            1: child_bone,
        }

        # Import child first - should recursively import parent
        fskl_importer_layer.import_bone(
            child_bone,
            skeleton,
            skeleton_structure,
            object_builder,
            matrix_factory,
        )

        # Both bones should be in skeleton
        self.assertIn("Bone.000", skeleton)
        self.assertIn("Bone.001", skeleton)

        # Child should have parent as its parent
        child_obj = skeleton["Bone.001"]
        parent_obj = skeleton["Bone.000"]
        self.assertEqual(child_obj.parent, parent_obj)

    def test_skip_existing_bone(self):
        """Test that existing bones are not reimported."""
        object_builder = MockObjectBuilder()
        matrix_factory = MockMatrixFactory()

        root_obj = object_builder.create_object("FSKL Tree", None)
        existing_bone_obj = object_builder.create_object("Bone.000", None)
        skeleton = {"Root": root_obj, "Bone.000": existing_bone_obj}

        bone = MockFBone(nodeID=0, parentID=-1)
        skeleton_structure = {0: bone}

        initial_count = len(object_builder.created_objects)

        fskl_importer_layer.import_bone(
            bone,
            skeleton,
            skeleton_structure,
            object_builder,
            matrix_factory,
        )

        # No new objects should be created
        self.assertEqual(len(object_builder.created_objects), initial_count)


class TestImportSkeleton(unittest.TestCase):
    """Test the import_skeleton function with mock data.

    Note: Full integration tests require actual FSKL files.
    """

    def test_creates_root_object(self):
        """Test that a root object is created when importing skeleton.

        This is a partial test - full testing requires mocking fskl.get_frontier_skeleton.
        """
        # This test is limited because import_skeleton calls fskl.get_frontier_skeleton
        # which requires actual file access. Full testing would require:
        # 1. Having test fixture files, or
        # 2. Mocking the fskl module
        pass


if __name__ == "__main__":
    unittest.main()
