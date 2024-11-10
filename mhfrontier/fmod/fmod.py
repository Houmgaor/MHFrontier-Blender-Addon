"""
Frontier 3D model file format utility.

Created on Fri Apr  5 23:03:36 2019

@author: AsteriskAmpersand
"""

import warnings
from itertools import cycle

from ..fmod import fblock
from ..common.filelike import FileLike


class FFaces:
    def __init__(self, face_block):
        self.faces = []
        for tris_trip_array in face_block.data:
            for tris_trip in tris_trip_array.data:
                vertices = tris_trip.data.vertices
                self.faces += [
                    [v1.id, v2.id, v3.id][:: ((w + 1) % 2) * 2 - 1]
                    for w, (v1, v2, v3) in enumerate(
                        zip(vertices[:-2], vertices[1:-1], vertices[2:])
                    )
                ]


class FUnkSing:
    def __init__(self, _unknown_singular_block):
        pass


class FTriData:
    def __init__(self, face_data_block):
        self.data = [faceElement.data for faceElement in face_data_block.data]


class FVertices:
    def __init__(self, vertex_block):
        self.vertices = [
            (vertex.data.x, vertex.data.y, vertex.data.z)
            for vertex in vertex_block.data
        ]


class FNormals:
    def __init__(self, normals_block):
        self.normals = [
            [normal.data.x, normal.data.y, normal.data.z]
            for normal in normals_block.data
        ]


class FUVs:
    def __init__(self, uv_block):
        self.uvs = [[uv.data.u, 1 - uv.data.v] for uv in uv_block.data]


class FRGB:
    def __init__(self, rgb_block):
        self.rgb = [
            [rgb.data.x, rgb.data.y, rgb.data.z, rgb.data.w] for rgb in rgb_block.data
        ]


class FWeights:
    def __init__(self, weights_block):
        groups = {}
        for vertID, weights in enumerate(weights_block.data):
            for weight in weights.weights:
                if weight.boneID not in groups:
                    groups[weight.boneID] = []
                groups[weight.boneID].append((vertID, weight.weightValue / 100))
        self.weights = groups


class FRemap:
    def __init__(self, remap_block):
        self.remapTable = []
        for data_id in remap_block.data:
            self.remapTable.append(data_id.data.id)

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
    weights = {}


class FMesh:
    """
    Create a Frontier Mesh, a single 3D model.

    It a complete model with textures, not a simple blender mesh.
    """

    def __init__(self, object_block):
        """Complete definition of the Frontier Mesh."""

        self.faces = None
        self.material_list = DummyMaterialsIndices()
        self.material_map = DummyFaceMaterials()
        self.vertices = None
        self.normals = None
        self.uvs = DummyUVs()
        self.rgb_like = None
        self.weights = DummyWeight()
        self.bone_remap = DummyRemap()
        attributes = {
            fblock.FaceBlock: "faces",
            fblock.MaterialList: "material_list",
            fblock.MaterialMap: "material_map",
            fblock.VertexData: "vertices",
            fblock.NormalsData: "normals",
            fblock.UVData: "uvs",
            fblock.RGBData: "rgb_like",
            fblock.WeightData: "weights",
            fblock.BoneMapData: "bone_remap",
            # fblock.UnknBlock: "unkn_block",
        }
        type_data = {
            fblock.FaceBlock: FFaces,
            fblock.MaterialList: FMatRemapList,
            fblock.MaterialMap: FMatPerTri,
            fblock.VertexData: FVertices,
            fblock.NormalsData: FNormals,
            fblock.UVData: FUVs,
            fblock.RGBData: FRGB,
            fblock.WeightData: FWeights,
            fblock.BoneMapData: FBoneRemap,
            # fblock.UnknBlock: "UnknBlock"
        }
        # Start assigning properties from data
        tris_trip_repetition = None
        for objectBlock in object_block.data:
            typing = fblock.FBlock.type_lookup(objectBlock.header.type)
            if typing in attributes:
                self.__setattr__(attributes[typing], type_data[typing](objectBlock))
            if typing is fblock.FaceBlock:
                tris_trip_repetition = self.calc_strip_lengths(objectBlock)
        if self.material_map is not None and tris_trip_repetition is not None:
            self.material_map = self.decompose_material_list(
                self.material_map, tris_trip_repetition
            )

    @staticmethod
    def calc_strip_lengths(face_block):
        lengths = []
        for tris_trip_array in face_block.data:
            for tris_trip in tris_trip_array.data:
                lengths.append(len(tris_trip.data.vertices) - 2)
        return lengths

    @staticmethod
    def decompose_material_list(material_list, tri_strip_counts):
        material_array = []
        for material, triangles_len in zip(material_list, tri_strip_counts):
            material_array += [material] * triangles_len
        return material_array

    def traditional_mesh_structure(self):
        """
        Format the mesh as a traditional structure.

        :return dict: Structure.
        """
        if isinstance(self.uvs, DummyUVs):
            # An actual fix is missing
            warnings.warn("No UV data found in this file. Texture won't be rendered.")
        structure = {
            "vertices": self.vertices.vertices,
            "faces": self.faces.faces,
            "normals": self.normals.normals,
            "uvs": None,
            "weights": self.weights.weights,
            "boneRemap": self.bone_remap,
            "materials": self.material_list,
            "faceMaterial": self.material_map,
        }
        if isinstance(self.uvs, FUVs):
            structure["uvs"] = self.uvs.uvs
        return structure


class FMat:
    """Load a Frontier material file."""

    def __init__(self, mat_block, textures):
        self.textureIndices = [
            textures[ix.index].data[0].imageID
            for ix in mat_block.data[0].textureIndices
        ]

    def get_diffuse(self):
        if len(self.textureIndices) >= 1:
            return self.textureIndices[0]
        return None

    def get_normal(self):
        if len(self.textureIndices) >= 2:
            return self.textureIndices[1]
        return None

    def get_specular(self):
        if len(self.textureIndices) >= 3:
            return self.textureIndices[2]
        return None


class FModel:
    """
    Load a 3D model from FMOD file.

    An FMOD file usually contains multiple files.
    """

    def __init__(self, file_path):
        """
        Load the meshes with the materials.

        :param str file_path: FMOD file to read.
        """

        with open(file_path, "rb") as modelFile:
            frontier_file = fblock.FBlock()
            frontier_file.marshall(FileLike(modelFile.read()))
        meshes = frontier_file.data[1].data
        materials = frontier_file.data[2].data
        textures = frontier_file.data[3].data
        self.mesh_parts = [FMesh(mesh) for mesh in meshes]
        self.materials = [FMat(material, textures) for material in materials]
        frontier_file.pretty_print()

    def traditional_mesh_structure(self):
        """Format each mesh part in the registered meshes."""

        return [mesh.traditional_mesh_structure() for mesh in self.mesh_parts]
