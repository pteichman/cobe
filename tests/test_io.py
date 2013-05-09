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

    def test_line_ngram(self):
        # input, expected
        tests = [
            ("foo\tbar\tbaz\t10\n", "foo\tbar\tbaz"),
            ("foo\tbar\t10\n", "foo\tbar"),
            ("foo\t10\n", "foo"),

            # the file will be utf-8 encoded, so test already-encoded
            # unicode byte strings
            (u"<∅>\tfoo\t1".encode("utf-8"), u"<∅>\tfoo".encode("utf-8")),
        ]

        for num, (test, expected) in enumerate(tests):
            self.assertEqual(expected, io.line_ngram(test),
                             "[%d] unexpected ngram" % num)

    def test_line_count(self):
        # input, expected
        tests = [
            ("foo\tbar\tbaz\t10\n", 10),
            ("foo\tbar\t10\n", 10),
            ("foo\t10\n", 10),
            (u"<∅>\tfoo\t1\n".encode("utf-8"), 1),
        ]

        for num, (test, expected) in enumerate(tests):
            self.assertEqual(expected, io.line_count(test),
                             "[%d] unexpected count" % num)

    def test_reverse_ngram(self):
        # input, expected
        tests = [
            ("foo\tbar\tbaz\t100\n", "bar\tbaz\tfoo\t100\n"),
            ("foo\tbar\t100\n", "bar\tfoo\t100\n"),

            # this shouldn't come up, but make sure the line isn't mangled
            ("foo\t100\n", "foo\t100\n"),
        ]

        for num, (test, expected) in enumerate(tests):
            self.assertEqual(expected, io.reverse_ngram(test),
                             "[%d] wrong reversed ngram")

    def test_line_prefix(self):
        # input, expected
        tests = [
            (("foo", "bar", "baz"), "foo\tbar\tbaz\t"),
            (("foo", "bar"), "foo\tbar\t"),
            (("foo",), "foo\t"),
        ]

        for num, (test, expected) in enumerate(tests):
            self.assertEqual(expected, io.line_prefix(test),
                             "[%d] wrong line prefix for ngram")
