# -*- coding: utf-8 -*-
"""
PAC archive parser for Monster Hunter Frontier.

PAC format:
  - 4 bytes: entry count (uint32 LE)
  - count × 8 bytes: entries (offset uint32 LE + size uint32 LE)
  - Entry data follows the table; offsets must not overlap the table.

Ported from MHBridge pac.cpp by Houmgaor.
"""

import struct
from dataclasses import dataclass, field
from typing import List, Optional

PAC_HEADER_SIZE = 4  # Just the count field
MAX_COUNT = 10000


@dataclass
class PacEntry:
    offset: int
    size: int


@dataclass
class PacArchive:
    entries: List[PacEntry] = field(default_factory=list)
    data: bytes = b""

    def extract(self, index: int) -> Optional[bytes]:
        if index >= len(self.entries):
            return None
        e = self.entries[index]
        if e.size == 0:
            return b""
        end = e.offset + e.size
        if end > len(self.data):
            return None
        return self.data[e.offset:end]


def is_pac_archive(data: bytes) -> bool:
    if len(data) < PAC_HEADER_SIZE:
        return False

    count = struct.unpack_from("<I", data, 0)[0]
    if count == 0 or count > MAX_COUNT:
        return False

    table_size = PAC_HEADER_SIZE + count * 8
    if table_size > len(data):
        return False

    # Validate all entries
    for i in range(count):
        pos = PAC_HEADER_SIZE + i * 8
        offset, size = struct.unpack_from("<II", data, pos)
        if offset + size > len(data):
            return False
        if size > 0 and offset < table_size:
            return False  # Data overlaps the entry table

    return True


def parse_pac(data: bytes) -> Optional[PacArchive]:
    if not is_pac_archive(data):
        return None

    count = struct.unpack_from("<I", data, 0)[0]
    archive = PacArchive(data=data)

    for i in range(count):
        pos = PAC_HEADER_SIZE + i * 8
        offset, size = struct.unpack_from("<II", data, pos)
        archive.entries.append(PacEntry(offset=offset, size=size))

    return archive
