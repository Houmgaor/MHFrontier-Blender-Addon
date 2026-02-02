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

- `blender/api.py` - Abstract interfaces: `MeshBuilder`, `ObjectBuilder`, `MaterialBuilder`, `ImageLoader`, `SceneManager`, `MatrixFactory`, `AnimationBuilder`
- `blender/builders.py` - Centralized `Builders` dataclass and `get_builders()` factory
- `blender/blender_impl.py` - Real Blender implementation (used in addon)
- `blender/mock_impl.py` - Mock implementation (used in tests)

Import modules accept `Builders` and can be tested with mocks via `get_mock_builders()`.

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
├── fmod/                    # Format parsers (pure parsing, no Blender)
│   ├── fblock.py            # Recursive block parser, BlockType enum, type→class mapping
│   ├── fmod.py              # FMOD loader: load_fmod_file(path) → (meshes, materials)
│   ├── fmesh.py             # Mesh extraction: vertices, faces, normals, UVs, weights
│   ├── fmat.py              # Material data extraction
│   ├── fskl.py              # Skeleton loader: get_frontier_skeleton(path)
│   ├── fbone.py             # Bone hierarchy data structures
│   └── fmot.py              # Motion file parsing
├── importers/               # Blender import orchestration (uses Builders)
│   ├── __init__.py          # Public API: import_model, import_skeleton, import_stage, etc.
│   ├── fmod.py              # FMOD model import orchestration
│   ├── mesh.py              # Mesh import using builder interfaces
│   ├── material.py          # Material/texture import using builder interfaces
│   ├── skeleton.py          # Skeleton to Blender empty objects
│   ├── motion.py            # Motion/animation import
│   ├── stage.py             # Stage/map import orchestration
│   ├── stage_container.py   # Imports from .pac containers
│   └── stage_directory.py   # Imports from directory of FMODs
├── operators/               # Blender UI operators
│   ├── fmod_import.py       # File > Import > MHF FMOD
│   ├── fskl_import.py       # File > Import > MHF FSKL
│   ├── fmot_import.py       # File > Import > MHF Motion
│   ├── stage_import.py      # File > Import > MHF Stage (container or directory)
│   └── fskl_convert.py      # Object > Create Armature from FSKL Tree
├── stage/                   # Stage container + compression
│   ├── stage_container.py   # .pac container parser (detects by magic bytes)
│   └── jkr_decompress.py    # JKR/JPK decompression (Huffman)
└── blender/
    ├── api.py               # Abstract builder interfaces for testability
    ├── builders.py          # Centralized Builders dataclass and factory
    ├── blender_impl.py      # Real Blender API implementation
    ├── mock_impl.py         # Mock implementation for testing
    └── blender_nodes_functions.py  # Shader node creation (Principled BSDF)
```

### Import Pipeline

**FMOD (3D Model):**
```
.fmod → fmod/fblock.py (recursive block parse) → fmod/fmesh.py (extract geometry)
     → importers/mesh.py (via Builders interface) → Blender mesh + materials + weight groups
```

**FSKL (Skeleton):**
```
.fskl → fmod/fblock.py → fmod/fskl.py (FBone hierarchy)
     → importers/skeleton.py → Blender empty objects with parent hierarchy
     → operators/fskl_convert.py → Blender armature (user-triggered)
```

**Motion (.mot):**
```
.mot → fmod/fmot.py (parse keyframes)
    → importers/motion.py → Blender Action with FCurves
```

**Stage/Map (two modes):**
```
Container mode (.pac):
  .pac → stage/stage_container.py (parse by magic bytes) → stage/jkr_decompress.py (if JKR)
       → importers/stage_container.py → Blender collection

Directory mode:
  folder/ → importers/stage_directory.py (finds all .fmod files)
         → imports each via importers/stage.py → Blender collection
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
- Pose vectors in `importers/skeleton.py` handle axis swapping

### Texture Loading

`import_textures()` in `importers/material.py` performs greedy search for .dds/.png files in the import directory using texture IDs from material data.

## Key Entry Points

- `fmod/fmod.py:load_fmod_file()` - Load model data from file
- `fmod/fskl.py:get_frontier_skeleton()` - Load skeleton data
- `fmod/fmot.py:load_motion_file()` - Load motion/animation data
- `importers.import_model()` - Create Blender objects from FMOD
- `importers.import_skeleton()` - Create Blender empty objects from FSKL
- `importers.import_motion()` - Create Blender Action from motion file
- `importers.import_stage()` - Import stage container or directory
- `stage/stage_container.py:parse_stage_container()` - Parse .pac files

## Testing

Tests use Python's `unittest`. Model files must be placed in `tests/models/` (not included in repo - users must provide their own legally obtained files).

Test helper `tests/__init__.py:get_model_files(directory, extension)` recursively finds test files.

Tests for format parsing can run without Blender. Tests involving import use the mock builders in `blender/mock_impl.py`.
