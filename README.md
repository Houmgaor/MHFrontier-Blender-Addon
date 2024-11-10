# Monster-Hunter-Frontier-Importer

A model importer for Monster Hunter Frontier FMod Files into Blender.

## Install

Install as any Blender add-on:

- Download this repo as a ZIP from the [latest release](https://github.com/Houmgaor/MHFrontier-Blender-Addon/releases/)
- Open Blender, ``Edit > Preferences > Add-ons > Install...`` select the ZIP folder.

## Usage

Locate the data you want to import, have a look at [Get FMOD/FSKL files](#get-fmodfskl-files) to find them.
Open Blender, ``File > Import > MHF FMOD``, select the file.

![Disufiroa 3D model](https://github.com/Houmgaor/Monster-Hunter-Frontier-Importer/assets/35099109/f9ebbd8f-2ccd-418b-ae0b-c1cfedbfcf68)
![Disufiroa with textures](https://github.com/Houmgaor/Monster-Hunter-Frontier-Importer/assets/35099109/2c9f9223-3296-437e-856b-446cfb1cf2a7)

Add the "skeleton" (hierarchy of axes), ``File > Import > MHF FSKL``.

![Disufiroa skeleton](https://github.com/Houmgaor/Monster-Hunter-Frontier-Importer/assets/35099109/6e4461a3-f65b-45c6-b3cc-509edafb76df)

Convert the skeleton to an armature, ``Object > Create Armature from FSKL Tree``.

![Disufiroa with armature](https://github.com/Houmgaor/Monster-Hunter-Frontier-Importer/assets/35099109/4d4dbf43-ae29-4d32-9af8-c3be6d85f1ff)

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

To have any data to extract, you need a Monster Hunter Frontier Z game.
Then, the game data need to be decompressed,
you don't need to decompress everything as the monster models are in "[yout MHFrontier folder]/dat/emmodel[_hd]".
To known which file is which monster you can
use [em.md](https://github.com/Houmgaor/ReFrontier/blob/1cc4bace77766868ba1d6230b39dce0a8a7f6d9b/data_dumps/em.md) as a
reference.
To decompress data use [ReFrontier](https://github.com/Houmgaor/ReFrontier).
You want .fmod (3D model) or .fskl (skeleton) files.

## In this fork (Houmgaor/)

- Compatibility with Blender 2.8+.
- Correctly scale and orient models.
- Documentation.
- Code linting.

## Credits

### Author

* **AsteriskAmpersand/\*&**

### Acknowledgements

* **MHVuze** - For the Frontier Recursive Block Format documentation used to build this importer.
* **Silvris** - For the Materials and Skeleton documentation used to build this importer.
