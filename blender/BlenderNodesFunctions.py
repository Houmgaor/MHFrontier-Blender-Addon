# -*- coding: utf-8 -*-
"""
Created on Mon Dec  2 00:15:34 2019

@author: AsteriskAmpersand
"""
import bpy


def set_location(node, location):
    x, y = location
    node.location = (x - 14) * 100, -y * 100


def create_tex_node(node_tree, color, texture, name):
    """
    setup scheme from https://i.stack.imgur.com/cdRIK.png
    """
    base_type = "ShaderNodeTexImage"
    node = node_tree.nodes.new(type=base_type)
    if bpy.app.version >= (2, 8):
        # Blender 2.8
        node.image = texture
        node.image.colorspace_settings.is_data = color == "NONE"
    else:
        # Blender <2.8
        node.color_space = color
        node.image = texture
    node.name = name
    return node


def material_setup(blender_obj, *_args):
    if "material" in blender_obj.data:
        mat_name = blender_obj.data["material"].replace("\x00", "")
    else:
        mat_name = "RenderMaterial"
    bpy.context.scene.render.engine = 'CYCLES'
    if mat_name in bpy.data.materials:
        blender_obj.data.materials.append(bpy.data.materials[mat_name])
        return None
    mat = bpy.data.materials.new(name=mat_name)
    blender_obj.data.materials.append(mat)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    for node in nodes:
        nodes.remove(node)
    return mat.node_tree


def principled_setup(node_tree):
    bsdf_node = node_tree.nodes.new(type="ShaderNodeBsdfPrincipled")
    set_location(bsdf_node, (6, 0))
    bsdf_node.name = "Principled BSDF"
    end_node = bsdf_node
    diffuse_node = yield
    if diffuse_node:
        transparent_node = node_tree.nodes.new(type="ShaderNodeBsdfTransparent")
        set_location(transparent_node, (6, 7))
        alpha_mixer_node = node_tree.nodes.new(type="ShaderNodeMixShader")
        set_location(alpha_mixer_node, (10, 1))
        node_tree.links.new(diffuse_node.outputs[0], bsdf_node.inputs[0])
        node_tree.links.new(diffuse_node.outputs[1], alpha_mixer_node.inputs[0])
        node_tree.links.new(transparent_node.outputs[0], alpha_mixer_node.inputs[1])

        node_tree.links.new(end_node.outputs[0], alpha_mixer_node.inputs[2])

        end_node = alpha_mixer_node
    normal_node = yield
    if normal_node:
        node_tree.links.new(normal_node.outputs[0], bsdf_node.inputs["Normal"])
    specular_node = yield
    if specular_node:
        node_tree.links.new(specular_node.outputs[0], bsdf_node.inputs["Specular"])
    yield
    yield end_node


def diffuse_setup(node_tree, texture, *_args):
    """Create DiffuseTexture"""
    diffuse_node = create_tex_node(node_tree, "COLOR", texture, "Diffuse Texture")
    set_location(diffuse_node, (0, 0))
    return diffuse_node


def normal_setup(node_tree, texture, *_args):
    """Create NormalMapData"""
    normal_node = create_tex_node(node_tree, "NONE", texture, "Normal Texture")
    set_location(normal_node, (0, 6))
    # Create NormalMapNode
    normalmap_node = node_tree.nodes.new(type="ShaderNodeNormalMap")
    normalmap_node.name = "Normal Map"
    set_location(normalmap_node, (4, 6))
    # Plug Normal Data to Node (color -> color)
    node_tree.links.new(normal_node.outputs[0], normalmap_node.inputs[1])
    return normalmap_node


def specular_setup(node_tree, texture, *_args):
    """Create SpecularityMaterial"""
    specular_node = create_tex_node(node_tree, "NONE", texture, "Specular Texture")
    set_location(specular_node, (0, 3))
    # Create RGB Curves
    curve_node = node_tree.nodes.new(type="ShaderNodeRGBCurve")
    curve_node.name = "Specular Curve"
    set_location(curve_node, (2, 1))
    # Plug Specularity Color to RGB Curves (color -> color)
    node_tree.links.new(specular_node.outputs[0], curve_node.inputs[0])
    return curve_node


def emission_setup(_node_tree, _texture, *_args):
    """Commented out, it's not really possible to work withit without the parameters"""
    return ""


def rmt_setup(node_tree, texture, *_args):
    """
    Create RMTMap.

    setup scheme from https://i.stack.imgur.com/TdK1W.png +
    https://i.stack.imgur.com/40vbG.jpg
    """
    rmtNode = create_tex_node(node_tree, "COLOR", texture, "RMT Texture")
    set_location(rmtNode, (0, 3))
    #Create Separate RGB
    splitterNode = node_tree.nodes.new(type="ShaderNodeSeparateRGB")
    splitterNode.name = "RMT Splitter"
    set_location(splitterNode, (2, 1))
    #Create Metallicness
    #Create Roughness - Create InvertNode
    inverterNode = node_tree.nodes.new(type="ShaderNodeInvert")
    inverterNode.name = "Roughness Inverter"
    set_location(inverterNode, (4, 2))
    #Tex To Splitter
    node_tree.links.new(rmtNode.outputs[0], splitterNode.inputs[0])
    #Splitter to Inverter
    node_tree.links.new(splitterNode.outputs[0], inverterNode.inputs[0])
    return inverterNode, splitterNode, rmtNode


def fur_setup(node_tree, texture, *_args):
    # TODO - Actually Finish This
    # Create FMMap
    fmNode = create_tex_node(node_tree, "COLOR", texture, "FM Texture")
    # Separate RGB
    splitterNode = node_tree.nodes.new(type="ShaderNodeSeparateRGB")
    splitterNode.name = "FM Splitter"
    node_tree.links.new(fmNode.outputs[0], splitterNode.inputs[0])
    # Create Input
    inputNode = node_tree.nodes.new(type="NodeReroute")
    inputNode.name = "Reroute Node"
    # Create Roughness - Create InvertNode
    inverterNode = node_tree.nodes.new(type="ShaderNodeInvert")
    inverterNode.name = "Fur Inverter"
    node_tree.links.new(splitterNode.outputs[1], inverterNode.inputs[1])
    # Create HairBSDF
    transmission_node = node_tree.nodes.new(type="ShaderNodeHairBSDF")
    transmission_node.component = "TRANSMISSION"
    reflectionNode = node_tree.nodes.new(type="ShaderNodeHairBSDF")
    reflectionNode.component = "REFLECTION"
    for targetNode in [transmission_node, reflectionNode]:
        node_tree.links.new(inputNode.outputs[0], targetNode.inputs[0])
        node_tree.links.new(splitterNode.outputs[0], targetNode.inputs[1])
        node_tree.links.new(splitterNode.outputs[1], targetNode.inputs[2])
        node_tree.links.new(inverterNode.outputs[0], targetNode.inputs[3])
    hairNode = node_tree.nodes.new(type="ShaderNodeMixShader")
    node_tree.links.new(transmission_node.outputs[0], hairNode.inputs[1])
    node_tree.links.new(reflectionNode.outputs[0], hairNode.inputs[2])
    return


def finish_setup(node_tree, end_node):
    output_node = node_tree.nodes.new(type="ShaderNodeOutputMaterial")
    node_tree.links.new(end_node.outputs[0], output_node.inputs[0])
    return
