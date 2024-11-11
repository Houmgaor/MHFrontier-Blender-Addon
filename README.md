# Monster Hunter Frontier Blender Add-on

A model importer for Monster Hunter Frontier FMOD/FSKL Files into Blender.

## Install

Install as any Blender add-on:

- Download this repo as a ZIP from the [latest release](https://github.com/Houmgaor/MHFrontier-Blender-Addon/releases/)
- Open Blender, ``Edit > Preferences > Add-ons > Install...`` select the ZIP folder.

## Usage

Locate the data you want to import, have a look at [Get FMOD/FSKL files](#get-fmodfskl-files) to find them.
Open Blender, ``File > Import > MHF FMOD``, select the file.

![Disufiroa with textures](https://github.com/user-attachments/assets/392141c6-064c-480b-b044-8cd85c70fda7)

Add the "skeleton" (hierarchy of axes), ``File > Import > MHF FSKL``.

![Disufiroa skeleton](https://github.com/user-attachments/assets/72ce210f-f1a5-4d54-88a8-b31def90ac17)

Convert the skeleton to an armature, ``Object > Create Armature from FSKL Tree``.

![Disufiroa with armature](https://github.com/user-attachments/assets/db92b3fe-f9d4-4d72-8ad8-6bf5747036ae)

Your model is imported with the textures, and you can change its pose.

![Disufiroa rendered](https://github.com/user-attachments/assets/fe1c5bbb-baac-4b08-84df-63fbdb9a2e5e)

## Build

The important part of the addon is in the "mhfrontier" folder.
You only need to create a ZIP of this folder to build it.
If you want to do it from a python script just run.

```commandline
python extra/zip_addon.py
```

## Get FMOD/FSKL files

To get any data to extract, you need a Monster Hunter Frontier Z game.
Then, the game data need to be decompressed,
you don't need to decompress everything as the monster models are in "[your MHFrontier folder]/dat/emmodel[_hd]".
To known which file is which monster you can
use [monster_ids.md](https://github.com/Houmgaor/ReFrontier/blob/c67b02d1031e380d9f217d17eb89ca3d075206ee/monster_ids.md)
as a
reference.
To decompress data use [ReFrontier](https://github.com/Houmgaor/ReFrontier).
You want .fmod (3D model) and .fskl (skeleton) files.

## In this fork (Houmgaor/)

- Some models could not load with the original add-on.
- Compatibility with Blender 2.8+.
- Correctly scale and orient models.
- Less memory usage, preventing crash.
- Documentation.
- Code linting.

## Credits

### Author

* **AsteriskAmpersand/\*&**

### Acknowledgements

* **MHVuze** - For the Frontier Recursive Block Format documentation used to build this importer.
* **Silvris** - For the Materials and Skeleton documentation used to build this importer.
