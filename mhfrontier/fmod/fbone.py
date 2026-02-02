"""
Definition of a Frontier bone.
"""

from typing import List, TYPE_CHECKING

from ..common import standard_structures

if TYPE_CHECKING:
    from . import fblock


class FBone:
    """
    Frontier bone with SRT (Scale-Rotation-Translation) transform.

    Attributes:
        nodeID: Bone identifier.
        parentID: Parent bone ID (-1 for root).
        leftChild: Left child bone ID in the tree.
        rightSibling: Right sibling bone ID in the tree.
        scale: Local scale [x, y, z, w] (usually [1, 1, 1, 1]).
        rotation: Rotation quaternion [x, y, z, w] (usually identity).
        position: Local translation [x, y, z, w].
        chainID: IK chain identifier.
    """

    nodeID: int
    parentID: int
    leftChild: int
    rightSibling: int
    scale: List[float]
    rotation: List[float]
    position: List[float]
    chainID: int

    def __init__(self, frontier_bone: "fblock.FBlock") -> None:
        """
        Create a bone from block data.

        :param frontier_bone: Block containing bone data.
        :raises TypeError: If the block doesn't contain BoneBlock data.
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
