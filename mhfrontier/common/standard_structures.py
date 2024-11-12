"""Standard structures for Python."""

from collections import OrderedDict

from .pycstruct import PyCStruct


class UIntField(PyCStruct):
    def __init__(self):
        self.id = None
        fields = OrderedDict(
            [
                ("id", "uint32"),
            ]
        )
        super().__init__(fields)


class UV(PyCStruct):

    def __init__(self):
        self.u = None
        self.v = None

        fields = OrderedDict(
            [
                ("u", "float"),
                ("v", "float"),
            ]
        )
        super().__init__(fields)


class Vect3(PyCStruct):
    def __init__(self):
        self.x = None
        self.y = None
        self.z = None
        fields = OrderedDict([("x", "float"), ("y", "float"), ("z", "float")])

        super().__init__(fields)


class Vect4(PyCStruct):

    def __init__(self):
        self.x = None
        self.y = None
        self.z = None
        self.w = None
        fields = OrderedDict(
            [
                ("x", "float"),
                ("y", "float"),
                ("z", "float"),
                ("w", "float"),
            ]
        )
        super().__init__(fields)


class VertexId(PyCStruct):

    def __init__(self):
        self.id = None
        fields = OrderedDict(
            [
                ("id", "uint32"),
            ]
        )
        super().__init__(fields)


class TrisTrip(PyCStruct):

    def __init__(self):
        self.count = None
        self.vertices = None
        fields = OrderedDict(
            [
                ("count", "uint32"),
            ]
        )
        super().__init__(fields)

    def marshall(self, data):
        super().marshall(data)
        self.vertices = [VertexId() for _ in range(self.count & 0xFFFFFFF)]
        for v in self.vertices:
            v.marshall(data)


class Weight(PyCStruct):

    def __init__(self):
        self.boneID = None
        self.weightValue = None
        fields = OrderedDict(
            [
                ("boneID", "uint32"),
                ("weightValue", "float"),
            ]
        )
        super().__init__(fields)


class WeightData(PyCStruct):

    def __init__(self):
        self.count = None
        self.weights = None
        fields = OrderedDict(
            [
                ("count", "uint32"),
            ]
        )
        super().__init__(fields)

    def marshall(self, data):
        super().marshall(data)
        self.weights = [Weight() for _ in range(self.count)]
        for w in self.weights:
            w.marshall(data)

    def pretty_print(self, base=0):
        """Disables printing."""
        pass


class BoneBlock(PyCStruct):

    def __init__(self):
        self.nodeID = None
        self.parentID = None
        self.leftChild = None
        self.rightSibling = None
        self.vec1 = None
        self.vec2 = None
        self.posVec = None
        self.null = None
        self.chainID = None
        self.unkn2 = None
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
        super().__init__(fields)

    def pretty_print(self, indent=0):
        pass


class TextureData(PyCStruct):
    def __init__(self):
        self.imageID = None
        self.width = None
        self.height = None
        self.unkn = None

        fields = OrderedDict(
            [
                ("imageID", "uint32"),
                ("width", "uint32"),
                ("height", "uint32"),
                ("unkn", "byte[244]"),
            ]
        )
        super().__init__(fields)


class FBlockHeader(PyCStruct):

    def __init__(self):
        self.type = None
        self.count = None
        self.size = None
        fields = OrderedDict(
            [
                ("type", "uint32"),
                ("count", "int32"),
                ("size", "uint32"),
            ]
        )
        super().__init__(fields)


class MaterialHeader(PyCStruct):

    def __init__(self):
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
        super().__init__(fields)


class MaterialChannelMapping(PyCStruct):
    def __init__(self, blocksize):
        self.unkn = None
        self.TextureLinkDif = None
        if blocksize > 272:
            fields = OrderedDict(
                [
                    ("unkn", "uint32[%s]" % (blocksize - 80)),
                    ("TextureLinkDif", "uint32"),
                    ("TextureLinkNor", "uint32"),
                    ("TextureLinkSpe", "uint32"),
                ]
            )
        else:
            fields = OrderedDict(
                [
                    ("unkn", "byte[%s]" % (blocksize - 72)),
                    ("TextureLinkDif", "uint32"),
                ]
            )

        # May not be set if blocksize below 272
        self.TextureLinkNor = None
        self.TextureLinkSpe = None
        super().__init__(fields)


class TextureIndex(PyCStruct):

    def __init__(self):
        self.index = None
        fields = OrderedDict([("index", "uint32")])
        super().__init__(fields)


class MaterialData(PyCStruct):

    def __init__(self):
        self.unkn3 = None
        self.unkn6 = None
        self.unkn7 = None
        self.float4 = None
        self.unkn8 = None
        self.unkn9 = None
        self.textureCount = None
        self.unkn = None
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

        # Supplementary property
        self.textureIndices = None
        super().__init__(fields)

    def marshall(self, data):
        super().marshall(data)
        self.textureIndices = [TextureIndex() for _ in range(self.textureCount)]
        for texture in self.textureIndices:
            texture.marshall(data)


class InitData(PyCStruct):
    """Simple structure containing 32 bits of data."""

    def __init__(self):
        self.data = None
        fields = OrderedDict([("data", "uint32")])
        super().__init__(fields)
