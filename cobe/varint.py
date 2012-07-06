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
    if not seq: return []

    ret = [seq[0]]
    for i in xrange(1, len(seq)):
        ret.append(seq[i] - seq[i-1])
    return ret

def undiff(seq):
    if not seq: return []

    ret = [seq[0]]
    for i in xrange(1, len(seq)):
        ret.append(seq[i] + ret[i-1])
    return ret

def encode_one(value):
    return encode((value,))

def encode(values):
    buf = array.array("B")
    append = buf.append

    for value in values:
        bits = value & 0x7f
        value >>= 7
        while value:
            append(0x80 | bits)
            bits = value & 0x7f
            value >>= 7
        append(bits)

    return buf.tostring()

def decode_one(value):
    return decode(value)[0]

def decode(data):
    ret = []
    append = ret.append
    local_ord = ord

    cur = pos = shift = 0
    end = len(data)

    while pos < end:
        b = local_ord(data[pos])
        cur |= ((b & 0x7f) << shift)

        # If the high bit is set, continue reading the current int
        if b & 0x80:
            shift += 7
        else:
            append(cur)
            shift = 0
            cur = 0

        pos += 1

    return ret
