"""
Definition of frontier blocks from Frontier files.

Created on Thu Apr 04 13:57:02 2019

@author: *&
"""

import abc
import logging
from enum import IntEnum
from typing import Any, Dict, List, Optional, Type, TYPE_CHECKING

from ..common import data_containers, filelike, standard_structures


class BlockType(IntEnum):
    """
    Block type identifiers for FMOD/FSKL file format.

    Frontier uses a recursive block structure where each block has a 4-byte
    type identifier. These are grouped by category:

    Structural blocks (0x0000000X): Define file hierarchy
    Geometry blocks (0x000X0000): Contain mesh data
    Material blocks (0x000X0000): Contain material/texture data
    Special blocks (0xX0000000): Skeleton and bone data
    """

    # Structural blocks - define file hierarchy
    FILE = 0x00000001           # Top-level file container
    MAIN = 0x00000002           # Main block containing mesh data
    OBJECT = 0x00000004         # Object block containing geometry components
    FACE = 0x00000005           # Face block containing triangle strip data
    MATERIAL = 0x00000009       # Material definition block
    TEXTURE = 0x0000000A        # Texture metadata block
    INIT = 0x00020000           # Initialization block with file metadata

    # Geometry data blocks
    TRIS_STRIPS_A = 0x00030000  # Triangle strip indices (variant A)
    TRIS_STRIPS_B = 0x00040000  # Triangle strip indices (variant B)
    VERTEX = 0x00070000         # Vertex position data
    NORMALS = 0x00080000        # Vertex normal data
    UV = 0x000A0000             # Texture coordinate data
    RGB = 0x000B0000            # Vertex color data
    WEIGHT = 0x000C0000         # Bone weight data

    # Material data blocks
    MATERIAL_LIST = 0x00050000  # List of material references
    MATERIAL_MAP = 0x00060000   # Material mapping data
    BONE_MAP = 0x00100000       # Bone index remapping data

    # Skeleton blocks
    SKELETON = 0xC0000000       # Skeleton block containing bone hierarchy
    BONE = 0x40000001           # Individual bone data
    BONE_HD = 0x40000002        # Individual bone data (HD variant)

if TYPE_CHECKING:
    from ..common.filelike import FileLike


class FBlock(abc.ABC):
    """
    Frontier data Block.

    Generic block with a recursive structure.

    Attributes:
        header: Block header with type and size info.
        data: List of child blocks or data.
        parent: Parent block (or None for root).
    """

    header: "standard_structures.FBlockHeader"
    data: Optional[List[Any]]
    parent: Optional["FBlock"]

    def __init__(self, parent: Optional["FBlock"] = None) -> None:
        """
        Create a block with empty data.

        :param parent: Parent block in the hierarchy.
        """
        self.header = standard_structures.FBlockHeader()
        self.data = None
        self.parent = parent

    def marshall(self, data: "FileLike") -> None:
        """
        Parse block data from a file-like stream.

        :param data: Stream to read from.
        """
        self.header.marshall(data)
        # Read header only
        sub_data = filelike.FileLike(
            data.read(self.header.size - self.header.CStruct.size())
        )
        self.data = [self.get_type() for _ in range(self.header.count)]
        for datum in self.data:
            datum.marshall(sub_data)

    def pretty_print(
        self,
        logger: Optional[logging.Logger] = None,
        indents: int = 0,
    ) -> None:
        """
        Print the block hierarchy to console or logger.

        :param logger: Logger to use (if None, prints to stdout).
        :param indents: Current indentation level.
        """
        name = type(self.get_type()).__name__
        type_label = _format_block_type(self.header.type)
        message = "\t" * indents + f"{name}: {self.header.count} \t{type_label}"
        if logger:
            logger.debug(message)
        else:
            print(message)
        for datum in self.data:
            datum.pretty_print(logger, indents + 1)

    def get_type(self) -> Any:
        """Get an instance of the block type for this header."""
        return fblock_type_lookup(self.header.type)()


def _build_block_type_map() -> Dict[int, Type[Any]]:
    """Build the block type lookup map. Called after classes are defined."""
    return {
        # Structural blocks
        BlockType.FILE: FileBlock,
        BlockType.MAIN: MainBlock,
        BlockType.OBJECT: ObjectBlock,
        BlockType.FACE: FaceBlock,
        BlockType.MATERIAL: MaterialBlock,
        BlockType.TEXTURE: TextureBlock,
        BlockType.INIT: InitBlock,
        BlockType.SKELETON: SkeletonBlock,
        # Bone data
        BlockType.BONE: standard_structures.BoneBlock,
        BlockType.BONE_HD: standard_structures.BoneBlock,
        # Geometry data
        BlockType.TRIS_STRIPS_A: data_containers.TrisStripsData,
        BlockType.TRIS_STRIPS_B: data_containers.TrisStripsData,
        BlockType.VERTEX: data_containers.VertexData,
        BlockType.NORMALS: data_containers.NormalsData,
        BlockType.UV: data_containers.UVData,
        BlockType.RGB: data_containers.RGBData,
        BlockType.WEIGHT: standard_structures.WeightData,
        # Material data
        BlockType.MATERIAL_LIST: data_containers.MaterialList,
        BlockType.MATERIAL_MAP: data_containers.MaterialMap,
        BlockType.BONE_MAP: data_containers.BoneMapData,
    }


# Initialized after class definitions (see end of module)
BLOCK_TYPE_MAP: Dict[int, Type[Any]] = {}


def _format_block_type(type_id: int) -> str:
    """
    Format a block type ID for display.

    :param type_id: Block type identifier.
    :return: Enum name if known, otherwise hex string.
    """
    try:
        return BlockType(type_id).name
    except ValueError:
        return hex(type_id)


def fblock_type_lookup(value: int) -> Type[Any]:
    """
    Return the block class corresponding to a type ID.

    :param value: Block type identifier.
    :return: Block class for the given type, or UnknBlock if unknown.
    """
    return BLOCK_TYPE_MAP.get(value, UnknBlock)


class FileBlock(FBlock):
    """Top-level file block containing other blocks."""
    pass


class MainBlock(FBlock):
    """Main block containing mesh data."""
    pass


class ObjectBlock(FBlock):
    """Object block containing geometry components."""
    pass


class FaceBlock(FBlock):
    """Face block containing triangle strip data."""
    pass


class SkeletonBlock(FBlock):
    """Skeleton block containing bone hierarchy."""
    pass


class SimpleFBlock(FBlock):
    """Block that contains simple structured data."""

    struct_type: Type[Any]

    def __init__(self, struct_type: Type[Any]) -> None:
        """
        Create a simple block with a specific structure type.

        :param struct_type: The structure class to use for data.
        """
        self.struct_type = struct_type
        super().__init__()

    def get_type(self) -> Any:
        """Get an instance of the struct type."""
        return self.struct_type()

    def pretty_print(
        self,
        logger: Optional[logging.Logger] = None,
        indents: int = 0,
    ) -> None:
        """Simple blocks don't print their contents."""
        pass


class TextureBlock(SimpleFBlock):
    """Block containing texture metadata."""

    def __init__(self) -> None:
        super().__init__(standard_structures.TextureData)


class MaterialBlock(SimpleFBlock):
    """Block containing material data."""

    def __init__(self) -> None:
        super().__init__(standard_structures.MaterialData)


class InitBlock(FBlock):
    """Initialization block with file metadata."""

    def marshall(self, data: "FileLike") -> None:
        """Parse init data from stream."""
        self.data = standard_structures.InitData()
        self.data.marshall(data)

    def pretty_print(
        self,
        logger: Optional[logging.Logger] = None,
        indents: int = 0,
    ) -> None:
        """Init blocks don't print their contents."""
        pass


class UnknBlock(FBlock):
    """Unknown block type - stores raw data."""

    def marshall(self, data: "FileLike") -> None:
        """Store raw data without parsing."""
        self.data = data

    def pretty_print(
        self,
        logger: Optional[logging.Logger] = None,
        indents: int = 0,
    ) -> None:
        """Unknown blocks don't print their contents."""
        pass


# Initialize the block type map now that all classes are defined
BLOCK_TYPE_MAP.update(_build_block_type_map())
