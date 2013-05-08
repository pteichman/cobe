# Copyright (C) 2013 Peter Teichman
# coding=utf-8

import cStringIO as StringIO
import os
import unittest2 as unittest

from cobe import io

# ngram counts from cobe's README. Put in its own file for
# convenience, its tab characters are significant.

def datafile(filename):
    return os.path.join(os.path.dirname(__file__), filename)


with open(datafile("README.ngrams")) as fd:
    README = fd.read()


class TestIo(unittest.TestCase):
    def setUp(self):
        self.fwd = StringIO.StringIO(README)

    def tearDown(self):
        self.fwd.close()

    def test_count(self):
        def ngram(s):
            return tuple(s.split(" "))

        # first line of the file
        self.assertEqual(1, io.count(self.fwd, ngram("$ cobe console")))

        # somewhere in the middle
        self.assertEqual(1, io.count(self.fwd, ngram("on this graph")))

        # last line of the file
        self.assertEqual(1, io.count(self.fwd, ngram("word n-grams (default")))

        # not found
        self.assertEqual(0, io.count(self.fwd, ngram("foo bar baz")))

        # sum of a few ngrams
        self.assertEqual(2, io.count(self.fwd, ngram("the best")))
        self.assertEqual(10, io.count(self.fwd, ngram("the")))
