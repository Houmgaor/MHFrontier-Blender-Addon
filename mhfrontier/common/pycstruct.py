"""
Definition of a Python structure interface for C-like blocks.
"""

import abc

from . import cstruct


class PyCStruct(abc.ABC):
    """Recursive block structure for Python."""

    def __init__(self, fields):
        """
        Define the C structure from fields.

        :param collections.OrderedDict fields:
        """
        self.fields = fields
        self.CStruct = cstruct.Cstruct(self.fields)

    def marshall(self, data):
        """Set each property found in the block as an object attribute."""

        items = self.CStruct.marshall(data).items()
        for attr, value in items:
            if not hasattr(self, attr):
                raise AttributeError(f"Object {self} has no attribute {attr}")
            self.__setattr__(attr, value)
