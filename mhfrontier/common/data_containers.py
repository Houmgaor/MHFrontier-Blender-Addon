"""
Definition file for DataContainer classses.
"""

import abc
import logging
from typing import Optional

from ..common import standard_structures as sstructs


class DataContainer(abc.ABC):
    """Simple data container system."""

    def __init__(self, data_type):
        """
        Associate a data type.

        :param data_type: Data structure to use.
        :type data_type: Type[mhfrontier.fmod.fblock.PyCStruct]
        """
        self.dataType = data_type
        self.data = self.dataType()

    def marshall(self, data):
        self.data.marshall(data)

    def pretty_print(
        self,
        logger: Optional[logging.Logger] = None,
        indents: int = 0,
    ) -> None:
        """Data containers don't print their contents."""
        pass


class TrisStripsData(DataContainer):

    def __init__(self):
        super().__init__(sstructs.TrisTrip)


class MaterialList(DataContainer):

    def __init__(self):
        super().__init__(sstructs.UIntField)


class MaterialMap(DataContainer):

    def __init__(self):
        super().__init__(sstructs.UIntField)


class BoneMapData(DataContainer):

    def __init__(self):
        super().__init__(sstructs.UIntField)


class VertexData(DataContainer):

    def __init__(self):
        super().__init__(sstructs.Vect3)


class NormalsData(DataContainer):
    def __init__(self):
        super().__init__(sstructs.Vect3)


class UVData(DataContainer):
    def __init__(self):
        super().__init__(sstructs.UV)


class RGBData(DataContainer):
    def __init__(self):
        super().__init__(sstructs.Vect4)
