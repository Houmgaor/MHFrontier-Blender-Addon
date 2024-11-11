# -*- coding: utf-8 -*-
"""
Created on Mon Jan 28 13:38:38 2019

@author: AsteriskAmpersand
"""
import abc
import struct
from collections import OrderedDict
from binascii import hexlify


def chunks(sliceable, n):
    """Yield successive n-sized chunks from sliceable."""
    for i in range(0, len(sliceable), n):
        yield sliceable[i : i + n]


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


class PyCStruct(abc.ABC):
    def __init__(self, data=None, _parent=None, **kwargs):
        """
        Define the structure.

        :param data: C-compatible object to load data from.
        :type data: mhfrontier.fmod.fblock.FBlock
        :param dict kwargs: Alternative to data if None
        """
        if not hasattr(self, "fields"):
            raise ValueError("fields should be implemented!")
        self.CStruct = Cstruct(self.fields)
        if data is not None:
            self.marshall(data)
        elif kwargs:
            fields_keys = set(self.fields.keys())
            entry_keys = set(kwargs.keys())
            if fields_keys == entry_keys:
                for attr, value in kwargs.items():
                    self.__setattr__(attr, value)
            else:
                if fields_keys > entry_keys:
                    raise AttributeError("Missing fields to Initialize")
                if fields_keys < entry_keys:
                    raise AttributeError("Excessive Fields passed")
                raise AttributeError("Field Mismatch")

    def __len__(self):
        return len(self.CStruct)

    def marshall(self, data):
        """Set each property found in the block as an object attribute."""

        for attr, value in self.CStruct.marshall(data).items():
            self.__setattr__(attr, value)

    def serialize(self):
        return self.CStruct.serialize(
            {key: self.__getattribute__(key) for key in self.fields}
        )

    def __eq__(self, other):
        return all(
            [
                self.__getattribute__(key) == other.__getattribute__(key)
                for key in self.fields
            ]
        )

    defaultProperties = {}
    requiredProperties = {}

    def construct(self, data):
        for field in self.fields:
            if field in data:
                self.__setattr__(field, data[field])
            elif field in self.defaultProperties:
                self.__setattr__(field, self.defaultProperties[field])
            elif field in self.requiredProperties:
                raise KeyError("Required Property missing in supplied data")
            self.__setattr__(field, None)

    def verify(self):
        for attr in self.fields:
            if self.__getattribute__(attr) is None:
                raise AssertionError("Attribute %s is not initialized." % attr)


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

        if base != "char":
            return {
                "size": int_size * data_type["size"],
                "deserializer": lambda x: [
                    data_type["deserializer"](chunk)
                    for chunk in chunks(x, data_type["size"])
                ],
                "serializer": lambda x: b"".join(map(data_type["serializer"], x)),
            }
        return {
            "size": int_size * data_type["size"],
            "deserializer": lambda x: "".join(
                [
                    data_type["deserializer"](chunk).decode("ascii")
                    for chunk in chunks(x, data_type["size"])
                ]
            ),
            "serializer": lambda x: x.encode("ascii").ljust(int_size, b"\x00"),
        }

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

    def __len__(self):
        return sum([self.struct[element]["size"] for element in self.struct])

    def marshall(self, data):
        return {
            varName: typeOperator["deserializer"](data.read(typeOperator["size"]))
            for varName, typeOperator in self.struct.items()
        }

    def serialize(self, data):
        return b"".join(
            [
                typeOperator["serializer"](data[varName])
                for varName, typeOperator in self.struct.items()
            ]
        )


class Mod3Container:
    def __init__(self, mod3class, containee_count=0):
        self.mod3Array = [mod3class() for _ in range(containee_count)]

    def marshall(self, data):
        for x in self.mod3Array:
            x.marshall(data)

    def construct(self, data):
        if len(data) != len(self.mod3Array):
            raise AssertionError(
                "Cannot construct container with different amounts of data"
            )
        for x, d in zip(self.mod3Array, data):
            x.construct(d)

    def serialize(self):
        return b"".join(element.serialize() for element in self.mod3Array)

    def __iter__(self):
        return self.mod3Array.__iter__()

    def __getitem__(self, ix):
        return self.mod3Array.__getitem__(ix)

    def __len__(self):
        if self.mod3Array:
            return len(self.mod3Array) * len(self.mod3Array[0])
        return 0

    def append(self, ele):
        self.mod3Array.append(ele)

    def pop(self, ix):
        self.mod3Array.pop(ix)

    def count(self):
        return len(self.mod3Array)

    def verify(self):
        for x in self.mod3Array:
            x.verify()
