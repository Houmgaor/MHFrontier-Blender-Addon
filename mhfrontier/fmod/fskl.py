# -*- coding: utf-8 -*-
"""
Frontier skeleton file loader.

Created on Sun Dec 29 21:50:00 2019

@author: AsteriskAmpersand
"""

from typing import Dict

from . import fblock, fbone
from ..common import filelike


def get_frontier_skeleton(file_path: str) -> Dict[int, "fbone.FBone"]:
    """
    Load a skeleton from an FSKL file.

    :param file_path: Path to the FSKL file.
    :return: Dictionary mapping node IDs to FBone objects.
    """
    with open(file_path, "rb") as model_file:
        frontier_file = fblock.FBlock()
        frontier_file.marshall(filelike.FileLike(model_file.read()))
    bones = frontier_file.data[1:]
    skeleton: Dict[int, fbone.FBone] = {}
    for file_bone in bones:
        if not isinstance(file_bone, fblock.FBlock):
            raise TypeError(
                f"Object should be {fblock.FBlock}, type is {type(file_bone)}"
            )
        frontier_bone = fbone.FBone(file_bone)
        skeleton[frontier_bone.nodeID] = frontier_bone
    return skeleton
