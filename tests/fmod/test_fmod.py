"""Basic testing for FMOD, loads files from ../models."""

import random
import unittest

from mhfrontier.fmod import fmod
from tests import get_model_files


class TestFModFileLoading(unittest.TestCase):
    def test_load_fmod_file(self):
        """Test whether a .fmod file can be loaded."""
        files = get_model_files("tests/models", ".fmod")
        selected_file = files[random.randint(0, len(files) - 1)]
        fmod.load_fmod_file(selected_file)


if __name__ == "__main__":
    unittest.main()
