# -*- coding: utf-8 -*-
"""
Created on Sun Dec 29 21:50:00 2019

@author: AsteriskAmpersand
"""
try:
    from ..fmod.FBlock import FBlock
    from ..common.FileLike import FileLike
except:
    import sys

    sys.path.insert(0, r'..\common')
    sys.path.insert(0, r'..\fmod')
    from FBlock import FBlock
    from FileLike import FileLike


class FBone:
    def __init__(self, frontier_bone):
        for field in frontier_bone.Data[0].fields:
            setattr(self, field, getattr(frontier_bone.Data[0], field))


class FSkeleton:
    def __init__(self, FilePath):
        with open(FilePath, "rb") as modelFile:
            frontier_file = FBlock()
            frontier_file.marshall(FileLike(modelFile.read()))
        bones = frontier_file.Data[1:]
        self.Skeleton = {}
        for fileBone in bones:
            fbone = FBone(fileBone)
            self.Skeleton[fbone.nodeID] = fbone

    def skeleton_structure(self):
        return self.Skeleton
