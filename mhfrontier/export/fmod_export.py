"""
FMOD (Frontier Model) file export.

Exports 3D model data to the Frontier FMOD binary format.
"""

import struct
from typing import Dict, List, Optional, Tuple

from .block_builder import BlockBuilder, DataBlockBuilder
from .blender_extractor import ExtractedMesh, ExtractedMaterial
from ..fmod.fblock import BlockType
from ..logging_config import get_logger

_logger = get_logger("export.fmod")


def serialize_vect3(x: float, y: float, z: float) -> bytes:
    """Serialize a 3D vector."""
    return struct.pack("<fff", x, y, z)


def serialize_vect4(x: float, y: float, z: float, w: float) -> bytes:
    """Serialize a 4D vector."""
    return struct.pack("<ffff", x, y, z, w)


def serialize_uv(u: float, v: float) -> bytes:
    """Serialize UV coordinates."""
    return struct.pack("<ff", u, v)


def serialize_uint32(value: int) -> bytes:
    """Serialize a uint32."""
    return struct.pack("<I", value)


def build_vertex_block(vertices: List[Tuple[float, float, float]]) -> BlockBuilder:
    """
    Build a VERTEX block containing vertex positions.

    :param vertices: List of (x, y, z) vertex positions.
    :return: BlockBuilder for vertex data.
    """
    items = [serialize_vect3(*v) for v in vertices]
    return DataBlockBuilder(BlockType.VERTEX, items)


def build_normals_block(normals: List[Tuple[float, float, float]]) -> BlockBuilder:
    """
    Build a NORMALS block containing normal vectors.

    :param normals: List of (x, y, z) normal vectors.
    :return: BlockBuilder for normals data.
    """
    items = [serialize_vect3(*n) for n in normals]
    return DataBlockBuilder(BlockType.NORMALS, items)


def build_uv_block(uvs: List[Tuple[float, float]]) -> BlockBuilder:
    """
    Build a UV block containing texture coordinates.

    :param uvs: List of (u, v) texture coordinates.
    :return: BlockBuilder for UV data.
    """
    items = [serialize_uv(*uv) for uv in uvs]
    return DataBlockBuilder(BlockType.UV, items)


def build_rgb_block(colors: List[Tuple[float, float, float, float]]) -> BlockBuilder:
    """
    Build an RGB block containing vertex colors.

    :param colors: List of (r, g, b, a) color values.
    :return: BlockBuilder for RGB data.
    """
    items = [serialize_vect4(*c) for c in colors]
    return DataBlockBuilder(BlockType.RGB, items)


def build_weight_data(
    weights: Dict[int, List[Tuple[int, float]]],
    vertex_count: int,
) -> bytes:
    """
    Build weight data for all vertices.

    Frontier weight format per vertex:
    - count (uint32): number of weights for this vertex
    - weights: (boneID, weightValue) pairs

    :param weights: Dict mapping bone_id to list of (vertex_id, weight) tuples.
    :param vertex_count: Total number of vertices.
    :return: Serialized weight data.
    """
    # Reorganize weights by vertex
    vertex_weights: Dict[int, List[Tuple[int, float]]] = {}
    for bone_id, bone_weights in weights.items():
        for vert_id, weight_value in bone_weights:
            if vert_id not in vertex_weights:
                vertex_weights[vert_id] = []
            vertex_weights[vert_id].append((bone_id, weight_value))

    parts = []
    for vert_id in range(vertex_count):
        vert_weights = vertex_weights.get(vert_id, [])
        # Weight count
        parts.append(struct.pack("<I", len(vert_weights)))
        # Weight data
        for bone_id, weight_value in vert_weights:
            parts.append(struct.pack("<If", bone_id, weight_value))

    return b"".join(parts)


def build_weight_block(
    weights: Dict[int, List[Tuple[int, float]]],
    vertex_count: int,
) -> BlockBuilder:
    """
    Build a WEIGHT block containing vertex weight data.

    :param weights: Dict mapping bone_id to list of (vertex_id, weight) tuples.
    :param vertex_count: Total number of vertices.
    :return: BlockBuilder for weight data.
    """
    builder = BlockBuilder(BlockType.WEIGHT, count=vertex_count)
    builder.set_raw_data(build_weight_data(weights, vertex_count))
    return builder


def build_tris_strip_data(faces: List[Tuple[int, int, int]]) -> bytes:
    """
    Build triangle strip data from face list.

    For simplicity, we export as simple triangles (3 vertices per strip).
    Each strip is: count (uint32 with flag) + vertex IDs (uint32 each).

    :param faces: List of (v0, v1, v2) triangle faces.
    :return: Serialized triangle strip data.
    """
    parts = []
    for face in faces:
        # Count with high bit set to indicate triangle (not strip continuation)
        # Count of 3 for a simple triangle
        parts.append(struct.pack("<I", 3))
        # Vertex indices
        parts.append(struct.pack("<III", face[0], face[1], face[2]))
    return b"".join(parts)


def build_face_block(faces: List[Tuple[int, int, int]]) -> BlockBuilder:
    """
    Build a FACE block containing triangle strip data.

    :param faces: List of (v0, v1, v2) triangle faces.
    :return: BlockBuilder for face data.
    """
    # FACE block contains TRIS_STRIPS blocks
    face_block = BlockBuilder(BlockType.FACE)

    # Build triangle strip block (one strip per triangle for simplicity)
    tris_block = BlockBuilder(BlockType.TRIS_STRIPS_A, count=len(faces))
    tris_block.set_raw_data(build_tris_strip_data(faces))

    face_block.add_child(tris_block)
    return face_block


def build_material_list_block(material_list: List[int]) -> BlockBuilder:
    """
    Build a MATERIAL_LIST block.

    :param material_list: List of material indices.
    :return: BlockBuilder for material list.
    """
    items = [serialize_uint32(m) for m in material_list]
    return DataBlockBuilder(BlockType.MATERIAL_LIST, items)


def build_material_map_block(material_indices: List[int]) -> BlockBuilder:
    """
    Build a MATERIAL_MAP block (per-face material assignment).

    :param material_indices: Material index for each face.
    :return: BlockBuilder for material map.
    """
    items = [serialize_uint32(m) for m in material_indices]
    return DataBlockBuilder(BlockType.MATERIAL_MAP, items)


def build_bone_map_block(bone_remap: List[int]) -> BlockBuilder:
    """
    Build a BONE_MAP block.

    :param bone_remap: Bone index remapping list.
    :return: BlockBuilder for bone map.
    """
    items = [serialize_uint32(b) for b in bone_remap]
    return DataBlockBuilder(BlockType.BONE_MAP, items)


def build_object_block(mesh: ExtractedMesh) -> BlockBuilder:
    """
    Build an OBJECT block containing all mesh geometry.

    :param mesh: Extracted mesh data.
    :return: BlockBuilder for the object.
    """
    obj_block = BlockBuilder(BlockType.OBJECT)

    # Add face data
    obj_block.add_child(build_face_block(mesh.faces))

    # Add material list
    if mesh.material_list:
        obj_block.add_child(build_material_list_block(mesh.material_list))

    # Add material map (per-face material assignment)
    if mesh.material_indices:
        obj_block.add_child(build_material_map_block(mesh.material_indices))

    # Add vertex positions
    obj_block.add_child(build_vertex_block(mesh.vertices))

    # Add normals
    obj_block.add_child(build_normals_block(mesh.normals))

    # Add UVs if available
    if mesh.uvs:
        obj_block.add_child(build_uv_block(mesh.uvs))

    # Add vertex colors if available
    if mesh.vertex_colors:
        obj_block.add_child(build_rgb_block(mesh.vertex_colors))

    # Add weights if available
    if mesh.weights:
        obj_block.add_child(build_weight_block(mesh.weights, len(mesh.vertices)))

    # Add bone remap if available
    if mesh.bone_remap:
        obj_block.add_child(build_bone_map_block(mesh.bone_remap))

    return obj_block


def build_main_block(meshes: List[ExtractedMesh]) -> BlockBuilder:
    """
    Build a MAIN block containing all mesh objects.

    :param meshes: List of extracted meshes.
    :return: BlockBuilder for main block.
    """
    main_block = BlockBuilder(BlockType.MAIN)

    for mesh in meshes:
        main_block.add_child(build_object_block(mesh))

    return main_block


def serialize_material_data(material: ExtractedMaterial) -> bytes:
    """
    Serialize a MaterialData structure.

    MaterialData: ambientColor(12) + opacity(4) + diffuseColor(12) +
                  specularColor(16) + materialFlags(4) + shininess(4) +
                  textureCount(4) + reserved(200)
    Total: 256 bytes (without texture indices)

    :param material: Extracted material data.
    :return: Serialized material data.
    """
    parts = []

    # ambientColor (3 floats)
    parts.append(struct.pack("<fff", *material.ambient_color))

    # opacity (float)
    parts.append(struct.pack("<f", material.opacity))

    # diffuseColor (3 floats)
    parts.append(struct.pack("<fff", *material.diffuse_color))

    # specularColor (4 floats)
    parts.append(struct.pack("<ffff", *material.specular_color))

    # materialFlags (uint32)
    parts.append(struct.pack("<I", material.material_flags))

    # shininess (float)
    parts.append(struct.pack("<f", material.shininess))

    # textureCount (uint32)
    parts.append(struct.pack("<I", len(material.texture_ids)))

    # reserved (200 bytes)
    parts.append(b"\x00" * 200)

    # textureIndices (uint32 each)
    for tex_id in material.texture_ids:
        parts.append(struct.pack("<I", tex_id))

    return b"".join(parts)


def build_material_block(material: ExtractedMaterial) -> BlockBuilder:
    """
    Build a MATERIAL block.

    :param material: Extracted material data.
    :return: BlockBuilder for the material.
    """
    builder = BlockBuilder(BlockType.MATERIAL, count=1)
    builder.set_raw_data(serialize_material_data(material))
    return builder


def serialize_texture_data(texture_id: int, width: int = 256, height: int = 256) -> bytes:
    """
    Serialize a TextureData structure.

    TextureData: imageID(4) + width(4) + height(4) + reserved(244)
    Total: 256 bytes

    :param texture_id: Texture image ID.
    :param width: Texture width.
    :param height: Texture height.
    :return: Serialized texture data.
    """
    parts = []
    parts.append(struct.pack("<III", texture_id, width, height))
    parts.append(b"\x00" * 244)
    return b"".join(parts)


def build_texture_block(texture_id: int) -> BlockBuilder:
    """
    Build a TEXTURE block.

    :param texture_id: Texture image ID.
    :return: BlockBuilder for the texture.
    """
    builder = BlockBuilder(BlockType.TEXTURE, count=1)
    builder.set_raw_data(serialize_texture_data(texture_id))
    return builder


def build_materials_block(materials: List[ExtractedMaterial]) -> BlockBuilder:
    """
    Build a MATERIAL block containing all materials.

    :param materials: List of extracted materials.
    :return: BlockBuilder for materials block.
    """
    # MATERIAL block (type 0x9) directly contains material data
    mat_block = BlockBuilder(BlockType.MATERIAL, count=len(materials))
    for material in materials:
        mat_block.add_raw_data(serialize_material_data(material))
    return mat_block


def build_textures_block(texture_ids: List[int]) -> BlockBuilder:
    """
    Build a TEXTURE block containing all textures.

    :param texture_ids: List of texture IDs.
    :return: BlockBuilder for textures block.
    """
    # TEXTURE block (type 0xA) directly contains texture data
    tex_block = BlockBuilder(BlockType.TEXTURE, count=len(texture_ids))
    for tex_id in texture_ids:
        tex_block.add_raw_data(serialize_texture_data(tex_id))
    return tex_block


def build_fmod_file(
    meshes: List[ExtractedMesh],
    materials: List[ExtractedMaterial],
) -> bytes:
    """
    Build complete FMOD file data.

    FMOD structure (matching original format):
    - FILE block (type 0x00000001)
      - INIT block (type 0x00020000) with metadata
      - MAIN block (type 0x00000002) containing OBJECT blocks
      - MATERIAL block (type 0x00000009) with material data
      - TEXTURE block (type 0x0000000A) with texture data

    :param meshes: List of extracted meshes.
    :param materials: List of extracted materials.
    :return: Complete FMOD file data.
    """
    # Build INIT block with file metadata
    init_block = BlockBuilder(BlockType.INIT, count=1)
    init_block.set_raw_data(struct.pack("<I", 0))

    # Build MAIN block containing all mesh objects
    main_block = build_main_block(meshes)

    # Build MATERIAL block
    materials_block = build_materials_block(materials)

    # Collect all texture IDs from materials
    texture_ids = []
    for mat in materials:
        texture_ids.extend(mat.texture_ids)
    # Remove duplicates while preserving order
    seen = set()
    unique_texture_ids = []
    for tid in texture_ids:
        if tid not in seen:
            seen.add(tid)
            unique_texture_ids.append(tid)

    # Build TEXTURE block (even if empty, we need it)
    if not unique_texture_ids:
        # Add a placeholder texture ID if none exist
        unique_texture_ids = [0]
    textures_block = build_textures_block(unique_texture_ids)

    # Build top-level FILE block
    file_block = BlockBuilder(BlockType.FILE)
    file_block.add_child(init_block)
    file_block.add_child(main_block)
    file_block.add_child(materials_block)
    file_block.add_child(textures_block)

    return file_block.serialize()


def export_fmod(
    filepath: str,
    meshes: List[ExtractedMesh],
    materials: Optional[List[ExtractedMaterial]] = None,
) -> None:
    """
    Export meshes and materials to an FMOD file.

    :param filepath: Output file path.
    :param meshes: List of meshes to export.
    :param materials: List of materials (optional, will use defaults if None).
    """
    if materials is None:
        materials = [ExtractedMaterial(name="Default")]

    _logger.info(
        "Exporting FMOD to %s with %d meshes and %d materials",
        filepath,
        len(meshes),
        len(materials),
    )

    data = build_fmod_file(meshes, materials)

    with open(filepath, "wb") as f:
        f.write(data)

    _logger.info("FMOD export complete: %d bytes written", len(data))
