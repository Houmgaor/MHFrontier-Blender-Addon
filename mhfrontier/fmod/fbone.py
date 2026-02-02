"""
Definition of a Frontier bone.
"""

from ..common import standard_structures


class FBone:
    """
    Frontier bone with SRT (Scale-Rotation-Translation) transform.

    Attributes:
        nodeID: Bone identifier
        parentID: Parent bone ID (-1 for root)
        leftChild, rightSibling: Tree navigation
        scale: Local scale [x, y, z, w] (usually [1,1,1,1])
        rotation: Rotation quaternion [x, y, z, w] (usually identity)
        position: Local translation [x, y, z, w]
        chainID: IK chain identifier
    """

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

        self.nodeID = source.nodeID
        self.parentID = source.parentID
        self.leftChild = source.leftChild
        self.rightSibling = source.rightSibling
        self.scale = source.scale
        self.rotation = source.rotation
        self.position = source.position
        self.chainID = source.chainID

        # Legacy aliases for backward compatibility
        self.vec1 = source.scale
        self.vec2 = source.rotation
        self.posVec = source.position
