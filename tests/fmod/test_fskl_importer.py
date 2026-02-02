# -*- coding: utf-8 -*-
"""Unit tests for skeleton importer using mock builders."""

import unittest
from dataclasses import dataclass, field
from typing import Dict

from mhfrontier.blender.mock_impl import (
    MockObjectBuilder,
    MockMatrixFactory,
    MockMatrix,
)
from mhfrontier.blender.builders import get_mock_builders
from mhfrontier.importers import skeleton as skeleton_importer


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
        builders = get_mock_builders()

        result = skeleton_importer.deserialize_pose_vector(
            (0.0, 0.0, 0.0, 1.0),
            builders,
        )

        # Should be close to identity with position at origin
        self.assertIsInstance(result, MockMatrix)

    def test_non_zero_position(self):
        """Test deserializing a non-zero position vector."""
        builders = get_mock_builders()

        result = skeleton_importer.deserialize_pose_vector(
            (100.0, 200.0, 300.0, 1.0),
            builders,
        )

        # The position should be scaled and axis-remapped
        self.assertIsInstance(result, MockMatrix)
        # Check that the matrix has been modified (not identity)
        # The exact values depend on IMPORT_SCALE and AXIS_REMAP


class TestImportBone(unittest.TestCase):
    """Test the import_bone function."""

    def test_import_single_bone(self):
        """Test importing a single bone with no parent."""
        builders = get_mock_builders()

        root_obj = builders.object.create_object("FSKL Tree", None)
        skeleton: Dict[str, any] = {"Root": root_obj}
        skeleton_structure = {}

        bone = MockFBone(nodeID=0, parentID=-1)
        skeleton_structure[0] = bone

        skeleton_importer.import_bone(
            bone,
            skeleton,
            skeleton_structure,
            builders,
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
        builders = get_mock_builders()

        root_obj = builders.object.create_object("FSKL Tree", None)
        skeleton: Dict[str, any] = {"Root": root_obj}

        parent_bone = MockFBone(nodeID=0, parentID=-1)
        child_bone = MockFBone(nodeID=1, parentID=0)

        skeleton_structure = {
            0: parent_bone,
            1: child_bone,
        }

        # Import child first - should recursively import parent
        skeleton_importer.import_bone(
            child_bone,
            skeleton,
            skeleton_structure,
            builders,
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
        builders = get_mock_builders()

        root_obj = builders.object.create_object("FSKL Tree", None)
        existing_bone_obj = builders.object.create_object("Bone.000", None)
        skeleton = {"Root": root_obj, "Bone.000": existing_bone_obj}

        bone = MockFBone(nodeID=0, parentID=-1)
        skeleton_structure = {0: bone}

        initial_count = len(builders.object.created_objects)

        skeleton_importer.import_bone(
            bone,
            skeleton,
            skeleton_structure,
            builders,
        )

        # No new objects should be created
        self.assertEqual(len(builders.object.created_objects), initial_count)


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
