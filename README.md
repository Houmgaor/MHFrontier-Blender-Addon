# Monster Hunter Frontier Blender Add-on

**Import and export Monster Hunter Frontier 3D models, skeletons, animations, and stage maps in Blender.**

Compatible with **Blender 2.8 through 4.x** | Actively maintained | [Download latest release](https://github.com/Houmgaor/MHFrontier-Blender-Addon/releases/)

![Disufiroa rendered in Blender](https://github.com/user-attachments/assets/fe1c5bbb-baac-4b08-84df-63fbdb9a2e5e)

## Features

| Format | Extension | Import | Export | Description |
|--------|-----------|:------:|:------:|-------------|
| FMOD | `.fmod` | Yes | Yes | 3D model geometry with textures |
| FSKL | `.fskl` | Yes | Yes | Skeleton/bone hierarchy |
| MOT | `.mot` | Yes | | Animation/motion data |
| AAN | `.aan` | Yes | | Animation packages with multi-part body regions |
| Stage | `.pac` / directory | Yes | | Map/stage files with multiple models and audio |

## Install

1. Download the ZIP from the [latest release](https://github.com/Houmgaor/MHFrontier-Blender-Addon/releases/).
2. In Blender: `Edit > Preferences > Add-ons > Install...`, select the ZIP.

## Quick Start

### Model Import

`File > Import > MHF FMOD`, select the file. Your model is imported with textures applied.

![Disufiroa with textures](https://github.com/user-attachments/assets/392141c6-064c-480b-b044-8cd85c70fda7)

### Skeleton Import

`File > Import > MHF FSKL` to add the bone hierarchy, then `Object > Create Armature from FSKL Tree` to convert it to a Blender armature.

![Disufiroa skeleton](https://github.com/user-attachments/assets/72ce210f-f1a5-4d54-88a8-b31def90ac17)

![Disufiroa with armature](https://github.com/user-attachments/assets/db92b3fe-f9d4-4d72-8ad8-6bf5747036ae)

### Animation Import

With an armature selected, `File > Import > MHF Motion (.mot)` or `File > Import > MHF AAN Animation (.aan)` for multi-part body animations. Choose between **Monster** mode (body region buckets) or **Player** mode (upper/lower body split).

### Stage/Map Import

- **Container mode**: `File > Import > MHF Stage` - Select a `.pac` container file. Handles JKR decompression and OGG audio extraction automatically.
- **Directory mode**: `File > Import > MHF Stage (Directory)` - Select a folder of FMOD files.

### Export

- `File > Export > MHF FMOD` - Export meshes back to Frontier format.
- `File > Export > MHF FSKL` - Export armature or empty hierarchy.

## Getting Game Files

You need a Monster Hunter Frontier Z game client. The game data must be decompressed:

1. Monster models are in `[MHFrontier folder]/dat/emmodel[_hd]`.
2. Animations are in `[MHFrontier folder]/dat/motion`.
3. Use [ReFrontier](https://github.com/Houmgaor/ReFrontier) to decompress files.
4. See [monster_ids.md](https://github.com/Houmgaor/ReFrontier/blob/c67b02d1031e380d9f217d17eb89ca3d075206ee/monster_ids.md) to identify which file corresponds to which monster.

For a complete guide, see [Getting Started (Frontier Z)](https://github.com/The1andonlyDarto/MHAssetInfo/wiki/Getting-Started-(Frontier-Z)) and the [Blender tutorial](https://github.com/The1andonlyDarto/MHAssetInfo/wiki/Blender-Importing-(Frontier-Z)).

## Build

The add-on source is in the `mhfrontier/` folder.

```bash
# Blender 4.2+
cd mhfrontier
blender --command extension build

# Legacy
python extra/zip_addon.py
```

## Test

```bash
# Run all tests (requires model files in tests/models/)
python -m unittest discover -s tests/

# Run specific test module
python -m unittest tests.fmod.test_fmod
python -m unittest tests.stage.test_stage_container
```

## Acknowledgements

* @AsteriskAmpersand / *& - Original author.
* @MHVuze / Vuze - For the Frontier Recursive Block Format documentation used to build this importer.
* @Silvris - For the Materials and Skeleton documentation used to build this importer.
* @Paxlord - For the AAN animation parser and player animation support from [mhfz-blender-plugin](https://github.com/Paxlord/mhfz-blender-plugin).

## License

Licensed under GPL v3.0, courtesy of @AsteriskAmpersand.
