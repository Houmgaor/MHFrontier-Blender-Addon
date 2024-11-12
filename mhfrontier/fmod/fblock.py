"""
Definition of frontier blocks from Frontier files.

Created on Thu Apr 04 13:57:02 2019

@author: *&
"""

import abc

from ..common import filelike
from ..common import standard_structures as sstructs
from ..common import data_containers as containers


class FBlock(abc.ABC):
    """
    Frontier data Block.

    Generic block with a recursive structure.
    """

    def __init__(self, parent=None):
        """Define block from parent with empty data."""

        self.header = sstructs.FBlockHeader()
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


def fblock_type_lookup(value):
    """
    Return the block corresponding to value.

    :param int value: Block identifier.
    """

    if value == 0x00020000:
        return InitBlock
    if value == 0x00000001:
        return FileBlock
    if value == 0x00000002:
        return MainBlock
    if value == 0x00000004:
        return ObjectBlock
    if value == 0x00000005:
        return FaceBlock
    if value == 0x00000009:
        return MaterialBlock
    if value == 0x0000000A:
        return TextureBlock
    if value == 0xC0000000:
        return SkeletonBlock
    if value == 0x40000001:
        return sstructs.BoneBlock
    if value == 0x00030000:
        return containers.TrisStripsData
    if value == 0x00040000:
        return containers.TrisStripsData
    if value == 0x00050000:
        return containers.MaterialList
    if value == 0x00060000:
        return containers.MaterialMap
    if value == 0x00070000:
        return containers.VertexData
    if value == 0x00080000:
        return containers.NormalsData
    if value == 0x000A0000:
        return containers.UVData
    if value == 0x000B0000:
        return containers.RGBData
    if value == 0x000C0000:
        return sstructs.WeightData
    if value == 0x00100000:
        return containers.BoneMapData
    return UnknBlock


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

    def __init__(self, ftype):
        self.ftype = ftype
        super().__init__()

    def get_type(self):
        return self.ftype()

    def pretty_print(self, indents=0):
        pass


class TextureBlock(SimpleFBlock):
    def __init__(self):
        super().__init__(sstructs.TextureData)


class MaterialBlock(SimpleFBlock):
    def __init__(self):
        super().__init__(sstructs.MaterialData)


class InitBlock(FBlock):
    def marshall(self, data):
        self.data = sstructs.InitData()
        self.data.marshall(data)

    def pretty_print(self, indents=0):
        pass


class UnknBlock(FBlock):
    def marshall(self, data):
        self.data = data

    def pretty_print(self, indents=0):
        pass
