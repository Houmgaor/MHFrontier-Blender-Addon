"""Basic testing for FMOD, loads files from ../models."""

import unittest

from mhfrontier.fmod import fmod
from tests import get_model_files


class TestFModFileLoading(unittest.TestCase):
    def test_load_fmod_file(self):
        """Test whether a .fmod file can be loaded."""
        files = get_model_files("tests/models", ".fmod")
        if not files:
            self.skipTest("No .fmod test files available in tests/models/")
        # Test the first available file
        fmod.load_fmod_file(files[0])


class TestGracefulErrorHandling(unittest.TestCase):
    """Tests for graceful error handling in FMOD loading.

    The graceful handling applies to block type validation after parsing,
    not to low-level binary parsing errors (which still raise exceptions
    for truly malformed data).
    """

    def test_returns_lists(self):
        """Test that valid files return list types."""
        files = get_model_files("tests/models", ".fmod")
        if not files:
            self.skipTest("No test model files available")
        selected_file = files[0]
        meshes, materials = fmod.load_fmod_file(selected_file)
        self.assertIsInstance(meshes, list)
        self.assertIsInstance(materials, list)

    def test_multiple_files_no_type_error(self):
        """Test that multiple valid files load without TypeError."""
        files = get_model_files("tests/models", ".fmod")
        if not files:
            self.skipTest("No test model files available")
        # Test all available files don't raise TypeError
        for filepath in files:
            try:
                meshes, materials = fmod.load_fmod_file(filepath)
                self.assertIsInstance(meshes, list)
                self.assertIsInstance(materials, list)
            except TypeError as e:
                self.fail(f"TypeError on {filepath}: {e}")


if __name__ == "__main__":
    unittest.main()
