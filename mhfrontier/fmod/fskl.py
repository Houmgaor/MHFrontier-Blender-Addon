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
        for field in frontier_bone.data[0].fields:
            setattr(self, field, getattr(frontier_bone.data[0], field))


class FSkeleton:
    """Start the definition of a Frontier Skeleton from file."""

    def __init__(self, file_path):
        with open(file_path, "rb") as modelFile:
            frontier_file = fblock.FBlock()
            frontier_file.marshall(FileLike(modelFile.read()))
        bones = frontier_file.data[1:]
        self.skeleton = {}
        for fileBone in bones:
            frontier_bone = FBone(fileBone)
            self.skeleton[frontier_bone.nodeID] = frontier_bone

    def skeleton_structure(self):
        return self.skeleton
