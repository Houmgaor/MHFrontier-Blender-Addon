"""
Frontier material file.
"""

import warnings


class FMat:
    """Load a Frontier material file."""

    def __init__(self, mat_block, textures):
        """
        Load the data to the corresponding values.

        :param mat_block: Material, contains destination data.
        :type mat_block: mhfrontier.fmod.fblock.MaterialBlock
        :param textures: Information on texture to assign.
        :type textures: list[mhfrontier.fmod.fblock.TextureBlock]
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
