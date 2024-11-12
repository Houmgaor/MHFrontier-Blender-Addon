# -*- coding: utf-8 -*-
"""
Created on Mon Jan 28 13:38:38 2019

@author: AsteriskAmpersand
"""
import struct
from collections import OrderedDict
from binascii import hexlify


def chunks(array, n):
    """Yield successive n-sized chunks from array."""
    for i in range(0, len(array), n):
        yield array[i : i + n]


def half_to_float(h):
    s = int((h >> 15) & 0x00000001)  # sign
    e = int((h >> 10) & 0x0000001F)  # exponent
    f = int(h & 0x000003FF)  # fraction
    if s == 0 and e == 0 and f == 0:
        return 0
    return (-1) ** s * 2 ** (e - 15) * (f / (2**10) + 1)


def minifloat_deserialize(x):
    v = struct.unpack("H", x)
    return half_to_float(v[0])


def minifloat_serialize(x):
    f16_exponent_bits = 0x1F
    f16_exponent_shift = 10
    f16_exponent_bias = 15
    f16_mantissa_bits = 0x3FF
    f16_mantissa_shift = 23 - f16_exponent_shift
    f16_max_exponent = f16_exponent_bits << f16_exponent_shift
    a = struct.pack(">f", x)
    b = hexlify(a)
    f32 = int(b, 16)
    sign = (f32 >> 16) & 0x8000
    exponent = ((f32 >> 23) & 0xFF) - 127
    mantissa = f32 & 0x007FFFFF
    if exponent == 128:
        f16 = sign | f16_max_exponent
        if mantissa:
            f16 |= mantissa & f16_mantissa_bits
    elif exponent > 15:  # hack
        f16 = sign | f16_max_exponent
    elif exponent >= -15:  # hack
        exponent += f16_exponent_bias
        mantissa >>= f16_mantissa_shift
        f16 = sign | exponent << f16_exponent_shift | mantissa
    else:
        f16 = sign
    return struct.pack("H", f16)


def deserializer(data_format, size):
    """Prepares the deserialization of data with a specific format."""
    return {
        "deserializer": lambda x: struct.unpack(data_format, x)[0],
        "serializer": lambda x: struct.pack(data_format, x),
        "size": size,
    }


class Cstruct:
    """Main structure to parse C-like data type."""

    CTypes = {
        "byte": deserializer("b", 1),
        "int8": deserializer("b", 1),
        "ubyte": deserializer("B", 1),
        "uint8": deserializer("B", 1),
        "short": deserializer("h", 2),
        "int16": deserializer("h", 2),
        "ushort": deserializer("H", 2),
        "uint16": deserializer("H", 2),
        "long": deserializer("i", 4),
        "int32": deserializer("i", 4),
        "int": deserializer("i", 4),
        "ulong": deserializer("I", 4),
        "uint32": deserializer("I", 4),
        "uint": deserializer("I", 4),
        "quad": deserializer("q", 8),
        "int64": deserializer("q", 8),
        "uquad": deserializer("Q", 8),
        "uint64": deserializer("Q", 8),
        "hfloat": {
            "size": 2,
            "deserializer": minifloat_deserialize,
            "serializer": minifloat_serialize,
        },
        "float": deserializer("f", 4),
        "double": deserializer("d", 8),
        "char": deserializer("c", 1),
        "bool": deserializer("b", 1),
    }
    StructTypes = {}

    @staticmethod
    def is_array_type(type_str):
        return "[" in type_str and (
            type_str[: type_str.index("[")] in Cstruct.CTypes
            or type_str[: type_str.index("[")] in Cstruct.StructTypes
        )

    @staticmethod
    def array_type(type_str):
        """
        Get the type for an array of data.

        :param str type_str: Data types to assign.
        """

        base = type_str[: type_str.index("[")]
        size = type_str[type_str.index("[") + 1 : type_str.index("]")]
        data_type = Cstruct.CTypes[base]
        int_size = int(size)

        output = {"size": int_size * data_type["size"]}
        if base == "char":
            output.update(
                {
                    "deserializer": lambda x: "".join(
                        [
                            data_type["deserializer"](chunk).decode("ascii")
                            for chunk in chunks(x, data_type["size"])
                        ]
                    ),
                    "serializer": lambda x: x.encode("ascii").ljust(int_size, b"\x00"),
                }
            )
        else:
            output.update(
                {
                    "deserializer": lambda x: [
                        data_type["deserializer"](chunk)
                        for chunk in chunks(x, data_type["size"])
                    ],
                    "serializer": lambda x: b"".join(map(data_type["serializer"], x)),
                }
            )
        return output

    def __init__(self, fields):
        """
        Assign the structure type.

        :param dict fields: Fields to assign.
        """
        self.struct = OrderedDict()
        self.initialized = True
        for name in fields:
            if fields[name] in Cstruct.CTypes:
                self.struct[name] = Cstruct.CTypes[fields[name]]
            elif Cstruct.is_array_type(fields[name]):
                self.struct[name] = Cstruct.array_type(fields[name])
            else:
                raise ValueError(
                    "%s Type is not C Struct class compatible." % fields[name]
                )

    def size(self):
        """Total size of the contained data."""
        return sum(self.struct[element]["size"] for element in self.struct)

    def marshall(self, data):
        """Build a dictionary of deserialized data."""
        return {
            varName: typeOperator["deserializer"](data.read(typeOperator["size"]))
            for varName, typeOperator in self.struct.items()
        }

    def serialize(self, data):
        """Serialize all input data."""
        return b"".join(
            [
                typeOperator["serializer"](data[varName])
                for varName, typeOperator in self.struct.items()
            ]
        )
