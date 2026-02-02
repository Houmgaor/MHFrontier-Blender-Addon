"""Test utilities for MHFrontier addon tests."""

import os


def get_model_files(directory, extension):
    """
    Recursively find all files with a given extension in subdirectories.

    :param str directory: The path of the directory to search.
    :param str extension: File extension to match (e.g., ".fmod", ".fskl").
    :return: A list of file paths matching the extension.
    :rtype: list[str]
    """
    model_files = []

    for root, dirs, _files in os.walk(directory):
        for sub_directory in dirs:
            sub_path = os.path.join(root, sub_directory)
            for root2, _dirs, files in os.walk(sub_path):
                for file in files:
                    if file.endswith(extension):
                        model_files.append(os.path.join(root2, file))

    return model_files
