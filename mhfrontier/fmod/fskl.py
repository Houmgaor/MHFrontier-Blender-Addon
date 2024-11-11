# -*- coding: utf-8 -*-
"""
Created on Sun Dec 29 21:50:00 2019

@author: AsteriskAmpersand
"""
from ..fmod import fblock
from ..common.filelike import FileLike


class FBone:
    """Simple Frontier bone definition."""

    def __init__(self, frontier_bone):
        """
        Create the bone.

        :param frontier_bone: Input bone to parse
        :type frontier_bone: mhfrontier.fmod.fblock.FBlock
        """
        source = frontier_bone.data[0]
        if not isinstance(source, fblock.BoneBlock):
            raise TypeError(
                f"Should be {fblock.BoneBlock.__name__}, " f"type is {type(source)}"
            )

        self.nodeID = frontier_bone.data[0].nodeID
        self.parentID = frontier_bone.data[0].parentID
        self.leftChild = frontier_bone.data[0].leftChild
        self.rightSibling = frontier_bone.data[0].rightSibling
        self.vec1 = frontier_bone.data[0].vec1
        self.vec2 = frontier_bone.data[0].vec2
        self.posVec = frontier_bone.data[0].posVec
        self.null = frontier_bone.data[0].null
        self.chainID = frontier_bone.data[0].chainID
        self.unkn2 = frontier_bone.data[0].unkn2


def get_frontier_skeleton(file_path):
    """
    Read the FSKL file.

    :param str file_path: FSKL file path.
    :return dict[int, FBone]: skeleton
    """
    with open(file_path, "rb") as modelFile:
        frontier_file = fblock.FBlock()
        frontier_file.marshall(FileLike(modelFile.read()))
    bones = frontier_file.data[1:]
    skeleton = {}
    for fileBone in bones:
        if not isinstance(fileBone, fblock.FBlock):
            raise TypeError(
                f"Object should be {fblock.FBlock}, type is {type(fileBone)}"
            )
        frontier_bone = FBone(fileBone)
        skeleton[frontier_bone.nodeID] = frontier_bone
    return skeleton
