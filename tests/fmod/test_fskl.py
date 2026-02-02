"""Basic testing for FSKL, loads files from ../models."""

import random
import unittest

from mhfrontier.fmod import fskl
from tests import get_model_files


class TestFSklFileLoading(unittest.TestCase):
    def test_load_fskl_file(self):
        """Test whether a .fskl file can be loaded."""
        files = get_model_files("tests/models", ".fskl")
        selected_file = files[random.randint(0, len(files) - 1)]
        fskl.get_frontier_skeleton(selected_file)


if __name__ == "__main__":
    unittest.main()
