"""
Quick way to zip the add-on part of the project.
"""

import zipfile
import os


def zip_folder(folder_path, output_path):
    """
    Zip any folder.
    """
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(folder_path):
            if not root.startswith("./mhfrontier"):
                continue
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, folder_path)
                zip_file.write(file_path, arcname)
    print(f"Created ZIP file at {output_path}")


# Usage example
zip_folder(".", "MHFrontier-Blender-Addon.zip")
