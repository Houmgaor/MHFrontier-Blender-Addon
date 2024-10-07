# Monster-Hunter-Frontier-Importer

A model importer for Monster Hunter Frontier FMod Files into Blender.

## Install

Install as any Blender add-on:

- Download this repo as ZIP ([Code > Download ZIP](https://github.com/Houmgaor/Monster-Hunter-Frontier-Importer/archive/refs/heads/main.zip))
- Open Blender, ``Edit > Preferences > Add-ons > Install...`` select the ZIP folder.

## Usage

Decompress data with [ReFrontier](https://github.com/Houmgaor/ReFrontier).
You want .fmod (3D model) or .fskl (skeleton) files.
Open Blender, ``File > Import > MHF FMOD``, select the file.

![Disufiroa 3D model](https://github.com/Houmgaor/Monster-Hunter-Frontier-Importer/assets/35099109/f9ebbd8f-2ccd-418b-ae0b-c1cfedbfcf68)

Add the "skeleton" (hierarchy of axes), ``File > Import > MHF FSKL``.
  
![Disufiroa skeleton](https://github.com/Houmgaor/Monster-Hunter-Frontier-Importer/assets/35099109/6e4461a3-f65b-45c6-b3cc-509edafb76df)

Convert the skeleton to an armature, ``Object > Create Armature from FSKL Tree``.

![Disufiroa with armature](https://github.com/Houmgaor/Monster-Hunter-Frontier-Importer/assets/35099109/4d4dbf43-ae29-4d32-9af8-c3be6d85f1ff)

Your model is imported with the textures, and you can change its pose.

![Disufiroa image](https://github.com/Houmgaor/Monster-Hunter-Frontier-Importer/assets/35099109/2c9f9223-3296-437e-856b-446cfb1cf2a7)

## Author

* **AsteriskAmpersand/\*&**

## Acknowledgements

* **MHVuze** - For the Frontier Recursive Block Format documentation used to build this importer.
* **Silvris** - For the Materials and Skeleton documentation used to build this importer.

## In this fork (Houmgaor/)

- Compatibility with Blender 2.8+.
- Some code documentation.
