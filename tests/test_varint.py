# Copyright (C) 2012 Peter Teichman

import unittest

from cobe.varint import decode, decode_one, diff, encode, encode_one, undiff


class TestVarint(unittest.TestCase):
    def test_varint_size(self):
        # Check each boundary of varint sizing
        sizes = {
            2: 0x80,
            3: 0x4000,
            4: 0x200000,
            5: 0x10000000,
            6: 0x800000000L,
            7: 0x40000000000L,
            8: 0x2000000000000L,
            9: 0x100000000000000L,
            10: 0x8000000000000000L
            }

        for i in xrange(128):
            self.assertEquals(1, len(encode_one(i)))

        for size, value in sizes.items():
            self.assertEquals(size - 1, len(encode_one(value - 1)))
            self.assertEquals(size, len(encode_one(value)))

    def test_encode_one(self):
        # numbers 0..127 get encoded as a single byte
        for i in xrange(128):
            self.assertEquals(chr(i), encode_one(i))

    def test_decode_one(self):
        for i in xrange(64, 128):
            self.assertEquals(i, decode_one(chr(i)))

    def test_encode_decode_one(self):
        for i in xrange(100000):
            self.assertEquals(i, decode_one(encode_one(i)))

    def test_encode_decode(self):
        nums = range(0, 2048)

        data = encode(nums)
        self.assertEquals(3968, len(data))

        nums2 = decode(data)
        self.assertEquals(nums, nums2)

    def test_diff(self):
        seq = []
        self.assertEquals([], diff(seq))

        seq = [1]
        self.assertEquals([1], diff(seq))

        seq = [10]
        self.assertEquals([10], diff(seq))

        seq = [1, 2, 7, 10, 23]
        self.assertEquals([1, 1, 5, 3, 13], diff(seq))

    def test_undiff(self):
        seq = []
        self.assertEquals([], undiff(seq))

        seq = [1]
        self.assertEquals([1], undiff(seq))

        seq = [10]
        self.assertEquals([10], undiff(seq))

        seq = [1, 1, 5, 3, 13]
        self.assertEquals([1, 2, 7, 10, 23], undiff(seq))

if __name__ == '__main__':
    unittest.main()
