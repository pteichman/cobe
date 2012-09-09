# Copyright (C) 2012 Peter Teichman
# coding=utf8

import time
import unittest2 as unittest

from cobe import utils


class ITimeTest(unittest.TestCase):
    def test_itime(self):
        seq = ["one", "two", "three"]

        # Surely the unit test harness can yield the three above items in 1s
        self.assertSequenceEqual(seq, list(utils.itime(seq, 1000)))

        # Give a negative time and make sure at least one item is
        # returned
        self.assertSequenceEqual(["one"], list(utils.itime(seq, -1)))

        # Create a generator that yields one item every quarter second.
        def delay(items):
            for item in items:
                time.sleep(0.10)
                yield item

        # 0.00s: sleep
        # 0.10s: yield "one"
        # 0.20s: yield "two"
        # 0.30s: yield "three"

        # Make sure the right number of elements from seq are yielded
        # for various lengths of time.
        self.assertSequenceEqual(["one"],
                                 list(utils.itime(delay(seq), 0.05)))
        self.assertSequenceEqual(["one"],
                                 list(utils.itime(delay(seq), 0.15)))
        self.assertSequenceEqual(["one", "two"],
                                 list(utils.itime(delay(seq), 0.25)))
        self.assertSequenceEqual(["one", "two", "three"],
                                 list(utils.itime(delay(seq), 0.35)))
        self.assertSequenceEqual(["one", "two", "three"],
                                 list(utils.itime(delay(seq), 1.00)))
