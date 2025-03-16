"""
Quick way to zip the add-on part of the project.
"""

import os
import sys
import zipfile

if sys.version_info.major == 3 and sys.version_info.minor > 10:
    import tomllib
else:
    tomllib = None


def get_output_file_path():
    """Proposed output path for the addon, versioned is possible."""
    base_name = "mhfrontier_model_importer"
    extension = ".zip"
    if tomllib is None:
        return base_name + extension

    target_toml = "mhfrontier/blender_manifest.toml"
    with open(target_toml, "rb") as f:
        data = tomllib.load(f)
        base_name = data["id"]
        version = data["version"]
    return f"{base_name}-{version}{extension}"


def zip_folder(folder_path, output_path):
    """
    Zip any folder.
    """
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(folder_path):
            if not root.startswith("./mhfrontier"):
                continue
            for file in files:
                file_path = str(os.path.join(root, file))
                arcname = os.path.relpath(file_path, folder_path)
                zip_file.write(file_path, arcname)
    print(f"Created ZIP file at {output_path}")


# Usage example
if __name__ == "__main__":
    zip_folder(".", get_output_file_path())
