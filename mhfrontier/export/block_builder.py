"""
Block construction utilities for Frontier file formats.

Provides BlockBuilder class for constructing recursive block structures
with automatic size calculation, matching the FMOD/FSKL file format.
"""

import struct
from typing import List, Optional, Union

from ..fmod.fblock import BlockType


# Block header size: type (4) + count (4) + size (4) = 12 bytes
HEADER_SIZE = 12


class BlockBuilder:
    """
    Builder for constructing Frontier block structures.

    Frontier files use a recursive block structure where each block has:
    - 4-byte type identifier (BlockType enum)
    - 4-byte count (number of child blocks or data items)
    - 4-byte size (total size including header)
    - Variable-length content (child blocks or raw data)

    Usage:
        builder = BlockBuilder(BlockType.FILE)
        builder.add_child(child_block)
        builder.add_raw_data(bytes_data)
        data = builder.serialize()
    """

    def __init__(
        self,
        block_type: Union[BlockType, int],
        count: Optional[int] = None,
    ) -> None:
        """
        Create a block builder.

        :param block_type: Block type identifier.
        :param count: Optional explicit count. If None, computed from children.
        """
        self.block_type = int(block_type)
        self._explicit_count = count
        self.children: List["BlockBuilder"] = []
        self.raw_data: bytes = b""

    @property
    def count(self) -> int:
        """Get the block count (number of children or explicit value)."""
        if self._explicit_count is not None:
            return self._explicit_count
        return len(self.children)

    def add_child(self, child: "BlockBuilder") -> "BlockBuilder":
        """
        Add a child block.

        :param child: Child BlockBuilder to add.
        :return: Self for chaining.
        """
        self.children.append(child)
        return self

    def add_raw_data(self, data: bytes) -> "BlockBuilder":
        """
        Add raw data to this block.

        Raw data is appended after any child blocks.

        :param data: Binary data to add.
        :return: Self for chaining.
        """
        self.raw_data += data
        return self

    def set_raw_data(self, data: bytes) -> "BlockBuilder":
        """
        Set raw data for this block (replaces existing).

        :param data: Binary data to set.
        :return: Self for chaining.
        """
        self.raw_data = data
        return self

    def content_size(self) -> int:
        """Calculate the size of content (children + raw data)."""
        children_size = sum(child.total_size() for child in self.children)
        return children_size + len(self.raw_data)

    def total_size(self) -> int:
        """Calculate total size including header."""
        return HEADER_SIZE + self.content_size()

    def serialize_header(self) -> bytes:
        """Serialize the block header."""
        return struct.pack(
            "<III",  # Little-endian: type, count, size
            self.block_type,
            self.count,
            self.total_size(),
        )

    def serialize(self) -> bytes:
        """
        Serialize the entire block including header and content.

        :return: Complete block data as bytes.
        """
        parts = [self.serialize_header()]

        # Serialize children first
        for child in self.children:
            parts.append(child.serialize())

        # Append raw data
        if self.raw_data:
            parts.append(self.raw_data)

        return b"".join(parts)


class DataBlockBuilder(BlockBuilder):
    """
    Builder for data blocks that contain arrays of structured data.

    Used for geometry data blocks (VERTEX, NORMALS, UV, etc.) where
    each item is serialized individually.
    """

    def __init__(
        self,
        block_type: Union[BlockType, int],
        items: List[bytes],
    ) -> None:
        """
        Create a data block builder.

        :param block_type: Block type identifier.
        :param items: List of serialized data items.
        """
        super().__init__(block_type, count=len(items))
        self.raw_data = b"".join(items)
