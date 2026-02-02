# Monster Hunter Frontier Blender Add-on

A model importer for Monster Hunter Frontier FMOD/FSKL/MOT files into Blender.

## Install

Install as any Blender add-on:

- Download this repo as a ZIP from the [latest release](https://github.com/Houmgaor/MHFrontier-Blender-Addon/releases/)
- Open Blender, ``Edit > Preferences > Add-ons > Install...`` select the ZIP folder.

## Usage

Locate the data you want to import, have a look at the [documentation](#documentation) section to find them.
Open Blender, ``File > Import > MHF FMOD``, select the file.

![Disufiroa with textures](https://github.com/user-attachments/assets/392141c6-064c-480b-b044-8cd85c70fda7)

Add the "skeleton" (hierarchy of axes), ``File > Import > MHF FSKL``.

![Disufiroa skeleton](https://github.com/user-attachments/assets/72ce210f-f1a5-4d54-88a8-b31def90ac17)

Convert the skeleton to an armature, ``Object > Create Armature from FSKL Tree``.

![Disufiroa with armature](https://github.com/user-attachments/assets/db92b3fe-f9d4-4d72-8ad8-6bf5747036ae)

Your model is imported with the textures, and you can change its pose.

### Animation Import

To import animations, first create an armature as described above.
Then with the armature selected, ``File > Import > MHF Motion (.mot)``.

The animation will be imported as a Blender Action and automatically assigned to the armature.
You can view the animation in the Timeline or Dope Sheet editors.

![Disufiroa rendered](https://github.com/user-attachments/assets/fe1c5bbb-baac-4b08-84df-63fbdb9a2e5e)

## Build

The important part of the addon is in the "mhfrontier" folder.
You only need to create a ZIP of this folder to build it.

If you have Blender 4.2+ use:

```commandline
cd mhfrontier
blender --command extension build
```

Otherwise we provide a legacy Python script:

```commandline
python extra/zip_addon.py
```

## Test

Tests are performed with [unittest](https://docs.python.org/3/library/unittest.html).
You need to manually add model folders in ``tests/models/``.
Then open a terminal in the main folder and run:

```commandline
python -m unittest discover -s tests/fmod/
```

## Documentation

An online documentation is available
at [Getting started (Frontier Z)](https://github.com/The1andonlyDarto/MHAssetInfo/wiki/Getting-Started-(Frontier-Z)).

To get any data to extract, you need a Monster Hunter Frontier Z game.
Then, the game data need to be decompressed,
you don't need to decompress everything as the monster models are in "[your MHFrontier folder]/dat/emmodel[_hd]".

To known which file is which monster you can
use [monster_ids.md](https://github.com/Houmgaor/ReFrontier/blob/c67b02d1031e380d9f217d17eb89ca3d075206ee/monster_ids.md)
as a reference.
To decompress data use [ReFrontier](https://github.com/Houmgaor/ReFrontier).
You want .fmod (3D model), .fskl (skeleton), and .mot (animation) files.
Animation files can be found in "[your MHFrontier folder]/dat/motion".

For the next steps, you can follow
the [Blender tutorial](https://github.com/The1andonlyDarto/MHAssetInfo/wiki/Blender-Importing-(Frontier-Z)).

## In this fork (Houmgaor/)

New features:

- Animation/motion file (.mot) import support.
- Weapons such as lance or models with different parts can now be loaded with a skeleton assigned.
- Some models could not load with the original add-on.
- Compatibility with Blender 2.8+.

Changes:

- Correctly scales and orients models.
- Less memory usage, preventing crash.
- Documentation.
- Code linting.

## Acknowledgements

* @AsteriskAmpersand / *& - Original author.
* @MHVuze / Vuze - For the Frontier Recursive Block Format documentation used to build this importer.
* @Silvris - For the Materials and Skeleton documentation used to build this importer.

## License

Licensed under GPL v3.0, courtesy of @AsteriskAmpersand.
