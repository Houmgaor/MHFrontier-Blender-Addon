# -*- coding: utf-8 -*-
"""
Created on Thu Apr 04 13:57:02 2019

@author: *&
"""

from collections import OrderedDict

from ..common.cstruct import PyCStruct
from ..common.filelike import FileLike


class Byte4(PyCStruct):
    fields = OrderedDict(
        [
            ("array", "byte[4]"),
        ]
    )


class UIntField(PyCStruct):
    fields = OrderedDict(
        [
            ("id", "uint32"),
        ]
    )


class UV(PyCStruct):
    fields = OrderedDict(
        [
            ("u", "float"),
            ("v", "float"),
        ]
    )


class Vect3(PyCStruct):
    fields = OrderedDict([("x", "float"), ("y", "float"), ("z", "float")])


position = Vect3
normal = Vect3


class Vect4(PyCStruct):
    fields = OrderedDict(
        [
            ("x", "float"),
            ("y", "float"),
            ("z", "float"),
            ("w", "float"),
        ]
    )


tangent = Vect4


class VertexId(PyCStruct):
    fields = OrderedDict(
        [
            ("id", "uint32"),
        ]
    )


class TrisTrip(PyCStruct):
    fields = OrderedDict(
        [
            ("count", "uint32"),
        ]
    )

    def marshall(self, data):
        super().marshall(data)
        self.vertices = [VertexId() for i in range(self.count & 0xFFFFFFF)]
        [v.marshall(data) for v in self.vertices]


class Weight(PyCStruct):
    fields = OrderedDict(
        [
            ("boneID", "uint32"),
            ("weightValue", "float"),
        ]
    )


class WeightData(PyCStruct):
    fields = OrderedDict(
        [
            ("count", "uint32"),
        ]
    )

    def marshall(self, data):
        super().marshall(data)
        self.weights = [Weight() for i in range(self.count)]
        [w.marshall(data) for w in self.weights]

    def pretty_print(self, base=""):
        # name = type(self).__name__
        # print(base+name)
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


class TextureData(PyCStruct):
    fields = OrderedDict(
        [
            ("imageID", "uint32"),
            ("width", "uint32"),
            ("height", "uint32"),
            ("unkn", "byte[244]"),
        ]
    )


class FBlockHeader(PyCStruct):
    fields = OrderedDict(
        [
            ("type", "uint32"),
            ("count", "int32"),
            ("size", "uint32"),
        ]
    )


class FBlock:
    def __init__(self, parent=None):
        self.Header = FBlockHeader()
        self.Data = None
        self.Parent = parent

    def marshall(self, data):
        self.Header.marshall(data)
        sub_data = FileLike(data.read(self.Header.size - len(self.Header)))
        self.Data = [self.get_type() for _ in range(self.Header.count)]
        [datum.marshall(sub_data) for datum in self.Data]

    def pretty_print(self, base=""):
        name = type(self.get_type()).__name__
        print(f"{base}{name}: {self.Header.count} \t{hex(self.Header.type)}")
        for datum in self.Data:
            datum.pretty_print(base + "\t")

    def get_type(self):
        return self.type_lookup(self.Header.type)()

    @staticmethod
    def type_lookup(value):
        types = {
            0x00020000: InitBlock,
            0x00000001: FileBlock,
            0x00000002: MainBlock,
            0x00000004: ObjectBlock,
            0x00000005: FaceBlock,
            0x00000009: MaterialBlock,
            0x0000000A: TextureBlock,
            0xC0000000: SkeletonBlock,
            0x40000001: BoneBlock,
            0x00030000: TrisStripsData,
            0x00040000: TrisStripsData,
            0x00050000: MaterialList,
            0x00060000: MaterialMap,
            0x00070000: VertexData,
            0x00080000: NormalsData,
            0x000A0000: UVData,
            0x000B0000: RGBData,
            0x000C0000: WeightData,
            0x00100000: BoneMapData,
        }
        return types[value] if value in types else UnknBlock


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

    def pretty_print(self, base=""):
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


class MaterialChannelMapping(PyCStruct):
    def __init__(self, blocksize):
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
        super().__init__()


class TextureIndex(PyCStruct):
    fields = OrderedDict([("index", "uint32")])


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

    def marshall(self, data):
        super().marshall(data)
        self.textureIndices = [TextureIndex() for i in range(self.textureCount)]
        list(map(lambda x: x.marshall(data), self.textureIndices))

    """
    def marshall(self,data):
        self.Header = materialHeader()
        self.Header.marshall(data)
        self.Channels = materialChannelMapping(self.Header.blockSize)
        self.Channels.marshall(data)
        return self"""


class TextureBlock(SimpleFBlock):
    ftype = TextureData


class MaterialBlock(SimpleFBlock):
    ftype = MaterialData


class InitData(PyCStruct):
    fields = {"data": "uint32"}


class InitBlock(FBlock):
    def marshall(self, data):
        self.Data = InitData()
        self.Data.marshall(data)

    def pretty_print(self, base=""):
        pass


class UnknBlock(FBlock):
    def marshall(self, data):
        self.Data = data

    def pretty_print(self, base=""):
        pass


class DataContainer:
    def marshall(self, data):
        self.Data = self.dataType()
        self.Data.marshall(data)

    def pretty_print(self, base=""):
        # name = type(self).__name__
        # print(base+name)
        pass


class TrisStripsData(DataContainer):
    dataType = TrisTrip


class ByteArrayData(DataContainer):
    dataType = Byte4


class MaterialList(DataContainer):
    dataType = UIntField


class MaterialMap(DataContainer):
    dataType = UIntField


class BoneMapData(DataContainer):
    dataType = UIntField


class VertexData(DataContainer):
    dataType = position


class NormalsData(DataContainer):
    dataType = normal


class UVData(DataContainer):
    dataType = UV


class RGBData(DataContainer):
    dataType = Vect4
