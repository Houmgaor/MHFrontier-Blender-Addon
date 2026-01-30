# -*- coding: utf-8 -*-
"""
Importer operator for MHF Stage/Map files.

Supports both packed .pac containers and unpacked directories.
"""

import os
from pathlib import Path

import bpy
import bpy_extras

from ..fmod import stage_importer_layer


class ImportStage(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
    """Import a Monster Hunter Frontier Stage/Map file."""

    bl_idname = "custom_import.import_mhf_stage"
    bl_label = "Load MHF Stage file"
    bl_options = {"REGISTER", "PRESET", "UNDO"}

    # ImportHelper mixin class uses this
    filename_ext = ".pac"
    filter_glob: bpy.props.StringProperty(
        default="*.pac;*.fmod;*.jkr",
        options={"HIDDEN"},
        maxlen=255,
    )

    clear_scene: bpy.props.BoolProperty(
        name="Clear scene before import",
        description="Clears all contents before importing",
        default=True,
    )

    import_textures: bpy.props.BoolProperty(
        name="Import Textures",
        description="Import textures from the stage container or nearby files",
        default=True,
    )

    create_collection: bpy.props.BoolProperty(
        name="Create Collection",
        description="Create a new collection for the imported stage",
        default=True,
    )

    # Allow selecting directories for unpacked stages
    use_filter_folder: bpy.props.BoolProperty(
        default=True,
        options={"HIDDEN"},
    )

    def execute(self, context):
        """Import the stage to the scene."""
        try:
            bpy.ops.object.mode_set(mode="OBJECT")
        except RuntimeError as error:
            print(error)

        bpy.ops.object.select_all(action="DESELECT")

        filepath = Path(self.properties.filepath)

        # Check if user selected a directory or a file
        if filepath.is_dir():
            stage_path = filepath
        elif filepath.is_file():
            stage_path = filepath
        else:
            # Could be selecting a file inside a directory - use parent
            if filepath.parent.is_dir():
                stage_path = filepath.parent
            else:
                self.report({"ERROR"}, f"Invalid path: {filepath}")
                return {"CANCELLED"}

        try:
            imported_objects = stage_importer_layer.import_stage(
                str(stage_path),
                import_textures=self.import_textures,
                clear_scene=self.clear_scene,
                create_collection=self.create_collection,
            )

            self.report(
                {"INFO"},
                f"Imported {len(imported_objects)} objects from stage",
            )

        except Exception as e:
            self.report({"ERROR"}, f"Import failed: {e}")
            import traceback
            traceback.print_exc()
            return {"CANCELLED"}

        return {"FINISHED"}

    def draw(self, context):
        """Draw the import options panel."""
        layout = self.layout
        layout.prop(self, "clear_scene")
        layout.prop(self, "import_textures")
        layout.prop(self, "create_collection")


class ImportStageDirect(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
    """Import FMOD or JKR files directly from an unpacked stage directory."""

    bl_idname = "custom_import.import_mhf_stage_direct"
    bl_label = "Load MHF Stage Files (FMOD/JKR)"
    bl_options = {"REGISTER", "PRESET", "UNDO"}

    filename_ext = ".fmod"
    filter_glob: bpy.props.StringProperty(
        default="*.fmod;*.jkr",
        options={"HIDDEN"},
        maxlen=255,
    )

    # Allow multiple file selection
    files: bpy.props.CollectionProperty(
        type=bpy.types.OperatorFileListElement,
    )

    directory: bpy.props.StringProperty(
        subtype="DIR_PATH",
    )

    clear_scene: bpy.props.BoolProperty(
        name="Clear scene before import",
        description="Clears all contents before importing",
        default=False,
    )

    import_textures: bpy.props.BoolProperty(
        name="Import Textures",
        description="Import textures from nearby files",
        default=True,
    )

    create_collection: bpy.props.BoolProperty(
        name="Create Collection",
        description="Create a new collection for the imported files",
        default=True,
    )

    def execute(self, context):
        """Import selected files."""
        try:
            bpy.ops.object.mode_set(mode="OBJECT")
        except RuntimeError as error:
            print(error)

        bpy.ops.object.select_all(action="DESELECT")

        if self.clear_scene:
            stage_importer_layer.fmod_importer_layer.clear_scene()

        directory = Path(self.directory)
        total_objects = 0

        # Create a collection for all imports
        collection = None
        if self.create_collection:
            collection = bpy.data.collections.new(directory.name)
            bpy.context.scene.collection.children.link(collection)

        for file_elem in self.files:
            filepath = directory / file_elem.name

            try:
                if filepath.suffix.lower() == ".fmod":
                    objects = stage_importer_layer.import_fmod_file(
                        filepath, self.import_textures, collection
                    )
                elif filepath.suffix.lower() == ".jkr":
                    objects = stage_importer_layer.import_jkr_file(
                        filepath, self.import_textures, collection
                    )
                else:
                    print(f"Skipping unknown file type: {filepath.name}")
                    continue

                total_objects += len(objects)
                print(f"Imported {len(objects)} objects from {filepath.name}")

            except Exception as e:
                print(f"Error importing {filepath.name}: {e}")
                import traceback
                traceback.print_exc()

        self.report({"INFO"}, f"Imported {total_objects} objects from {len(self.files)} files")
        return {"FINISHED"}

    def draw(self, context):
        """Draw the import options panel."""
        layout = self.layout
        layout.prop(self, "clear_scene")
        layout.prop(self, "import_textures")
        layout.prop(self, "create_collection")


def menu_func_import(self, context):
    """Add the operator to the import menu."""
    self.layout.operator(ImportStage.bl_idname, text="MHF Stage (.pac)")


def menu_func_import_direct(self, context):
    """Add the direct import operator to the import menu."""
    self.layout.operator(
        ImportStageDirect.bl_idname, text="MHF Stage Files (FMOD/JKR)"
    )
