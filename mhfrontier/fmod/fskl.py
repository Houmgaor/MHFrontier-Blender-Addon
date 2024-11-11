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
            raise TypeError("Should be " + fblock.BoneBlock.__name__)
        self.boneID = None
        self.nodeID = None
        self.parentID = None
        # Properties imported without selection
        for field in frontier_bone.data[0].fields:
            setattr(self, field, getattr(frontier_bone.data[0], field))


class FSkeleton:
    """Start the definition of a Frontier Skeleton from file."""

    def __init__(self, file_path):
        """
        Read the FSKL file.

        :param str file_path: FSKL file path.
        """
        with open(file_path, "rb") as modelFile:
            frontier_file = fblock.FBlock()
            frontier_file.marshall(FileLike(modelFile.read()))
        bones = frontier_file.data[1:]
        self.skeleton = {}
        for fileBone in bones:
            frontier_bone = FBone(fileBone)
            self.skeleton[frontier_bone.nodeID] = frontier_bone

    def skeleton_structure(self):
        """
        Skeleton of Frontier bones.

        :return dict[FBone]: Skeleton definition.
        """
        return self.skeleton
