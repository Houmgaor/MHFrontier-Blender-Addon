# MHFrontier Animation Debug Findings

This document captures the investigation and fixes for getting MHF animations to work in Blender.

## Problem Summary

Animations parsed from MHF .mot files "only animate parts of the body." Investigation revealed 5 issues in the motion file parser and exporter.

## Game Engine

MHF uses a custom engine derived from the MH2/Freedom Unite era. It is **not** MT Framework (which powers MH4U, MHWorld, etc.). This means file formats and animation conventions differ significantly from the MT Framework modding community's documentation.

## Root Causes Found

### 1. Bone Rotation Mode Mismatch (Primary Issue)

**Problem:** Blender pose bones default to `QUATERNION` rotation mode, but MHF animations use Euler rotations stored in the `rotation_euler` property.

**Symptom:** Animation data exists but bones don't move because Blender ignores `rotation_euler` when in `QUATERNION` mode.

**Fix:** Set each animated bone's `rotation_mode = 'XYZ'` before applying animation.

```python
pose_bone.rotation_mode = 'XYZ'
```

**Location:** `mhfrontier/importers/motion.py`

### 2. Bone Block Size Mismatch (12-byte vs 8-byte)

**Problem:** Real game `.mot` files use 12-byte bone group headers:

| Offset | Size | Field |
|--------|------|-------|
| 0 | 4 | block_type (`0x80000000 \| channel_mask`) |
| 4 | 4 | channel_count |
| 8 | 4 | block_size (total bytes including this header) |

The parser was reading only 8 bytes, treating the block_size word as the next block. This caused the parser to misinterpret data and lose track of bone boundaries.

**Fix:** After reading the 8-byte bone header, peek at the next word. If it's not a keyframe block (`0x8012xxxx`), not another bone block (`0x8xxxxxxx`), and not zero, treat it as the block_size third word and skip it. This handles both 12-byte game files and legacy 8-byte exported files.

**Export fix:** `build_bone_group_block()` now writes proper 12-byte blocks with channel_mask, channel_count, and block_size.

**Location:** `mhfrontier/fmod/fmot.py` - `_parse_animation_at_offset()`, `mhfrontier/export/fmot_export.py` - `build_bone_group_block()`

### 3. Bone ID Mapping (Fixed Earlier)

**Problem:** Animation parser was treating channel mask values (0x038, 0x1C0, 0x1F8) as bone IDs.

**Fix:** Changed to sequential bone indexing based on bone group block order (block 0 -> Bone.000, block 1 -> Bone.001, etc.).

**Location:** `mhfrontier/fmod/fmot.py` - `_parse_animation_at_offset()`

### 4. Position Animation Values (Fixed Earlier)

**Problem:** Position values in MHF animations appear to be absolute world positions, not local bone offsets.

**Fix:** Skip position animation for non-root bones.

**Location:** `mhfrontier/importers/motion.py`

### 5. Index Table Header Ignored

**Problem:** `.mot` files have an animation offset table at the start, before the animation blocks. The parser currently scans for `0x80000002` markers instead of using this table.

**Impact:** Low. The scan approach works but is less efficient and could theoretically find false positives in large files. The index table format needs further investigation.

## Animation File Structure

### Index Table (File Header)

The `.mot` file begins with an index table pointing to animation blocks. Format not fully decoded. The current parser bypasses this by scanning for `0x80000002` animation header markers.

### Animation Block

```
Animation Header (16 bytes):
  uint32: type (0x80000002)
  uint32: bone count
  uint32: total size (bytes, including this header)
  uint32: format version (0=standard, >0=extended with extra float)

If format_version > 0:
  float32: unknown extra value (4 bytes)

Bone Group Blocks (12 bytes each):
  uint32: block_type (0x80000000 | channel_mask)
  uint32: channel_count
  uint32: block_size (total including this 12-byte header)

  Channel masks:
    0x038 = position channels (X:0x008, Y:0x010, Z:0x020)
    0x1C0 = rotation channels (X:0x040, Y:0x080, Z:0x100)
    0xE00 = scale channels (X:0x200, Y:0x400, Z:0x800)
    0x1F8 = position + rotation

Keyframe Blocks (8 + N*8 bytes):
  uint32: block_type (0x80120000 | channel_type)
  uint16: keyframe count
  uint16: padding
  N * 8 bytes: keyframes
    int16: tangent_in
    int16: tangent_out
    int16: value
    uint16: frame number
```

## Observed Bone Counts and Animation Tiers

Animation bone counts vary by model type:

| Model Type | Observed Bone Counts | Notes |
|------------|---------------------|-------|
| NPC | 23 | Most consistent |
| Player | 9 or 12 | Varies by animation |
| Monster | 5, 11, 29 | Varies widely |

Animations typically cover only a subset of the skeleton's total bones.

### Monster Animation Tier System (Verified in Blender)

Analysis of em107 (Espinas, 58-bone skeleton, 255 animations) revealed a precise 3-tier system:

| Tier | Bone Count | Bones Covered | Count | Purpose |
|------|-----------|---------------|-------|---------|
| Core | 5 | Bones 0-4 | 85 | Root/spine movement |
| Upper | 15 | Bones 1-15 | 85 | Body + wings + head |
| Full | 31 | Bones 0-30 | 85 | All major bones including tail, legs |

All three tiers have exactly 85 animations each (255 total = 85 x 3). Each tier has the same set of animation indices (idle, attacks, etc.) but at different detail levels. The game likely blends these tiers as animation layers.

This explains the "only animates parts of the body" observation: it's by design, not a parser bug. A 5-bone animation only moves the core, while a 31-bone animation moves 31 out of 58 bones. The remaining 27 bones (Bones 31-56 + root Bone.255) are never animated in this monster's data — they are likely driven by IK, physics, or are static attachment points.

Blender rendering confirms all tiers produce visually distinct and plausible poses.

## Channel Type Mapping

| MHF Channel | Hex Value | Blender Property | Array Index | Notes |
|-------------|-----------|------------------|-------------|-------|
| POSITION_X | 0x008 | location | 0 | Root only |
| POSITION_Y | 0x010 | location | 2 | Y->Z swap |
| POSITION_Z | 0x020 | location | 1 | Z->Y swap |
| ROTATION_X | 0x040 | rotation_euler | 0 | |
| ROTATION_Y | 0x080 | rotation_euler | 2 | Y->Z swap |
| ROTATION_Z | 0x100 | rotation_euler | 1 | Z->Y swap |
| SCALE_X | 0x200 | scale | 0 | |
| SCALE_Y | 0x400 | scale | 2 | Y->Z swap |
| SCALE_Z | 0x800 | scale | 1 | Z->Y swap |

## Value Conversion

- **Position:** `value * IMPORT_SCALE` (0.01)
- **Rotation:** `value * ROTATION_SCALE` (pi / 32768)
- **Scale:** `(value / 32768.0) + 1.0` (offset from unit scale)

## Open Questions

### Bone-to-Skeleton Mapping

Sequential mapping (bone block 0 -> Bone.000, block 1 -> Bone.001, etc.) is confirmed working in Blender for all three animation tiers. The 5-bone tier animates Bones 0-4, 15-bone animates Bones 1-15, and 31-bone animates Bones 0-30. All produce visually correct and distinct poses on the em107 model.

However, the mapping assumes animation bones always start from bone 0/1 and are contiguous. If some animation format maps to non-contiguous bones (e.g., animating only the head and tail), the current parser would mis-assign them. Evidence so far shows contiguous mapping, but other monster types may differ.

The game engine likely uses animation layers — blending a 5-bone core animation with a 15-bone or 31-bone detail animation at runtime.

### Channel Reinterpretation

Mask-0x038 channels are interpreted as position (X:0x008, Y:0x010, Z:0x020). However, the same bit positions could represent rotation in an alternate scheme. Values observed are plausible as either position or rotation. Further binary analysis of the game executable would be needed to confirm.

### Stray Values Between Keyframe Blocks

Small integer values (1-3) sometimes appear between keyframe blocks within a bone's data region. These don't match any known block header pattern. Possible interpretations:

- Padding/alignment bytes
- Interpolation mode flags
- Sub-block separators

The parser currently skips these via the `pos += 4` fallback for unknown block types.

## Testing

```bash
cd MHFrontier-Blender-Addon
python -m unittest tests.fmod.test_fmot
python -m unittest tests.fmod.test_fmot_export
python -m unittest discover -s tests/
```

The round-trip test (`TestRoundTripConsistency`) is the critical check: export -> reimport must produce identical data structures.

## Important: Blender Module Caching

If testing changes to the addon, Blender caches Python modules. To force reload:

```python
import sys
modules_to_reload = [name for name in sys.modules.keys() if 'mhfrontier' in name]
for mod_name in modules_to_reload:
    del sys.modules[mod_name]
```
