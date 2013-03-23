# Copyright (C) 2012 Peter Teichman

import array

# A few routines for encoding & decoding varint-encoded integers, as
# described in the Protocol Buffers docs:
# https://developers.google.com/protocol-buffers/docs/encoding#varints
#
# varint is a 7-bit integer encoding with the 8th reserved as a
# continuation bit. This is an implementation of the unsigned encoding
# only (not ZigZag).


def diff(seq):
    if not seq:
        return []

    ret = [seq[0]]
    for i in xrange(1, len(seq)):
        ret.append(seq[i] - seq[i - 1])
    return ret


def undiff(seq):
    if not seq:
        return []

    ret = [seq[0]]
    for i in xrange(1, len(seq)):
        ret.append(seq[i] + ret[i - 1])
    return ret


def encode_one(value, buf=array.array("B")):
    append = buf.append

    if value >= 0:
        bits = value & 0x7f
        value >>= 7
        while value:
            append(0x80 | bits)
            bits = value & 0x7f
            value >>= 7
        append(bits)

        ret = buf.tostring()
        del buf[:]
        return ret

    raise ValueError("negative numbers not supported")


def encode(values, buf=array.array("B")):
    append = buf.append

    for value in values:
        bits = value & 0x7f
        value >>= 7
        while value:
            append(0x80 | bits)
            bits = value & 0x7f
            value >>= 7
        append(bits)

    ret = buf.tostring()
    del buf[:]
    return ret


def decode_one(data):
    local_ord = ord
    cur = shift = 0

    for byte in iter(data):
        b = local_ord(byte)
        cur |= ((b & 0x7f) << shift)

        if b & 0x80:
            shift += 7
        else:
            return cur


def write_one(value, fd):
    local_chr = chr
    local_write = fd.write

    if value >= 0:
        bits = value & 0x7f
        value >>= 7
        while value:
            fd.write(local_chr(0x80 | bits))
            bits = value & 0x7f
            value >>= 7
        fd.write(local_chr(bits))


def read_one(fd):
    local_ord = ord
    local_read = fd.read

    cur = shift = 0

    while 1:
        r = local_read(1)
        if not r:
            break

        b = local_ord(r)
        cur |= ((b & 0x7f) << shift)

        if b & 0x80:
            shift += 7
        else:
            return cur


def decode(data):
    # At least for small data, it's a significant performance
    # improvement to copy the data into a byte array to avoid calling
    # ord() on every byte.
    bytes = array.array("B", data)

    ret = []
    append = ret.append

    cur = shift = 0
    for b in bytes:
        cur |= ((b & 0x7f) << shift)

        if b & 0x80:
            shift += 7
        else:
            append(cur)
            shift = 0
            cur = 0

    return ret
