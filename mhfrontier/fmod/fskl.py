# -*- coding: utf-8 -*-
"""
Created on Sun Dec 29 21:50:00 2019

@author: AsteriskAmpersand
"""
from ..fmod import fblock, fbone
from ..common import filelike


def get_frontier_skeleton(file_path):
    """
    Read the FSKL file.

    :param str file_path: FSKL file path.
    :return dict[int, FBone]: skeleton
    """
    with open(file_path, "rb") as modelFile:
        frontier_file = fblock.FBlock()
        frontier_file.marshall(filelike.FileLike(modelFile.read()))
    bones = frontier_file.data[1:]
    skeleton = {}
    for fileBone in bones:
        if not isinstance(fileBone, fblock.FBlock):
            raise TypeError(
                f"Object should be {fblock.FBlock}, type is {type(fileBone)}"
            )
        frontier_bone = fbone.FBone(fileBone)
        skeleton[frontier_bone.nodeID] = frontier_bone
    return skeleton
