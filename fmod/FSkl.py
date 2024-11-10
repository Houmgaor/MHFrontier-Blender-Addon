# -*- coding: utf-8 -*-
"""
Created on Sun Dec 29 21:50:00 2019

@author: AsteriskAmpersand
"""
from ..fmod.FBlock import FBlock
from ..common.FileLike import FileLike

class FBone:
    def __init__(self, frontier_bone):
        for field in frontier_bone.Data[0].fields:
            setattr(self, field, getattr(frontier_bone.Data[0], field))


class FSkeleton:
    def __init__(self, file_path):
        with open(file_path, "rb") as modelFile:
            frontier_file = FBlock()
            frontier_file.marshall(FileLike(modelFile.read()))
        bones = frontier_file.Data[1:]
        self.Skeleton = {}
        for fileBone in bones:
            frontier_bone = FBone(fileBone)
            self.Skeleton[frontier_bone.nodeID] = frontier_bone

    def skeleton_structure(self):
        return self.Skeleton
