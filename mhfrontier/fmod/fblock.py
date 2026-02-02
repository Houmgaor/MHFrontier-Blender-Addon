"""
Definition of frontier blocks from Frontier files.

Created on Thu Apr 04 13:57:02 2019

@author: *&
"""

import abc

from ..common import data_containers, filelike, standard_structures


class FBlock(abc.ABC):
    """
    Frontier data Block.

    Generic block with a recursive structure.
    """

    def __init__(self, parent=None):
        """Define block from parent with empty data."""

        self.header = standard_structures.FBlockHeader()
        self.data = None
        self.parent = parent

    def marshall(self, data):
        """
        Assign the values to the data block.

        :param data: Data to read.
        :type data: mhfrontier.common.filelike.FileLike
        """

        self.header.marshall(data)
        # Read header only
        sub_data = filelike.FileLike(
            data.read(self.header.size - self.header.CStruct.size())
        )
        self.data = [self.get_type() for _ in range(self.header.count)]
        for datum in self.data:
            datum.marshall(sub_data)

    def pretty_print(self, indents=0):
        """
        Nice display of the block and its hierarchy in the console.

        :param int indents: Number of indentation to set.
        """
        name = type(self.get_type()).__name__
        print("\t" * indents + f"{name}: {self.header.count} \t{hex(self.header.type)}")
        for datum in self.data:
            datum.pretty_print(indents + 1)

    def get_type(self):
        return fblock_type_lookup(self.header.type)()


def _build_block_type_map():
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
BLOCK_TYPE_MAP = {}


def fblock_type_lookup(value):
    """
    Return the block class corresponding to a type ID.

    :param int value: Block type identifier.
    :return: Block class for the given type, or UnknBlock if unknown.
    """
    return BLOCK_TYPE_MAP.get(value, UnknBlock)


class FileBlock(FBlock):
    pass


class MainBlock(FBlock):
    pass


class ObjectBlock(FBlock):
    pass


class FaceBlock(FBlock):
    pass


class SkeletonBlock(FBlock):
    pass


class SimpleFBlock(FBlock):

    def __init__(self, struct_type):
        """

        :param struct_type: Structure to use
        :type struct_type: Type[mhfrontier.common.pycstruct]
        """
        self.struct_type = struct_type
        super().__init__()

    def get_type(self):
        return self.struct_type()

    def pretty_print(self, indents=0):
        pass


class TextureBlock(SimpleFBlock):
    def __init__(self):
        super().__init__(standard_structures.TextureData)


class MaterialBlock(SimpleFBlock):
    def __init__(self):
        super().__init__(standard_structures.MaterialData)


class InitBlock(FBlock):
    def marshall(self, data):
        self.data = standard_structures.InitData()
        self.data.marshall(data)

    def pretty_print(self, indents=0):
        pass


class UnknBlock(FBlock):
    def marshall(self, data):
        self.data = data

    def pretty_print(self, indents=0):
        pass


# Initialize the block type map now that all classes are defined
BLOCK_TYPE_MAP.update(_build_block_type_map())
