# MHFrontier Animation Debug Findings

This document captures the investigation and fixes for getting MHF animations to work in Blender.

## Problem Summary

Animations parsed from MHF .mot files were not visually playing on imported monster models, despite:
- FCurves being created correctly
- Actions being assigned to armatures
- Keyframe values being present

## Root Causes Found

### 1. Bone Rotation Mode Mismatch (Primary Issue)

**Problem:** Blender pose bones default to `QUATERNION` rotation mode, but MHF animations use Euler rotations stored in the `rotation_euler` property.

**Symptom:** Animation data exists but bones don't move because Blender ignores `rotation_euler` when in `QUATERNION` mode.

**Fix:** Set each animated bone's `rotation_mode = 'XYZ'` before applying animation.

```python
pose_bone.rotation_mode = 'XYZ'
```

**Location:** `mhfrontier/importers/motion.py` - added `_set_bone_rotation_mode()` helper and calls to it.

### 2. Bone ID Mapping (Fixed Earlier)

**Problem:** Animation parser was treating channel mask values (0x038, 0x1C0, 0x1F8) as bone IDs.

**Fix:** Changed to sequential bone indexing based on bone group block order, starting at bone 3 (first weighted bone). Now correctly maps animation blocks to bones 4, 5, 6, etc.

**Location:** `mhfrontier/fmod/fmot.py` - `_parse_animation_at_offset()`

### 3. Position Animation Values (Fixed Earlier)

**Problem:** Position values in MHF animations appear to be absolute world positions, not local bone offsets.

**Fix:** Skip position animation for non-root bones.

**Location:** `mhfrontier/importers/motion.py` - `_channel_to_property_info()` returns `None` for position channels on non-root bones.

## Animation File Structure

MHF animation files (embedded in .bin containers) have this structure:

```
Animation Header: 0x80000002 (4 bytes)
Animation Count: uint32
Total Size: uint32
Padding: 4 bytes

Bone Group Blocks: 0x80XXXXXX where XXXX is channel mask
  - 0x038 = position channels (X,Y,Z)
  - 0x1C0 = rotation channels (X,Y,Z)
  - 0x1F8 = all channels

Keyframe Blocks: 0x801200XX
  - Count: uint16
  - Padding: 2 bytes
  - Keyframes: N * 8 bytes each
    - tangent_in: int16
    - tangent_out: int16
    - value: int16
    - frame: uint16
```

## Channel Type Mapping

| MHF Channel | Hex Value | Blender Property | Array Index | Notes |
|-------------|-----------|------------------|-------------|-------|
| POSITION_X | 0x008 | location | 0 | Root only |
| POSITION_Y | 0x010 | location | 2 | Y→Z swap |
| POSITION_Z | 0x020 | location | 1 | Z→Y swap |
| ROTATION_X | 0x040 | rotation_euler | 0 | |
| ROTATION_Y | 0x080 | rotation_euler | 2 | Y→Z swap |
| ROTATION_Z | 0x100 | rotation_euler | 1 | Z→Y swap |
| SCALE_X | 0x200 | scale | 0 | |
| SCALE_Y | 0x400 | scale | 2 | Y→Z swap |
| SCALE_Z | 0x800 | scale | 1 | Z→Y swap |

## Value Conversion

- **Position:** `value * IMPORT_SCALE` (0.01)
- **Rotation:** `value * ROTATION_SCALE` (π / 32768)
- **Scale:** `value / 32768.0` if large, else raw

## Debug Scripts

Test scripts are in the scratchpad directory:
- `full_debug_animation.py` - Comprehensive debug showing bone names, animation parsing, and FCurve creation
- `simple_anim_test.py` - Direct keyframe creation test
- `check_bone_hierarchy.py` - Lists bone weights and hierarchy

## Testing

Run animation debug in Blender:
```bash
blender --python scratchpad/full_debug_animation.py
```

The script will:
1. Import model and skeleton
2. Convert to armature
3. Parse animation block 41
4. Show which bones exist vs. which are animated
5. Create manual test animation on Bone.003
6. Verify rotation values are applied correctly

## Verified Working

After fixes:
- 58 bones in armature (Bone.000 through Bone.057)
- Animation targets bones 4-18 (15 bones)
- All animated bones exist in armature
- FCurves created with proper keyframe values
- Setting `rotation_mode = 'XYZ'` enables animation playback

## Important: Blender Module Caching

If testing changes to the addon, Blender caches Python modules. To force reload:

```python
import sys
modules_to_reload = [name for name in sys.modules.keys() if 'mhfrontier' in name]
for mod_name in modules_to_reload:
    del sys.modules[mod_name]
```

This ensures the latest code is used when importing modules.
