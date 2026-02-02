"""
Definition of frontier blocks from Frontier files.

Created on Thu Apr 04 13:57:02 2019

@author: *&
"""

import abc
from typing import Any, Dict, List, Optional, Type, TYPE_CHECKING

from ..common import data_containers, filelike, standard_structures

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

    def pretty_print(self, indents: int = 0) -> None:
        """
        Print the block hierarchy to console.

        :param indents: Current indentation level.
        """
        name = type(self.get_type()).__name__
        print("\t" * indents + f"{name}: {self.header.count} \t{hex(self.header.type)}")
        for datum in self.data:
            datum.pretty_print(indents + 1)

    def get_type(self) -> Any:
        """Get an instance of the block type for this header."""
        return fblock_type_lookup(self.header.type)()


def _build_block_type_map() -> Dict[int, Type[Any]]:
    """Build the block type lookup map. Called after classes are defined."""
    return {
        # Structural blocks
        0x00000001: FileBlock,
        0x00000002: MainBlock,
        0x00000004: ObjectBlock,
        0x00000005: FaceBlock,
        0x00000009: MaterialBlock,
        0x0000000A: TextureBlock,
        0x00020000: InitBlock,
        0xC0000000: SkeletonBlock,
        # Bone data
        0x40000001: standard_structures.BoneBlock,
        # Geometry data
        0x00030000: data_containers.TrisStripsData,
        0x00040000: data_containers.TrisStripsData,
        0x00070000: data_containers.VertexData,
        0x00080000: data_containers.NormalsData,
        0x000A0000: data_containers.UVData,
        0x000B0000: data_containers.RGBData,
        0x000C0000: standard_structures.WeightData,
        # Material data
        0x00050000: data_containers.MaterialList,
        0x00060000: data_containers.MaterialMap,
        0x00100000: data_containers.BoneMapData,
    }


# Initialized after class definitions (see end of module)
BLOCK_TYPE_MAP: Dict[int, Type[Any]] = {}


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

    def pretty_print(self, indents: int = 0) -> None:
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

    def pretty_print(self, indents: int = 0) -> None:
        """Init blocks don't print their contents."""
        pass


class UnknBlock(FBlock):
    """Unknown block type - stores raw data."""

    def marshall(self, data: "FileLike") -> None:
        """Store raw data without parsing."""
        self.data = data

    def pretty_print(self, indents: int = 0) -> None:
        """Unknown blocks don't print their contents."""
        pass


# Initialize the block type map now that all classes are defined
BLOCK_TYPE_MAP.update(_build_block_type_map())
