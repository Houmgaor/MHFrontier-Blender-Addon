# -*- coding: utf-8 -*-
"""
ECD/EXF decryption for Monster Hunter Frontier files.

Ported from ReFrontier (C#) and FrontierTextHandler (Python) by Houmgaor.

Supports two encryption formats:
- ECD (0x1A646365): LCG-based encryption with nibble Feistel cipher
- EXF (0x1A667865): LCG-based 16-byte XOR key with position-dependent transform
"""

import struct

ECD_MAGIC = 0x1A646365
EXF_MAGIC = 0x1A667865
HEADER_SIZE = 16

_RND_BUF_ECD = bytes([
    0x4A, 0x4B, 0x52, 0x2E, 0x00, 0x00, 0x00, 0x01,
    0x00, 0x01, 0x0D, 0xCD, 0x00, 0x00, 0x00, 0x01,
    0x00, 0x01, 0x0D, 0xCD, 0x00, 0x00, 0x00, 0x01,
    0x00, 0x01, 0x0D, 0xCD, 0x00, 0x00, 0x00, 0x01,
    0x00, 0x19, 0x66, 0x0D, 0x00, 0x00, 0x00, 0x03,
    0x7D, 0x2B, 0x89, 0xDD, 0x00, 0x00, 0x00, 0x01,
])

_RND_BUF_EXF = bytes([
    0x4A, 0x4B, 0x52, 0x2E, 0x00, 0x00, 0x00, 0x01,
    0x00, 0x01, 0x0D, 0xCD, 0x00, 0x00, 0x00, 0x01,
    0x00, 0x01, 0x0D, 0xCD, 0x00, 0x00, 0x00, 0x01,
    0x00, 0x01, 0x0D, 0xCD, 0x00, 0x00, 0x00, 0x01,
    0x02, 0xE9, 0x0E, 0xDD, 0x00, 0x00, 0x00, 0x03,
])


def _load_uint32_be(buffer: bytes, offset: int) -> int:
    return (buffer[offset] << 24) | (buffer[offset + 1] << 16) | (buffer[offset + 2] << 8) | buffer[offset + 3]


def is_ecd_file(data: bytes) -> bool:
    if len(data) < 4:
        return False
    return struct.unpack("<I", data[:4])[0] == ECD_MAGIC


def is_exf_file(data: bytes) -> bool:
    if len(data) < 4:
        return False
    return struct.unpack("<I", data[:4])[0] == EXF_MAGIC


def is_encrypted_file(data: bytes) -> bool:
    return is_ecd_file(data) or is_exf_file(data)


def decode_ecd(data: bytes) -> bytes:
    ecd_key = struct.unpack("<H", data[4:6])[0]
    payload_size = struct.unpack("<I", data[8:12])[0]
    crc32 = struct.unpack("<I", data[12:16])[0]

    multiplier = _load_uint32_be(_RND_BUF_ECD, 8 * ecd_key)
    increment = _load_uint32_be(_RND_BUF_ECD, 8 * ecd_key + 4)

    rnd = ((crc32 << 16) | (crc32 >> 16) | 1) & 0xFFFFFFFF
    rnd = (rnd * multiplier + increment) & 0xFFFFFFFF
    xorpad = rnd
    r8 = xorpad & 0xFF

    output = bytearray(payload_size)
    for i in range(payload_size):
        rnd = (rnd * multiplier + increment) & 0xFFFFFFFF
        xorpad = rnd

        encrypted_byte = data[HEADER_SIZE + i]
        r11 = encrypted_byte ^ r8
        r12 = (r11 >> 4) & 0xFF

        for _ in range(8):
            r10 = xorpad ^ r11
            r11 = r12
            r12 = (r12 ^ r10) & 0xFF
            xorpad >>= 4

        r8 = (r12 & 0xF) | ((r11 & 0xF) << 4)
        output[i] = r8

    return bytes(output)


def decode_exf(data: bytes) -> bytes:
    header = data[:HEADER_SIZE]
    index = struct.unpack("<H", header[4:6])[0]
    temp_val = struct.unpack("<I", header[12:16])[0]
    value = temp_val

    key_buffer = bytearray(16)
    for i in range(4):
        multiplier = _load_uint32_be(_RND_BUF_EXF, index * 8)
        increment = _load_uint32_be(_RND_BUF_EXF, index * 8 + 4)
        temp_val = (temp_val * multiplier + increment) & 0xFFFFFFFF
        key = temp_val ^ value
        struct.pack_into("<I", key_buffer, i * 4, key)
    keybuf = bytes(key_buffer)

    output = bytearray(len(data) - HEADER_SIZE)
    for i in range(HEADER_SIZE, len(data)):
        r28 = i - HEADER_SIZE
        r8 = data[i]
        idx = r28 & 0xF
        r4 = r8 ^ r28
        r12 = keybuf[idx]
        r0 = (r4 & 0xF0) >> 4
        r7 = keybuf[r0]
        r9 = r4 >> 4
        r5 = r7 >> 4
        r9 ^= r12
        r26 = r5 ^ r4
        r26 = (r26 & ~0xF0) | ((r9 & 0xF) << 4)
        output[r28] = r26 & 0xFF

    return bytes(output)


def decrypt_file(data: bytes) -> bytes:
    """Decrypt an ECD or EXF file, returning the payload only."""
    if is_ecd_file(data):
        return decode_ecd(data)
    elif is_exf_file(data):
        return decode_exf(data)
    return data
