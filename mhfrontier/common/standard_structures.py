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
    """
    Bone transformation data in SRT (Scale-Rotation-Translation) format.

    Fields:
    - nodeID, parentID, leftChild, rightSibling: Tree structure navigation
    - scale: Local scale [scaleX, scaleY, scaleZ, 1.0] (usually identity [1,1,1,1])
    - rotation: Rotation quaternion [x, y, z, w] (usually identity [0,0,0,1])
    - position: Local translation [x, y, z, 1.0]
    - sentinel: Always 0xFFFFFFFF, unused marker
    - chainID: IK chain identifier
    - reserved: 184 bytes of padding (always zeros in analyzed files)
    """

    def __init__(self):
        self.nodeID = None
        self.parentID = None
        self.leftChild = None
        self.rightSibling = None
        self.scale = None
        self.rotation = None
        self.position = None
        self.sentinel = None
        self.chainID = None
        self.reserved = None
        fields = OrderedDict(
            [
                ("nodeID", "int32"),
                ("parentID", "int32"),
                ("leftChild", "int32"),
                ("rightSibling", "int32"),
                ("scale", "float[4]"),
                ("rotation", "float[4]"),
                ("position", "float[4]"),
                ("sentinel", "uint32"),
                ("chainID", "uint32"),
                ("reserved", "uint32[46]"),
            ]
        )
        super().__init__(fields)

    def pretty_print(self, indent=0):
        pass


class TextureData(PyCStruct):
    """
    Texture metadata header.

    Contains texture identification and dimensions. The reserved field
    (244 bytes) is typically all zeros for standard textures. Non-zero
    values have been observed in some files and may contain:
    - Mipmap count or format flags
    - Stride/pitch information for unusual aspect ratios
    - Platform-specific texture metadata

    Most textures (91% in analyzed files) have all-zero reserved data.
    """

    def __init__(self):
        self.imageID = None
        self.width = None
        self.height = None
        self.reserved = None

        fields = OrderedDict(
            [
                ("imageID", "uint32"),
                ("width", "uint32"),
                ("height", "uint32"),
                ("reserved", "byte[244]"),
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
    """
    Material header structure (UNUSED).

    This structure was reverse-engineered but is not currently used in the
    import pipeline. It may represent an alternative material format or
    version. Kept for reference and potential future use.

    Fields unkn3-unkn9 likely represent material color properties similar
    to MaterialData.
    """

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
    """
    Material texture channel mapping (UNUSED).

    Maps texture slots to material channels. Contains useful named fields:
    - TextureLinkDif: Diffuse texture index
    - TextureLinkNor: Normal map texture index (if blocksize > 272)
    - TextureLinkSpe: Specular texture index (if blocksize > 272)

    Not currently used in the import pipeline. Kept for reference.
    """

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
    """
    Material properties structure.

    Contains color and shading properties for a material:
    - ambientColor: RGB ambient light response (float[3], 0.0-1.0)
    - opacity: Material transparency/alpha (float, 0.0=transparent, 1.0=opaque)
    - diffuseColor: RGB diffuse/base color (float[3], 0.0-1.0)
    - specularColor: RGBA specular highlight color with intensity (float[4])
    - materialFlags: Render mode/blend flags (uint32)
    - shininess: Specular power/glossiness (float)
    - textureCount: Number of textures assigned to this material
    - reserved: Extended material data, mostly zeros (byte[200])
    """

    def __init__(self):
        self.ambientColor = None
        self.opacity = None
        self.diffuseColor = None
        self.specularColor = None
        self.materialFlags = None
        self.shininess = None
        self.textureCount = None
        self.reserved = None
        fields = OrderedDict(
            [
                ("ambientColor", "float[3]"),
                ("opacity", "float"),
                ("diffuseColor", "float[3]"),
                ("specularColor", "float[4]"),
                ("materialFlags", "uint32"),
                ("shininess", "float"),
                ("textureCount", "uint32"),
                ("reserved", "byte[200]"),
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
