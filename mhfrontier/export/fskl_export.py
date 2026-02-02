"""
FSKL (Frontier Skeleton) file export.

Exports skeleton data to the Frontier FSKL binary format.
"""

import struct
from typing import List

from .block_builder import BlockBuilder, HEADER_SIZE
from .blender_extractor import ExtractedBone
from ..fmod.fblock import BlockType
from ..logging_config import get_logger

_logger = get_logger("export.fskl")


# BoneBlock size: 252 bytes
# nodeID(4) + parentID(4) + leftChild(4) + rightSibling(4) + scale(16) +
# rotation(16) + position(16) + sentinel(4) + chainID(4) + reserved(184)
BONE_BLOCK_SIZE = 252


def serialize_bone_block(bone: ExtractedBone) -> bytes:
    """
    Serialize a bone to the BoneBlock binary format.

    :param bone: Extracted bone data.
    :return: 252-byte binary representation.
    """
    parts = []

    # nodeID, parentID, leftChild, rightSibling (4 int32 each)
    parts.append(struct.pack(
        "<iiii",
        bone.node_id,
        bone.parent_id,
        bone.left_child,
        bone.right_sibling,
    ))

    # scale (4 floats)
    parts.append(struct.pack("<ffff", *bone.scale))

    # rotation (4 floats)
    parts.append(struct.pack("<ffff", *bone.rotation))

    # position (4 floats)
    parts.append(struct.pack("<ffff", *bone.position))

    # sentinel (always 0xFFFFFFFF)
    parts.append(struct.pack("<I", 0xFFFFFFFF))

    # chainID
    parts.append(struct.pack("<I", bone.chain_id))

    # reserved (46 uint32 = 184 bytes of zeros)
    parts.append(b"\x00" * 184)

    return b"".join(parts)


def build_bone_block(bone: ExtractedBone) -> BlockBuilder:
    """
    Build a BONE block for a single bone.

    :param bone: Extracted bone data.
    :return: BlockBuilder containing the bone data.
    """
    builder = BlockBuilder(BlockType.BONE, count=1)
    builder.set_raw_data(serialize_bone_block(bone))
    return builder


def build_metadata_block() -> BlockBuilder:
    """
    Build the FSKL metadata block.

    This is the first child of the skeleton block with type 0x0 and count=2.
    Contains 8 bytes of data (2 uint32 values, usually both 0).

    :return: BlockBuilder for metadata.
    """
    # Type 0x0 with count=2, contains 8 bytes of zeros
    metadata = BlockBuilder(0x00000000, count=2)
    metadata.set_raw_data(struct.pack("<II", 0, 0))
    return metadata


def build_fskl_file(bones: List[ExtractedBone]) -> bytes:
    """
    Build complete FSKL file data.

    FSKL structure (matching original format):
    - SKELETON block (type 0xC0000000) as root
      - Metadata block (type 0x00000000, count=2)
      - BONE blocks (type 0x40000001, count=1 each)

    :param bones: List of extracted bones.
    :return: Complete FSKL file data.
    """
    # Count: 1 (metadata) + number of bones
    skeleton = BlockBuilder(BlockType.SKELETON, count=1 + len(bones))

    # Add metadata block first
    skeleton.add_child(build_metadata_block())

    # Sort bones by node_id and add each as a BONE block
    sorted_bones = sorted(bones, key=lambda b: b.node_id)
    for bone in sorted_bones:
        skeleton.add_child(build_bone_block(bone))

    return skeleton.serialize()


def export_fskl(filepath: str, bones: List[ExtractedBone]) -> None:
    """
    Export bones to an FSKL file.

    :param filepath: Output file path.
    :param bones: List of bones to export.
    """
    _logger.info("Exporting FSKL to %s with %d bones", filepath, len(bones))

    data = build_fskl_file(bones)

    with open(filepath, "wb") as f:
        f.write(data)

    _logger.info("FSKL export complete: %d bytes written", len(data))
