# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.2] - 2025-03-16

### Added

- For weapons with different parts such as lance, it was impossible to import due to missing vertex group data.
  Those vertex group are not recreated automatically, but not linked to each other.
  This does fix the bug, but does not bring a useful feature yet.
  See [#5](https://github.com/Houmgaor/MHFrontier-Blender-Addon/issues/5), thanks
  to [@byDaan](https://github.com/byDaan) for his support.

### Changed

- `extra/zip_addon.py` parses the project version and add the version to the output zip name.

## [2.1.1] - 2024-11-13

### Added in 2.1.1

- Support for the new [Extension](https://extensions.blender.org/) format.

### Changed in 2.1.1

- Licensing as GPL v3.0 (authorized by *&).
- Files reorganization.

### Fixed in 2.1.1

- You can load more models ([#1](https://github.com/Houmgaor/MHFrontier-Blender-Addon/issues/1)).

## [2.1.0] - 2024-11-11

### Changed in 2.1.0

- Code structure overhaul for future maintenance.

It also comes with more lintings and improvements.

### Fixed in 2.1.0

- Models are now scaled to 1/100th and axes are
  swapped ([#2](https://github.com/Houmgaor/MHFrontier-Blender-Addon/issues/2)).

## [2.0.0] - 2024-11-10

Initial compatibility of the project with Blender 2.8+.

### Added in 2.0.0

- Cleaned-up project
- Compatibility with modern Blender version (anything in between 2.7.0 and 4.2.x
  is fine).
