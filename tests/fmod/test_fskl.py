"""Basic testing for FMOD, loads files from ../models."""

import os
import random
import unittest

from mhfrontier.fmod import fskl


def get_fskl_files(directory):
    """
    Recursively find all .fskl files in the given directory and its subdirectories.

    :param str directory: The path of the directory to search for .fmod
    :return list[str]: A list of file paths with the ".fmod" extension.
    """

    fmod_files = []

    # Iterate over each item in the directory tree
    for root, dirs, _files in os.walk(directory):
        # Search in subdirectories only
        for sub_directory in dirs:
            sub_path = os.path.join(root, sub_directory)
            for root2, _dirs, files in os.walk(sub_path):
                # For each file in the current directory
                for file in files:
                    # Check if the file has the ".fmod" extension
                    if file.endswith(".fskl"):
                        # Construct the full path of the file
                        fmod_file = os.path.join(root2, file)
                        # Add the file to the list
                        fmod_files.append(fmod_file)

    return fmod_files


class TestFSklFileLoading(unittest.TestCase):
    def test_load_fskl_file(self):
        """Test whether a .fskl file can be loaded."""
        files = get_fskl_files("tests/models")
        fskl.get_frontier_skeleton(files[random.randint(0, len(files) - 1)])


if __name__ == "__main__":
    unittest.main()
