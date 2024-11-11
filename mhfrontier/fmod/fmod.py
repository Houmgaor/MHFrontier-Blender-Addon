"""
Frontier 3D model file format utility.

Created on Fri Apr  5 23:03:36 2019

@author: AsteriskAmpersand
"""

import warnings

from ..fmod import fblock
from ..common.filelike import FileLike


def frontier_faces(face_block):
    """Builds faces from Frontier file."""

    faces = []
    for tris_trip_array in face_block.data:
        for tris_trip in tris_trip_array.data:
            vertices = tris_trip.data.vertices
            faces += [
                [v1.id, v2.id, v3.id][:: ((w + 1) % 2) * 2 - 1]
                for w, (v1, v2, v3) in enumerate(
                    zip(vertices[:-2], vertices[1:-1], vertices[2:])
                )
            ]
    return faces


def frontier_unknown_singular(_unknown_singular_block):
    pass


def frontier_triangles_data(face_data_block):
    """Triangles data."""
    return [faceElement.data for faceElement in face_data_block.data]


def frontier_vertices(vertex_block):
    """Vertices definition."""
    return [
        (vertex.data.x, vertex.data.y, vertex.data.z) for vertex in vertex_block.data
    ]


def frontier_normals(normals_block):
    """Normals definition."""
    return [
        [normal.data.x, normal.data.y, normal.data.z] for normal in normals_block.data
    ]


def frontier_uvs(uv_block):
    """UV map."""
    return [[uv.data.u, 1 - uv.data.v] for uv in uv_block.data]


def frontier_rgb(self, rgb_block):
    """Vertices RGB data."""
    self.rgb = [
        [rgb.data.x, rgb.data.y, rgb.data.z, rgb.data.w] for rgb in rgb_block.data
    ]


def frontier_weights(weights_block):
    """Assign weights to the data."""

    groups = {}
    for vertID, weights in enumerate(weights_block.data):
        for weight in weights.weights:
            if weight.boneID not in groups:
                groups[weight.boneID] = []
            groups[weight.boneID].append((vertID, weight.weightValue / 100))
    return groups


def frontier_remap_block(remap_block):
    """Reorganize a block by taking its data."""

    return [data_id.data.id for data_id in remap_block.data]


class FMesh:
    """
    Create a Frontier Mesh, a single 3D model.

    It a complete model with textures, not a simple blender mesh.
    """

    def __init__(self, object_block):
        """
        Complete definition of the Frontier Mesh.

        :param object_block: Block to read data from.
        :type object_block: mhfrontier.fmod.fblock.MainBlock
        """

        self.faces = None
        self.material_list = []
        self.material_map = []
        self.vertices = None
        self.normals = None
        self.uvs = None
        self.rgb_like = None
        self.weights = {}
        self.bone_remap = []
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
        }
        type_data = {
            fblock.FaceBlock: frontier_faces,
            fblock.MaterialList: frontier_remap_block,
            fblock.MaterialMap: frontier_remap_block,
            fblock.VertexData: frontier_vertices,
            fblock.NormalsData: frontier_normals,
            fblock.UVData: frontier_uvs,
            fblock.RGBData: frontier_rgb,
            fblock.WeightData: frontier_weights,
            fblock.BoneMapData: frontier_remap_block,
        }
        # Start assigning properties from data
        tris_trip_repetition = None
        for objectBlock in object_block.data:
            typing = fblock.fblock_type_lookup(objectBlock.header.type)
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
        if self.uvs is None:
            # An actual fix is missing
            warnings.warn("No UV data found in this file. Texture won't be rendered.")
        structure = {
            "vertices": self.vertices,
            "faces": self.faces,
            "normals": self.normals,
            "uvs": self.uvs,
            "weights": self.weights,
            "boneRemap": self.bone_remap,
            "materials": self.material_list,
            "faceMaterial": self.material_map,
        }
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
        if not isinstance(frontier_file.data[1], fblock.MainBlock):
            raise ValueError("Second child should be " + fblock.MainBlock.__name__)
        meshes = frontier_file.data[1].data
        if not isinstance(frontier_file.data[2], fblock.MaterialBlock):
            raise ValueError("Third child should be " + fblock.MaterialBlock.__name__)
        materials = frontier_file.data[2].data
        if not isinstance(frontier_file.data[3], fblock.TextureBlock):
            raise ValueError("Third child should be " + fblock.MainBlock.__name__)
        textures = frontier_file.data[3].data
        self.mesh_parts = [FMesh(mesh) for mesh in meshes]
        self.materials = [FMat(material, textures) for material in materials]
        frontier_file.pretty_print()

    def traditional_mesh_structure(self):
        """Format each mesh part in the registered meshes."""

        return [mesh.traditional_mesh_structure() for mesh in self.mesh_parts]
