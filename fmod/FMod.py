# -*- coding: utf-8 -*-
"""
Created on Fri Apr  5 23:03:36 2019

@author: AsteriskAmpersand
"""
import warnings
from itertools import cycle

try:
    from ..fmod.FBlock import FBlock
    from ..fmod.FBlock import (
        FaceBlock,
        MaterialList,
        MaterialMap,
        VertexData,
        NormalsData,
        UVData,
        RGBData,
        WeightData,
        BoneMapData,
    )
    from ..common.FileLike import FileLike
except Exception as err:
    print("Cannot import modules in normal mode, fallback to local folder search. Error:", err)
    import sys

    sys.path.insert(0, r'..\common')
    sys.path.insert(0, r'..\fmod')
    from FBlock import FBlock
    from FBlock import (
        FaceBlock,
        MaterialList,
        MaterialMap,
        VertexData,
        NormalsData,
        UVData,
        RGBData,
        WeightData,
        BoneMapData,
    )
    from FileLike import FileLike


class FFaces:
    def __init__(self, face_block):
        self.Faces = []
        for tristripArray in face_block.Data:
            for tristrip in tristripArray.Data:
                verts = tristrip.Data.vertices
                self.Faces += [
                    [v1.id, v2.id, v3.id][::((w + 1) % 2) * 2 - 1]
                    for w, (v1, v2, v3) in enumerate(zip(verts[:-2], verts[1:-1], verts[2:]))
                ]


class FUnkSing:
    def __init__(self, _unknown_singular_block):
        pass


class FTriData:
    def __init__(self, face_data_block):
        self.Data = [faceElement.Data for faceElement in face_data_block.Data]


class FVertices:
    def __init__(self, vertex_block):
        self.Vertices = [(Vertex.Data.x, Vertex.Data.y, Vertex.Data.z) for Vertex in vertex_block.Data]


class FNormals:
    def __init__(self, normals_block):
        self.Normals = [[Normal.Data.x, Normal.Data.y, Normal.Data.z] for Normal in normals_block.Data]


class FUVs:
    def __init__(self, uv_block):
        self.UVs = [[UV.Data.u, 1 - UV.Data.v] for UV in uv_block.Data]


class FRGB:
    def __init__(self, rgb_block):
        self.RGB = [[rgb.Data.x, rgb.Data.y, rgb.Data.z, rgb.Data.w] for rgb in rgb_block.Data]


class FWeights:
    def __init__(self, weights_block):
        groups = {}
        for vertID, weights in enumerate(weights_block.Data):
            for weight in weights.weights:
                if weight.boneID not in groups:
                    groups[weight.boneID] = []
                groups[weight.boneID].append((vertID, weight.weightValue / 100))
        self.Weights = groups


class FRemap:
    def __init__(self, remap_block):
        self.remapTable = []
        for ID in remap_block.Data:
            self.remapTable.append(ID.Data.id)

    def __getitem__(self, key):
        return self.remapTable[key]

    def __iter__(self):
        return iter(self.remapTable)

    def __repr__(self):
        return str(self.remapTable)

    def __len__(self):
        return len(self.remapTable)


class FBoneRemap(FRemap):
    pass


class FMatRemapList(FRemap):
    pass


class FMatPerTri(FRemap):
    pass


class DummyRemap:
    def __getitem__(self, value):
        return value


class DummyMaterialsIndices:
    def __iter__(self):
        return iter([0])


class DummyFaceMaterials:
    def __iter__(self):
        return cycle([0])

    def __getitem__(self, value):
        return 0


class DummyUVs:
    def __iter__(self):
        return cycle([(0, 0)])

    def __getitem__(self, value):
        return 0, 0


class DummyWeight:
    Weights = {}


class FMesh:
    def __init__(self, object_block):
        self.UVs = DummyUVs()
        self.BoneRemap = DummyRemap()
        self.MaterialList = DummyMaterialsIndices()
        self.MaterialMap = DummyFaceMaterials()
        self.Weights = DummyWeight()
        objects = object_block.Data
        attributes = {
            FaceBlock: "Faces", MaterialList: "MaterialList",
            MaterialMap: "MaterialMap", VertexData: "Vertices",
            NormalsData: "Normals", UVData: "UVs",
            RGBData: "RGBLike", WeightData: "Weights",
            BoneMapData: "BoneRemap"
        }  # ,UnknBlock:"UnknBlock"}
        type_data = {
            FaceBlock: FFaces, MaterialList: FMatRemapList,
            MaterialMap: FMatPerTri, VertexData: FVertices,
            NormalsData: FNormals, UVData: FUVs,
            RGBData: FRGB, WeightData: FWeights,
            BoneMapData: FBoneRemap
        }  # ,UnknBlock:"UnknBlock"}
        for objectBlock in objects:
            typing = FBlock.type_lookup(objectBlock.Header.type)
            if typing in attributes:
                setattr(self, attributes[typing], type_data[typing](objectBlock))
            if typing is FaceBlock:
                tristrip_repetition = self.calc_strip_lengths(objectBlock)
        if hasattr(self, "MaterialMap"):
            # Not sure if the condition is necessary
            self.MaterialMap = self.decompose_material_list(self.MaterialMap, tristrip_repetition)

        """
        # Automatically assigns the map data.
        
        self.Faces = FFaces(next(objects))
        self.MaterialList = FMatList(next(objects))  # Material List
        self.MaterialMap = FMatPerTri(next(objects))  # Material Map
        self.Vertices = FVertices(next(objects))
        self.Normals = FNormals(next(objects))
        self.UVs = FUVs(next(objects))
        self.RGBLike = FRGB(next(objects))
        self.Weights = FWeights(next(objects))
        self.BoneRemap = FBoneRemap(next(objects))
        # unknownBlock
        
        """

    @staticmethod
    def calc_strip_lengths(face_block):
        lengths = []
        for tristripArray in face_block.Data:
            for tristrip in tristripArray.Data:
                lengths.append(len(tristrip.Data.vertices) - 2)
        return lengths

    @staticmethod
    def decompose_material_list(material_list, tri_strip_counts):
        material_array = []
        for m, tlen in zip(material_list, tri_strip_counts):
            material_array += [m] * tlen
        return material_array

    def traditional_mesh_structure(self):
        if isinstance(self.UVs, DummyUVs):
            # An actual fix is missing
            warnings.warn("No UV data found in this file. Texture won't be rendered.")
        return {
            "vertices": self.Vertices.Vertices,
            "faces": self.Faces.Faces,
            "normals": self.Normals.Normals,
            "uvs": self.UVs.UVs if isinstance(self.UVs, FUVs) else None,
            "weights": self.Weights.Weights,
            "boneRemap": self.BoneRemap,
            "materials": self.MaterialList,
            "faceMaterial": self.MaterialMap
        }


class FMat:
    def __init__(self, mat_block, textures):
        # print(len(MatBlock.Data[0].textureIndices))
        self.textureIndices = [textures[ix.index].Data[0].imageID for ix in mat_block.Data[0].textureIndices]

    def get_diffuse(self):
        # print(len(self.textureIndices))
        # (self.textureIndices)
        return self.textureIndices[0] if len(self.textureIndices) >= 1 else None

    def get_normal(self):
        return self.textureIndices[1] if len(self.textureIndices) >= 2 else None

    def get_specular(self):
        return self.textureIndices[2] if len(self.textureIndices) >= 3 else None


class FModel:
    def __init__(self, FilePath):
        with open(FilePath, "rb") as modelFile:
            frontier_file = FBlock()
            frontier_file.marshall(FileLike(modelFile.read()))
        meshes = frontier_file.Data[1].Data
        materials = frontier_file.Data[2].Data
        textures = frontier_file.Data[3].Data
        self.Meshparts = [FMesh(Mesh) for Mesh in meshes]
        self.Materials = [FMat(Material, textures) for Material in materials]
        frontier_file.pretty_print()

    def traditional_mesh_structure(self):
        return [mesh.traditional_mesh_structure() for mesh in self.Meshparts]
