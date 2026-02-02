"""Basic testing for FSKL, loads files from ../models."""

import unittest

from mhfrontier.fmod import fskl
from tests import get_model_files


class TestFSklFileLoading(unittest.TestCase):
    def test_load_fskl_file(self):
        """Test whether a .fskl file can be loaded."""
        files = get_model_files("tests/models", ".fskl")
        if not files:
            self.skipTest("No .fskl test files available in tests/models/")
        # Test the first available file
        fskl.get_frontier_skeleton(files[0])


if __name__ == "__main__":
    unittest.main()
