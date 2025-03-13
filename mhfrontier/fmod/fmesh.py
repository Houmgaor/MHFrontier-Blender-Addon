"""
Simple FMesh class.
"""

import warnings

from ..fmod import fblock
from ..common.standard_structures import WeightData
from ..common import data_containers as containers


def frontier_faces(face_block):
    """Builds faces from Frontier file."""

    faces = []
    for tris_trip_array in face_block:
        for tris_trip in tris_trip_array.data:
            vertices = tris_trip.data.vertices
            faces += [
                [v1.id, v2.id, v3.id][:: ((w + 1) % 2) * 2 - 1]
                for w, (v1, v2, v3) in enumerate(
                    zip(vertices[:-2], vertices[1:-1], vertices[2:])
                )
            ]
    return faces


def frontier_vertices(vertex_block):
    """Vertices definition."""
    return [(vertex.data.x, vertex.data.y, vertex.data.z) for vertex in vertex_block]


def frontier_normals(normals_block):
    """Normals definition."""
    return [[normal.data.x, normal.data.y, normal.data.z] for normal in normals_block]


def frontier_uvs(uv_block):
    """UV map."""
    return [[uv.data.u, 1 - uv.data.v] for uv in uv_block]


def frontier_rgb(rgb_block):
    """Vertices RGB data."""
    return [[rgb.data.x, rgb.data.y, rgb.data.z, rgb.data.w] for rgb in rgb_block]


def frontier_weights(weights_block):
    """Assign weights to the data."""
    groups = {}
    for vertID, weights in enumerate(weights_block):
        for weight in weights.weights:
            if weight.boneID not in groups:
                groups[weight.boneID] = []
            groups[weight.boneID].append((vertID, weight.weightValue / 100))
    return groups


def frontier_remap_block(remap_block):
    """Reorganize a block by taking its data."""

    return [data_id.data.id for data_id in remap_block]


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

        # Accumulate data
        face_data = None
        properties = {}
        for objectBlock in object_block.data:
            typing = fblock.fblock_type_lookup(objectBlock.header.type)
            if typing is fblock.FaceBlock:
                face_data = objectBlock.data
                properties[typing] = frontier_faces(face_data)
            elif typing is containers.MaterialList:
                properties[typing] = frontier_remap_block(objectBlock.data)
            elif typing is containers.MaterialMap:
                properties[typing] = frontier_remap_block(objectBlock.data)
            elif typing is containers.VertexData:
                properties[typing] = frontier_vertices(objectBlock.data)
            elif typing is containers.NormalsData:
                properties[typing] = frontier_normals(objectBlock.data)
            elif typing is containers.UVData:
                properties[typing] = frontier_uvs(objectBlock.data)
            elif typing is containers.RGBData:
                properties[typing] = frontier_rgb(objectBlock.data)
            elif typing is WeightData:
                properties[typing] = frontier_weights(objectBlock.data)
            elif typing is containers.BoneMapData:
                properties[typing] = frontier_remap_block(objectBlock.data)
            elif typing is fblock.UnknBlock:
                properties[typing] = objectBlock.data
            else:
                warnings.warn(f"Unknown block type {type(objectBlock)}")

        self.faces = properties[fblock.FaceBlock]
        self.material_list = properties[containers.MaterialList]
        self.material_map = None
        if containers.MaterialMap in properties and fblock.FaceBlock in properties:
            self.material_map = self.decompose_material_list(
                properties[containers.MaterialMap], self.calc_strip_lengths(face_data)
            )
        self.vertices = properties[containers.VertexData]
        self.normals = properties[containers.NormalsData]
        # Some blocks store visual effects and other properties,
        # they do not have uv or weight
        if containers.UVData in properties:
            self.uvs = properties[containers.UVData]
        else:
            warnings.warn("No UV data found for this model. Texture won't be rendered.")
            self.uvs = None
        self.rgb_like = properties[containers.RGBData]
        if WeightData in properties:
            self.weights = properties[WeightData]
        else:
            warnings.warn(
                "No weights data found for this model. Pose editing won't work."
            )
            self.weights = None
        if containers.BoneMapData in properties:
            self.bone_remap = properties[containers.BoneMapData]
        else:
            warnings.warn("No bone map data. Pose won't be available.")
            self.bone_remap = None

    @staticmethod
    def calc_strip_lengths(face_block):
        lengths = []
        for tris_trip_array in face_block:
            for tris_trip in tris_trip_array.data:
                lengths.append(len(tris_trip.data.vertices) - 2)
        return lengths

    @staticmethod
    def decompose_material_list(material_list, tri_strip_counts):
        material_array = []
        for material, triangles_len in zip(material_list, tri_strip_counts):
            material_array += [material] * triangles_len
        return material_array
