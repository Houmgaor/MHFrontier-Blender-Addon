# MHFrontier Animation Debug Findings

This document captures the full investigation and fixes for getting MHF animations to work correctly in Blender. The test model is em107 (Disufiroa), a dragon with a 56-bone skeleton and 255 animations.

## Game Engine

MHF uses a custom engine derived from the MH2/Freedom Unite era. It is **not** MT Framework (which powers MH4U, MHWorld, etc.). File formats and animation conventions differ significantly from MT Framework modding documentation.

## Bugs Found and Fixed

### 1. Bone Block Size Mismatch (12-byte vs 8-byte)

**Commit:** `dc51c12`

**Problem:** Real game `.mot` files use 12-byte bone group headers (type + channel_count + block_size), but the parser read only 8 bytes. This caused the parser to misinterpret the block_size word as keyframe data, corrupting bone boundaries.

**Fix:** After reading the 8-byte bone header, peek at the next word. If it's not a keyframe block (`0x8012xxxx`), not another bone block (`0x8xxxxxxx`), and not zero, treat it as the block_size third word and skip it. This handles both 12-byte game files and legacy 8-byte exported files. Export was also fixed to write 12-byte blocks.

**Files:** `fmot.py`, `fmot_export.py`

### 2. Tier-Based Bone Offset Mapping

**Commit:** `baf2507`

**Problem:** Animation bone IDs are local (0-based) within each body-region tier, but the importer mapped them directly to skeleton bone IDs. This caused tier 1 (upper body) animations to target bones 0-30 (hind legs, root) instead of bones 16-46 (torso, head, wings, front legs).

**Symptoms:** "The left legs are almost the only moving parts" — the animation data was correct but applied to the wrong bones.

**Fix:** Added `determine_tier_bone_offsets()` to scan the animation file and detect tier boundaries by grouping consecutive animations with the same bone count. Each tier's cumulative bone count becomes the offset for the next tier. The importer adds `bone_offset` to each local bone ID.

**Files:** `fmot.py` (tier detection), `motion.py` (offset application)

### 3. X Rotation Negation for Coordinate System Conversion

**Commit:** `baf2507`

**Problem:** When converting from MHF's Y-up to Blender's Z-up coordinate system, rotation values around the X axis must be negated. Mathematically: the Y↔Z swap matrix S has determinant -1, and `S · Rx(θ) · S⁻¹ = Rx(-θ)`. Without negation, bones rotated in the wrong direction.

**Fix:** Added `_is_x_rotation()` helper. When a channel represents X-axis rotation (either explicit `ROTATION_X` or reinterpreted `POSITION_X` when no explicit rotation bits), both the value and Bezier tangents are negated.

**Files:** `motion.py`

### 4. Euler Order Change (XYZ → XZY)

**Commit:** `baf2507`

**Problem:** The Y↔Z axis swap changes the Euler decomposition order. MHF's `Rz·Ry·Rx` becomes `Ry_blend·Rz_blend·Rx_blend` in Blender coordinates, which matches Blender's XZY mode, not XYZ.

**Derivation:** For a Y↔Z swap matrix S:
- `S · Rz_mhf(θ) · S⁻¹ = Ry_blend(θ)` (Z→Y, same sign)
- `S · Ry_mhf(θ) · S⁻¹ = Rz_blend(θ)` (Y→Z, same sign)
- `S · Rx_mhf(θ) · S⁻¹ = Rx_blend(-θ)` (X stays, negated)

MHF XYZ: `Rz(rz) · Ry(ry) · Rx(rx)` → Blender: `Ry(rz) · Rz(ry) · Rx(-rx)` = XZY with `euler[0]=-rx, euler[1]=rz, euler[2]=ry`.

**Fix:** Changed `rotation_mode` from `'XYZ'` to `'XZY'` on all animated pose bones.

**Files:** `motion.py`

### 5. Blender animation_data Not Initialized

**Problem:** Blender requires `armature.animation_data_create()` before setting `animation_data.action`. Without it, the action assignment silently fails.

**Fix:** Call `animation_data_create()` before assigning the first action in the interactive script.

### 6. Bone Rotation Mode Mismatch (Earlier Fix)

**Problem:** Blender pose bones default to `QUATERNION` rotation mode, but MHF animations use Euler rotations stored in `rotation_euler`. Blender ignores `rotation_euler` FCurves when in `QUATERNION` mode.

**Fix:** Set `rotation_mode = 'XZY'` (originally `'XYZ'`, corrected later) on each animated bone before applying animation.

## Animation File Structure

### Motion File Layout

```
Motion File (.mot / .bin):
  ┌─ Index Table Header (variable size)
  │   uint32: entries_per_table (e.g., 100)
  │   uint32: total_bone_count (e.g., 56)
  │   N pairs of (uint32 count, uint32 table_offset)
  │   Followed by N tables of animation offsets
  │   Each table entry: uint32 offset to animation block (0xFFFFFFFF = unused)
  │
  ├─ Animation Block 0 (Tier 0, slot 0)
  ├─ Animation Block 1 (Tier 0, slot 1)
  │   ...
  ├─ Animation Block 84 (Tier 0, slot 84)
  ├─ Animation Block 85 (Tier 1, slot 0)
  │   ...
  ├─ Animation Block 169 (Tier 1, slot 84)
  ├─ Animation Block 170 (Tier 2, slot 0)
  │   ...
  └─ Animation Block 254 (Tier 2, slot 84)
```

### Animation Block

```
Animation Header (16 bytes):
  uint32: type marker (0x80000002)
  uint32: bone count (number of bone group blocks)
  uint32: total size (bytes, including this header)
  uint32: format version (0=standard, >0=extended with extra float)

If format_version > 0:
  float32: unknown extra value (4 bytes)

Bone Group Blocks (12 bytes each in game files):
  uint32: block_type (0x80000000 | channel_mask)
  uint32: channel_count (number of keyframe blocks following)
  uint32: block_size (total bytes including this 12-byte header)

Keyframe Blocks (8 + N*8 bytes):
  uint32: block_type (0x80120000 | channel_type)
  uint16: keyframe count
  uint16: padding
  N keyframes (8 bytes each):
    int16: tangent_in
    int16: tangent_out
    int16: value
    uint16: frame number
```

### Channel Masks

```
Bits 0-2:  Alternate position (weapon format): X=0x001, Y=0x002, Z=0x004
Bits 3-5:  Position: X=0x008, Y=0x010, Z=0x020
Bits 6-8:  Rotation: X=0x040, Y=0x080, Z=0x100
Bits 9-11: Scale:    X=0x200, Y=0x400, Z=0x800
```

**Channel reinterpretation:** When a bone's mask has only position bits (0x038) and no rotation bits (0x1C0), the position channels contain rotation data. This is the most common case for monster animations — most bones are rotation-only.

## Tier System (Body Region Animation Layers)

MHF motion files group animations into **tiers**, each animating a contiguous range of skeleton bones. The game plays all tiers simultaneously to compose the full-body animation.

### em107 (Disufiroa) Tier Structure

| Tier | Anim Indices | Bone Count | Skeleton Bones | Body Region |
|------|-------------|------------|----------------|-------------|
| 0 | 0-84 | 16 | 0-15 | Root, hind legs, rear decorations |
| 1 | 85-169 | 31 | 16-46 | Torso, front legs, chest, head/neck, wings |
| 2 | 170-254 | 5 | 47-51 | Tail |

**Total:** 52 animated bones out of 56. Bones 52-55 (auxiliary/physics chain) are never animated.

Each tier has 85 animation slots. Slot N in all tiers corresponds to the same game action (e.g., slot 73 across all 3 tiers = the "attack_heavy" full-body animation).

### Bone Offset Calculation

The offset for each tier is the cumulative bone count of all previous tiers:
- Tier 0: offset = 0
- Tier 1: offset = 16 (tier 0 has 16 bones)
- Tier 2: offset = 47 (16 + 31)

To map animation bone ID to skeleton bone:
```
skeleton_bone_id = animation_local_bone_id + tier_bone_offset
```

### Detection Algorithm

The tier structure is detected automatically by scanning all animation blocks in order and grouping consecutive animations with the same declared bone count. This avoids needing to parse the index table header.

## em107 (Disufiroa) Skeleton Map

56 bones, two root chains. All positions in Frontier-native units (Y-up).

```
Root Chain (Bones 0-51):
  Bone 0:  Root (origin)
  Bone 1:  Body container
  Bone 2:  Body container
  Bone 3:  Hip/pelvis hub
  ├── Bones 4-8:   Right hind leg (hip→thigh→knee→shin→foot)
  ├── Bones 9-13:  Left hind leg (mirror of right)
  ├── Bones 14-15: Rear dorsal spikes (right/left)
  ├── Bones 47-51: Tail (5 segments, extends ~11.5m rearward)
  └── Bone 16: Chest/torso pivot
      └── Bone 17: Upper chest / shoulder girdle
          ├── Bones 18-22: Right front leg (shoulder→arm→elbow→leg→foot)
          ├── Bones 23-27: Left front leg (mirror of right)
          ├── Bone 28: Chest underside / throat
          ├── Bone 29: Chest helper
          ├── Bone 30: Neck base
          │   └── Bones 31-36: Neck chain → head → snout → jaw tip
          │   └── Bone 37: Lower jaw (hinge at bone 33)
          │   └── Bone 38: Horn/accessory
          ├── Bones 39-42: Right wing (root → mid → tip → end, ~7m span)
          └── Bones 43-46: Left wing (mirror of right)

Auxiliary Chain (Bones 52-55):
  Bone 52: Second root (physics/effects anchor)
  └── Bones 53-55: Tracking/target bones
```

### Skeleton Properties

- All bones have identity rotation and identity scale in rest pose
- All posing is done purely through translation offsets
- Wings span ~14m total, tail extends ~11.5m
- Bone 37 (lower jaw) is the facial animation bone for biting/roaring

## Channel Type Mapping (Frontier → Blender)

| MHF Channel | Hex | Blender Property | Index | Negated? | Notes |
|-------------|-----|------------------|-------|----------|-------|
| POSITION_X | 0x008 | `location` | 0 | No | Or `rotation_euler` if no rotation mask |
| POSITION_Y | 0x010 | `location` | 2 | No | Y→Z swap |
| POSITION_Z | 0x020 | `location` | 1 | No | Z→Y swap |
| ROTATION_X | 0x040 | `rotation_euler` | 0 | **Yes** | X rotation negated for coord conversion |
| ROTATION_Y | 0x080 | `rotation_euler` | 2 | No | Y→Z swap |
| ROTATION_Z | 0x100 | `rotation_euler` | 1 | No | Z→Y swap |
| SCALE_X | 0x200 | `scale` | 0 | No | |
| SCALE_Y | 0x400 | `scale` | 2 | No | Y→Z swap |
| SCALE_Z | 0x800 | `scale` | 1 | No | Z→Y swap |

## Value Conversion

- **Position:** `value * 0.01` (IMPORT_SCALE)
- **Rotation:** `value * (π / 32768)` (ROTATION_SCALE), negated for X axis
- **Scale:** `value / 32768.0` if large, else pass through
- **Tangents:** Same scaling as the corresponding transform type, including X negation

## Debugging Steps Taken

### Phase 1: "Animations only animate parts of the body"

1. Discovered 12-byte vs 8-byte bone block header mismatch
2. Fixed parser to handle both formats
3. Fixed exporter to write 12-byte blocks
4. All 214 tests passing

### Phase 2: "Model is not moving (no animation)" in Blender

1. Found `animation_data` was None — Blender requires `animation_data_create()` before setting actions
2. Fixed interactive script
3. Also corrected monster identification: em107 is Disufiroa, not Espinas (em080)

### Phase 3: "Animation feels janky, only left legs move strangely"

Investigation with diagnostic scripts:

1. **Bone diagnostic (`diagnose_anim.py`):** Confirmed all 31 animated bones have rotation values that change across frames. Discovered mirror pattern between bones 24-26 and 28-30 (identical X rotation, negated Y/Z). FCurve breakdown: 93 rotation_euler + 6 location (bones 12, 22 only).

2. **Skeleton dump (`dump_skeleton.py`):** Mapped the 56-bone hierarchy to body parts. Found two roots (0 and 52), identified all limb chains.

3. **Header decode (`decode_header.py`):** Analyzed motion file header. Found 6 tables of 100 animation offsets (3 pairs for 3 tiers). Header total = 2456 bytes before first animation block.

4. **Bone remap check (`check_bone_remap.py`):** Confirmed mesh bone_remap tables are per-mesh (for vertex weights), NOT for animation. No animation bone mapping table found.

5. **Coordinate system analysis:** Mathematically derived that Y↔Z swap requires:
   - X rotation negation: `S · Rx(θ) · S⁻¹ = Rx(-θ)`
   - Euler order change: XYZ → XZY
   - Y and Z rotations keep same sign

6. Applied negation + Euler order fix → animation became "much more dynamic"

### Phase 4: "Same limbs continue to move wildly, head/tail not animated"

1. **Bone block header analysis (`dump_bone_blocks.py`):** Confirmed bits 12-30 of bone block type are all zero — no bone ID encoded in block type.

2. **Skeleton tree analysis (`skeleton_tree.py`):** Built complete body-part map with world-space positions. Identified that head (bones 30-38) and tail (bones 47-51) are in the upper bone ID range, unreachable by sequential 0-30 mapping.

3. **Tier verification (`verify_tiers.py`):** Confirmed 3-tier structure:
   - Tier 0 (16 bones, offset 0): lower body
   - Tier 1 (31 bones, offset 16): upper body
   - Tier 2 (5 bones, offset 47): tail

4. Applied tier bone offset → "body shows clear animations"

5. Merged all 3 tiers into single actions → full-body animation working

### Phase 5: Remaining Issues (Open)

- **Wing contortion:** Wings appear to contort inward. Possible causes: incorrect rotation sign on a specific axis, bone rest-pose orientation not matching, or Euler gimbal lock at extreme angles.
- **Rotation accuracy:** "The rotations are still [off]" — may need further investigation of the Euler order assumption (MHF's actual Euler convention is unconfirmed).

## Open Questions

### MHF Euler Convention

The fix assumes MHF uses XYZ Euler order. The correct Blender order (XZY) was derived from this assumption. If MHF uses a different order (ZYX, YXZ, etc.), the Euler conversion would need adjustment. Confirming this requires disassembly of the game's animation playback code.

### Animation Slot Correspondence Across Tiers

The current approach assumes animation slot N is the same across all 3 tiers (e.g., slot 73 in tier 0, 1, and 2 all belong to "attack_heavy"). This is inferred from the index table structure but not definitively confirmed. The index table header has 6 sub-tables (3 pairs) that may encode variants or priorities.

### Index Table Header Format

The motion file header contains 6 tables of 100 uint32 offset entries. These form 3 pairs (one per tier). Each pair appears to have a primary and secondary table with overlapping slot numbers. The secondary tables may represent animation variants, blend targets, or priority levels. Not fully decoded.

### Stray Values Between Keyframe Blocks

Small integer values (1-3) appear between some keyframe blocks within a bone's data region. The parser skips these via the `pos += 4` fallback. Purpose unknown — possibly padding, interpolation mode flags, or sub-block separators.

## Testing

```bash
cd MHFrontier-Blender-Addon
python -m unittest tests.fmod.test_fmot
python -m unittest tests.fmod.test_fmot_export
python -m unittest discover -s tests/
```

The round-trip test (`TestRoundTripConsistency`) is the critical check: export → reimport must produce identical data structures.

## Blender Module Caching

When testing addon changes interactively in Blender, Python module caching prevents seeing updates. Force reload with:

```python
import sys
for mod in [n for n in list(sys.modules.keys()) if 'mhfrontier' in n]:
    del sys.modules[mod]
```
