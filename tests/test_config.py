"""Tests for config module."""

import unittest

from mhfrontier.config import (
    IMPORT_SCALE,
    AXIS_REMAP,
    AXIS_REMAP_3D,
    transform_vertex,
    transform_vector4,
)


class TestConfigConstants(unittest.TestCase):
    """Test configuration constants."""

    def test_import_scale_value(self):
        """Test import scale is 1/100."""
        self.assertEqual(IMPORT_SCALE, 0.01)
        self.assertAlmostEqual(IMPORT_SCALE, 1 / 100)

    def test_axis_remap_swaps_y_z(self):
        """Test axis remap swaps Y and Z (indices 1 and 2)."""
        self.assertEqual(AXIS_REMAP, (0, 2, 1, 3))
        # X stays at 0, Y moves to Z position, Z moves to Y position, W stays
        self.assertEqual(AXIS_REMAP[0], 0)  # X -> X
        self.assertEqual(AXIS_REMAP[1], 2)  # Y -> Z (Blender Y comes from Frontier Z)
        self.assertEqual(AXIS_REMAP[2], 1)  # Z -> Y (Blender Z comes from Frontier Y)
        self.assertEqual(AXIS_REMAP[3], 3)  # W -> W

    def test_axis_remap_3d(self):
        """Test 3D axis remap is consistent with 4D."""
        self.assertEqual(AXIS_REMAP_3D, (0, 2, 1))
        self.assertEqual(AXIS_REMAP_3D, AXIS_REMAP[:3])


class TestTransformVertex(unittest.TestCase):
    """Test vertex transformation function."""

    def test_transform_scales_correctly(self):
        """Test that transform applies scale factor."""
        vertex = (100.0, 200.0, 300.0)
        result = transform_vertex(vertex)
        # Expected: scaled by 0.01, Y/Z swapped
        self.assertAlmostEqual(result[0], 1.0)   # X: 100 * 0.01
        self.assertAlmostEqual(result[1], 3.0)   # Y: 300 * 0.01 (from Z)
        self.assertAlmostEqual(result[2], 2.0)   # Z: 200 * 0.01 (from Y)

    def test_transform_swaps_y_z(self):
        """Test that transform swaps Y and Z axes."""
        vertex = (1.0, 2.0, 3.0)
        result = transform_vertex(vertex, scale=1.0)  # No scaling
        self.assertEqual(result[0], 1.0)  # X unchanged
        self.assertEqual(result[1], 3.0)  # Blender Y = Frontier Z
        self.assertEqual(result[2], 2.0)  # Blender Z = Frontier Y

    def test_transform_custom_scale(self):
        """Test transform with custom scale factor."""
        vertex = (10.0, 20.0, 30.0)
        result = transform_vertex(vertex, scale=0.1)
        self.assertAlmostEqual(result[0], 1.0)
        self.assertAlmostEqual(result[1], 3.0)
        self.assertAlmostEqual(result[2], 2.0)

    def test_transform_zero_vertex(self):
        """Test transform with zero vertex."""
        vertex = (0.0, 0.0, 0.0)
        result = transform_vertex(vertex)
        self.assertEqual(result, (0.0, 0.0, 0.0))

    def test_transform_negative_values(self):
        """Test transform with negative values."""
        vertex = (-100.0, -200.0, -300.0)
        result = transform_vertex(vertex)
        self.assertAlmostEqual(result[0], -1.0)
        self.assertAlmostEqual(result[1], -3.0)
        self.assertAlmostEqual(result[2], -2.0)


class TestTransformVector4(unittest.TestCase):
    """Test 4D vector transformation function."""

    def test_transform_4d_scales_correctly(self):
        """Test that 4D transform applies scale factor."""
        vec = (100.0, 200.0, 300.0, 400.0)
        result = transform_vector4(vec)
        self.assertAlmostEqual(result[0], 1.0)   # X
        self.assertAlmostEqual(result[1], 3.0)   # from Z
        self.assertAlmostEqual(result[2], 2.0)   # from Y
        self.assertAlmostEqual(result[3], 4.0)   # W

    def test_transform_4d_remap(self):
        """Test 4D axis remapping without scale."""
        vec = (1.0, 2.0, 3.0, 4.0)
        result = transform_vector4(vec, scale=1.0)
        self.assertEqual(result[0], 1.0)  # X -> X
        self.assertEqual(result[1], 3.0)  # Y <- Z
        self.assertEqual(result[2], 2.0)  # Z <- Y
        self.assertEqual(result[3], 4.0)  # W -> W


if __name__ == "__main__":
    unittest.main()
