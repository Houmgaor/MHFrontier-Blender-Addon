"""
Definition of blocks from Frontier files.

Created on Thu Apr 04 13:57:02 2019

@author: *&
"""

import abc
from collections import OrderedDict

from ..common.cstruct import PyCStruct
from ..common.filelike import FileLike


class Byte4(PyCStruct):
    fields = OrderedDict(
        [
            ("array", "byte[4]"),
        ]
    )

    def __init__(self, data=None, parent=None, **kwargs):
        self.array = None
        super().__init__(data, parent, **kwargs)


class UIntField(PyCStruct):
    fields = OrderedDict(
        [
            ("id", "uint32"),
        ]
    )

    def __init__(self, data=None, parent=None, **kwargs):
        self.id = None
        super().__init__(data, parent, **kwargs)


class UV(PyCStruct):
    fields = OrderedDict(
        [
            ("u", "float"),
            ("v", "float"),
        ]
    )

    def __init__(self, data=None, parent=None, **kwargs):
        self.u = None
        self.v = None
        super().__init__(data, parent, **kwargs)


class Vect3(PyCStruct):
    fields = OrderedDict([("x", "float"), ("y", "float"), ("z", "float")])

    def __init__(self, data=None, parent=None, **kwargs):
        self.x = None
        self.y = None
        self.z = None
        super().__init__(data, parent, **kwargs)


class Vect4(PyCStruct):
    fields = OrderedDict(
        [
            ("x", "float"),
            ("y", "float"),
            ("z", "float"),
            ("w", "float"),
        ]
    )

    def __init__(self, data=None, parent=None, **kwargs):
        self.x = None
        self.y = None
        self.z = None
        self.w = None
        super().__init__(data, parent, **kwargs)


class VertexId(PyCStruct):
    fields = OrderedDict(
        [
            ("id", "uint32"),
        ]
    )

    def __init__(self):
        self.id = None
        super().__init__()


class TrisTrip(PyCStruct):
    fields = OrderedDict(
        [
            ("count", "uint32"),
        ]
    )

    def __init__(self, data=None, parent=None, **kwargs):
        self.count = None
        self.vertices = None
        super().__init__(data, parent, **kwargs)

    def marshall(self, data):
        super().marshall(data)
        self.vertices = [VertexId() for _ in range(self.count & 0xFFFFFFF)]
        for v in self.vertices:
            v.marshall(data)


class Weight(PyCStruct):
    fields = OrderedDict(
        [
            ("boneID", "uint32"),
            ("weightValue", "float"),
        ]
    )

    def __init__(self):
        self.boneID = None
        self.weightValue = None
        super().__init__()


class WeightData(PyCStruct):
    fields = OrderedDict(
        [
            ("count", "uint32"),
        ]
    )

    def __init__(self, data=None, parent=None, **kwargs):
        self.count = None
        self.weights = None
        super().__init__(data, parent, **kwargs)

    def marshall(self, data):
        super().marshall(data)
        self.weights = [Weight() for _ in range(self.count)]
        for w in self.weights:
            w.marshall(data)

    def pretty_print(self, base=0):
        """Disables printing."""
        pass


class BoneBlock(PyCStruct):
    fields = OrderedDict(
        [
            ("nodeID", "int32"),
            ("parentID", "int32"),
            ("leftChild", "int32"),
            ("rightSibling", "int32"),
            ("vec1", "float[4]"),
            ("vec2", "float[4]"),
            ("posVec", "float[4]"),
            ("null", "uint32"),
            ("chainID", "uint32"),
            ("unkn2", "uint32[46]"),
        ]
    )

    def __init__(self, data=None, parent=None, **kwargs):
        self.nodeID = None
        self.parentID = None
        self.leftChild = None
        self.rightSibling = None
        self.vec1 = None
        self.vec2 = None
        self.poseVec = None
        self.null = None
        self.chainID = None
        self.unkn2 = None
        super().__init__(data, parent, **kwargs)

    def pretty_print(self, indent=0):
        pass


class TextureData(PyCStruct):
    fields = OrderedDict(
        [
            ("imageID", "uint32"),
            ("width", "uint32"),
            ("height", "uint32"),
            ("unkn", "byte[244]"),
        ]
    )

    def __init__(self, data=None, parent=None, **kwargs):
        self.imageID = None
        self.width = None
        self.height = None
        self.unkn = None
        super().__init__(data, parent, **kwargs)


class FBlockHeader(PyCStruct):
    fields = OrderedDict(
        [
            ("type", "uint32"),
            ("count", "int32"),
            ("size", "uint32"),
        ]
    )

    def __init__(self):
        self.type = None
        self.count = None
        self.size = None
        super().__init__()


class FBlock:
    """
    Frontier data Block.

    Generic block with a recursive structure.
    """

    def __init__(self, parent=None):
        """Define block from parent with empty data."""

        self.header = FBlockHeader()
        self.data = None
        self.parent = parent

    def marshall(self, data):
        """
        Assign the values to the data block.

        :param data: Data to read.
        :type data: mhfrontier.common.filelike.FileLike
        """

        self.header.marshall(data)
        sub_data = FileLike(data.read(self.header.size - len(self.header)))
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
        return BoneBlock
    if value == 0x00030000:
        return TrisStripsData
    if value == 0x00040000:
        return TrisStripsData
    if value == 0x00050000:
        return MaterialList
    if value == 0x00060000:
        return MaterialMap
    if value == 0x00070000:
        return VertexData
    if value == 0x00080000:
        return NormalsData
    if value == 0x000A0000:
        return UVData
    if value == 0x000B0000:
        return RGBData
    if value == 0x000C0000:
        return WeightData
    if value == 0x00100000:
        return BoneMapData
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
    def get_type(self):
        return self.ftype()

    def pretty_print(self, indents=0):
        pass


class MaterialHeader(PyCStruct):
    fields = OrderedDict(
        [
            ("unkn1", "uint32"),
            ("unkn2", "uint32"),
            ("blockSize", "uint32"),
            ("unkn3", "float"),
            ("unkn4", "float"),
            ("unkn5", "float"),
            ("unkn6", "float"),
            ("unkn7", "float"),
            ("unkn8", "float"),
            ("unkn9", "float"),
            ("float0", "float"),
            ("float1", "float"),
            ("float2", "float"),
            ("float3", "float"),
            ("textureCount", "uint32"),
            ("unkn11", "float"),
            ("unkn12", "uint32"),
        ]
    )

    def __init__(self, data=None, parent=None, **kwargs):
        self.unkn1 = None
        self.unkn2 = None
        self.blockSize = None
        self.unkn3 = None
        self.unkn4 = None
        self.unkn5 = None
        self.unkn6 = None
        self.unkn7 = None
        self.unkn8 = None
        self.unkn9 = None
        self.float0 = None
        self.float1 = None
        self.float2 = None
        self.float3 = None
        self.textureCount = None
        self.unkn11 = None
        self.unkn12 = None
        super().__init__(data, parent, **kwargs)


class MaterialChannelMapping(PyCStruct):
    def __init__(self, blocksize):
        self.unkn = None
        self.TextureLinkDif = None
        if blocksize > 272:
            self.fields = OrderedDict(
                [
                    ("unkn", "uint32[%s]" % (blocksize - 80)),
                    ("TextureLinkDif", "uint32"),
                    ("TextureLinkNor", "uint32"),
                    ("TextureLinkSpe", "uint32"),
                ]
            )
        else:
            self.fields = OrderedDict(
                [
                    ("unkn", "byte[%s]" % (blocksize - 72)),
                    ("TextureLinkDif", "uint32"),
                ]
            )

        # May not be set if blocksize below 272
        self.TextureLinkNor = None
        self.TextureLinkSpe = None
        super().__init__()


class TextureIndex(PyCStruct):
    fields = OrderedDict([("index", "uint32")])

    def __init__(self):
        self.index = None
        super().__init__()


class MaterialData(PyCStruct):
    fields = OrderedDict(
        [
            # ("unkn1" , "uint32"),
            # ("unkn2" , "uint32"),
            # ("blockSize" , "uint32"),
            ("unkn3", "float[3]"),
            ("unkn6", "float"),
            ("unkn7", "float[3]"),
            ("float4", "float[4]"),
            ("unkn8", "uint32"),
            ("unkn9", "float"),
            ("textureCount", "uint32"),
            ("unkn", "byte[200]"),
        ]
    )

    def __init__(self, data=None, parent=None, **kwargs):
        self.unkn3 = None
        self.unkn6 = None
        self.unkn7 = None
        self.float4 = None
        self.unkn8 = None
        self.unkn9 = None
        self.textureCount = None
        self.unkn = None

        # Supplementary property
        self.textureIndices = None
        super().__init__(data, parent, **kwargs)

    def marshall(self, data):
        super().marshall(data)
        self.textureIndices = [TextureIndex() for _ in range(self.textureCount)]
        for texture in self.textureIndices:
            texture.marshall(data)


class TextureBlock(SimpleFBlock):
    ftype = TextureData


class MaterialBlock(SimpleFBlock):
    ftype = MaterialData


class InitData(PyCStruct):
    fields = {"data": "uint32"}

    def __init__(self):
        self.data = None
        super().__init__()


class InitBlock(FBlock):
    def marshall(self, data):
        self.data = InitData()
        self.data.marshall(data)

    def pretty_print(self, indents=0):
        pass


class UnknBlock(FBlock):
    def marshall(self, data):
        self.data = data

    def pretty_print(self, indents=0):
        pass


class DataContainer(abc.ABC):
    """Simple data container system."""

    def __init__(self, data_type):
        """
        Associate a data type.

        :param data_type: Data structure to use.
        :type data_type: Type[mhfrontier.fmod.fblock.PyCStruct]
        """
        self.dataType = data_type
        self.data = self.dataType()

    def marshall(self, data):
        self.data.marshall(data)

    def pretty_print(self, indents=0):
        pass


class TrisStripsData(DataContainer):

    def __init__(self):
        super().__init__(TrisTrip)


class ByteArrayData(DataContainer):

    def __init__(self):
        super().__init__(Byte4)


class MaterialList(DataContainer):

    def __init__(self):
        super().__init__(UIntField)


class MaterialMap(DataContainer):

    def __init__(self):
        super().__init__(UIntField)


class BoneMapData(DataContainer):

    def __init__(self):
        super().__init__(UIntField)


class VertexData(DataContainer):

    def __init__(self):
        super().__init__(Vect3)


class NormalsData(DataContainer):
    def __init__(self):
        super().__init__(Vect3)


class UVData(DataContainer):
    def __init__(self):
        super().__init__(UV)


class RGBData(DataContainer):
    def __init__(self):
        super().__init__(Vect4)
