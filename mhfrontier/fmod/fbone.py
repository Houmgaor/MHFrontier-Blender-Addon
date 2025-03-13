"""
Definition of a Frontier bone.
"""

from ..common import standard_structures


class FBone:
    """Simple Frontier bone definition."""

    def __init__(self, frontier_bone):
        """
        Create the bone.

        :param frontier_bone: Input bone to parse
        :type frontier_bone: mhfrontier.fmod.fblock.FBlock
        """
        source = frontier_bone.data[0]
        if not isinstance(source, standard_structures.BoneBlock):
            raise TypeError(
                f"Should be {standard_structures.BoneBlock.__name__}, "
                f"type is {type(source)}"
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
