# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Blender add-on that imports Monster Hunter Frontier 3D models (.fmod), skeletons (.fskl), and stage/map files into Blender 2.8+. Part of the MHFrontier preservation ecosystem.

## Commands

```bash
# Build addon (Blender 4.2+)
cd mhfrontier
blender --command extension build

# Legacy build
python extra/zip_addon.py

# Run all tests (requires model files in tests/models/)
python -m unittest discover -s tests/

# Run specific test module
python -m unittest tests.fmod.test_fmod
python -m unittest tests.fmod.test_fskl
python -m unittest tests.stage.test_stage_container

# Run single test
python -m unittest tests.fmod.test_fmod.TestFModFileLoading.test_load_fmod_file
```

## Architecture

### Blender API Abstraction

The codebase uses an abstraction layer (`blender/api.py`) to decouple import logic from Blender's API. This enables unit testing without Blender:

- `blender/api.py` - Abstract interfaces: `MeshBuilder`, `ObjectBuilder`, `MaterialBuilder`, `ImageLoader`, `SceneManager`, `MatrixFactory`
- `blender/blender_impl.py` - Real Blender implementation (used in addon)
- `blender/mock_impl.py` - Mock implementation (used in tests)

Import modules accept builder interfaces and can be tested with mocks.

### Module Structure

```
mhfrontier/
├── __init__.py              # Blender registration, registers 5 operators
├── config.py                # Import scale (0.01) and axis remap constants
├── common/                  # Binary parsing infrastructure
│   ├── cstruct.py           # C-like struct serialization
│   ├── pycstruct.py         # Base class for structured data
│   ├── filelike.py          # File-like stream wrapper
│   ├── data_containers.py   # Geometry data blocks (vertex, UV, weight)
│   └── standard_structures.py # FBlockHeader, BoneBlock, MaterialData, etc.
├── fmod/                    # Format parsers + Blender import
│   ├── fblock.py            # Recursive block parser, BlockType enum, type→class mapping
│   ├── fmod.py              # FMOD loader API: load_fmod_file(path) → (meshes, materials)
│   ├── fmesh.py             # Mesh extraction: vertices, faces, normals, UVs, weights
│   ├── fmat.py              # Material data extraction
│   ├── fskl.py              # Skeleton loader: get_frontier_skeleton(path)
│   ├── fbone.py             # Bone hierarchy data structures
│   ├── mesh_importer.py     # Mesh import using builder interfaces
│   ├── material_importer.py # Material import using builder interfaces
│   ├── fmod_importer_layer.py    # Main Blender mesh/material import
│   ├── fskl_importer_layer.py    # Skeleton to Blender empty objects
│   ├── stage_importer_layer.py   # Stage/map import orchestration
│   ├── stage_container_importer.py  # Imports from .pac containers
│   └── stage_directory_importer.py  # Imports from directory of FMODs
├── operators/               # Blender UI operators
│   ├── fmod_import.py       # File > Import > MHF FMOD
│   ├── fskl_import.py       # File > Import > MHF FSKL
│   ├── stage_import.py      # File > Import > MHF Stage (container or directory)
│   └── fskl_convert.py      # Object > Create Armature from FSKL Tree
├── stage/                   # Stage container + compression
│   ├── stage_container.py   # .pac container parser (detects by magic bytes)
│   └── jkr_decompress.py    # JKR/JPK decompression (Huffman)
└── blender/
    ├── api.py               # Abstract builder interfaces for testability
    ├── blender_impl.py      # Real Blender API implementation
    ├── mock_impl.py         # Mock implementation for testing
    └── blender_nodes_functions.py  # Shader node creation (Principled BSDF)
```

### Import Pipeline

**FMOD (3D Model):**
```
.fmod → fblock.py (recursive block parse) → fmesh.py (extract geometry)
     → mesh_importer.py (via MeshBuilder interface) → Blender mesh + materials + weight groups
```

**FSKL (Skeleton):**
```
.fskl → fblock.py → fskl.py (FBone hierarchy)
     → fskl_importer_layer.py → Blender empty objects with parent hierarchy
     → fskl_convert.py → Blender armature (user-triggered)
```

**Stage/Map (two modes):**
```
Container mode (.pac):
  .pac → stage_container.py (parse by magic bytes) → jkr_decompress.py (if JKR)
       → stage_container_importer.py → Blender collection

Directory mode:
  folder/ → stage_directory_importer.py (finds all .fmod files)
         → imports each via fmod_importer_layer → Blender collection
```

### Block Format

Frontier uses a recursive block structure. Block types are identified by 4-byte IDs:
- `0x00000001` - FileBlock
- `0x00000002` - MainBlock (contains meshes)
- `0x00000003` - ObjectBlock
- `0x00000006` - MaterialBlock
- `0x00000007` - TextureBlock
- `0x0000000A` - SkeletonBlock

Magic bytes for stage segments:
- JKR: `0x1A524B4A` - Compressed data
- FMOD: `0x444F4D46` - Model geometry
- PNG: `0x474E5089`, DDS: `0x20534444`, OGG: `0x5367674F`

### Coordinate System

- Models scaled to 1/100th of original size
- Axis remapping: Frontier → Blender (indices [0,2,1,3])
- Pose vectors in `fskl_importer_layer.py` handle axis swapping

### Texture Loading

`import_textures()` in `fmod_importer_layer.py` performs greedy search for .dds/.png files in the import directory using texture IDs from material data.

## Key Entry Points

- `fmod/fmod.py:load_fmod_file()` - Load model data from file
- `fmod/fskl.py:get_frontier_skeleton()` - Load skeleton data
- `fmod/fmod_importer_layer.py:import_model()` - Create Blender objects
- `stage/stage_container.py:parse_stage_container()` - Parse .pac files

## Testing

Tests use Python's `unittest`. Model files must be placed in `tests/models/` (not included in repo - users must provide their own legally obtained files).

Test helper `tests/__init__.py:get_model_files(directory, extension)` recursively finds test files.

Tests for format parsing can run without Blender. Tests involving import use the mock builders in `blender/mock_impl.py`.
