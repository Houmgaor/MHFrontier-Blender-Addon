"""
Frontier material file.
"""

import warnings
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from . import fblock


class FMat:
    """
    Frontier material with texture references.

    Attributes:
        diffuse_id: Image ID for diffuse/albedo texture (or None).
        normal_id: Image ID for normal map texture (or None).
        specular_id: Image ID for specular/roughness texture (or None).
    """

    diffuse_id: Optional[int]
    normal_id: Optional[int]
    specular_id: Optional[int]

    def __init__(
        self,
        mat_block: "fblock.MaterialBlock",
        textures: List["fblock.TextureBlock"],
    ) -> None:
        """
        Create a material from block data.

        :param mat_block: Material block containing texture indices.
        :param textures: List of texture blocks for ID lookup.
        """
        self.diffuse_id = None
        self.normal_id = None
        self.specular_id = None
        for i, ix in enumerate(mat_block.data[0].textureIndices):
            image_id = textures[ix.index].data[0].imageID
            if i == 0:
                self.diffuse_id = image_id
            elif i == 1:
                self.normal_id = image_id
            elif i == 2:
                self.specular_id = image_id
            else:
                warnings.warn(f"Unknown texture index {i}, will be ignored")
