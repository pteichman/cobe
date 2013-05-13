# Copyright (C) 2013 Peter Teichman
# coding=utf-8

import cStringIO as StringIO
import os
import unittest2 as unittest

import cobe.ng as ng


def datafile(filename):
    return os.path.join(os.path.dirname(__file__), filename)


# ngram counts from cobe's README
with open(datafile("README.ngrams")) as fd:
    README = fd.read()


class TestNgrams(unittest.TestCase):
    def test_is_ngram(self):
        self.assertFalse(ng.is_ngram("foo"))
        self.assertTrue(ng.is_ngram("foo\t"))
        self.assertTrue(ng.is_ngram("foo\tbar\tbaz\t"))

    def test_choice(self):
        items = frozenset(["one", "two", "three"])

        for _ in xrange(10):
            self.assertIn(ng.choice(items), items)


class TestCounts(unittest.TestCase):
    def setUp(self):
        self.fwd = StringIO.StringIO(README)

    def tearDown(self):
        self.fwd.close()

    def test_length(self):
        with open(datafile("README.ngrams"), "r") as fd:
            self.assertEqual(5520, ng.f_length(fd))

    def test_count(self):
        def ngram(s):
            return "\t".join(s.split(" ")) + "\t"

        # first line of the file
        self.assertEqual(1, ng.f_count(self.fwd, ngram("$ cobe console")))

        # somewhere in the middle
        self.assertEqual(1, ng.f_count(self.fwd, ngram("on this graph")))

        # last line of the file
        self.assertEqual(1, ng.f_count(self.fwd,
                                       ngram("word n-grams (default")))

        # not found
        self.assertEqual(0, ng.f_count(self.fwd, ngram("foo bar baz")))

        # sum of a few ngrams
        self.assertEqual(2, ng.f_count(self.fwd, ngram("the best")))
        self.assertEqual(10, ng.f_count(self.fwd, ngram("the")))

    def test_line_ngram(self):
        # input, expected
        tests = [
            ("foo\tbar\tbaz\t10\n", "foo\tbar\tbaz\t"),
            ("foo\tbar\t10\n", "foo\tbar\t"),
            ("foo\t10\n", "foo\t"),

            # the README file is be utf-8 encoded, so test
            # already-encoded unicode byte strings
            (u"<∅>\tfoo\t1".encode("utf-8"), u"<∅>\tfoo\t".encode("utf-8")),
        ]

        for num, (test, expected) in enumerate(tests):
            self.assertEqual(expected, ng.line_ngram(test),
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
            self.assertEqual(expected, ng.line_count(test),
                             "[%d] unexpected count" % num)

    def test_line_reverse(self):
        # input, expected
        tests = [
            ("foo\tbar\tbaz\t100\n", "bar\tbaz\tfoo\t100\n"),
            ("foo\tbar\t100\n", "bar\tfoo\t100\n"),

            # this shouldn't come up, but make sure the line isn't mangled
            ("foo\t100\n", "foo\t100\n"),
        ]

        for num, (test, expected) in enumerate(tests):
            self.assertEqual(expected, ng.line_reverse(test),
                             "[%d] wrong reversed line" % num)

    def test_reverse_ngram(self):
        # input, expected
        tests = [
            ("foo\tbar\tbaz\t", "bar\tbaz\tfoo\t"),
            ("foo\tbar\t", "bar\tfoo\t"),
            ("foo\t", "foo\t"),
        ]

        for num, (test, expected) in enumerate(tests):
            self.assertEqual(expected, ng.reverse_ngram(test),
                             "[%d] wrong reversed ngram" % num)
        

    def test_unreverse_ngram(self):
        # input, expected
        tests = [
            ("bar\tbaz\tfoo\t", "foo\tbar\tbaz\t"),
            ("bar\tfoo\t", "foo\tbar\t"),
            ("foo\t", "foo\t"),
        ]

        for num, (test, expected) in enumerate(tests):
            self.assertEqual(expected, ng.unreverse_ngram(test),
                             "[%d] wrong unreversed ngram" % num)

    def test_complete(self):
        tests = [
            ("$\tcobe\t", ["$\tcobe\tconsole\t",
                           "$\tcobe\tinit\t",
                           "$\tcobe\tlearn\t"]),
            ("pip\t", ["pip\tinstall\tcobe\t"])
        ]

        for num, (test, expected) in enumerate(tests):
            self.assertSequenceEqual(expected, ng.f_complete(self.fwd, test))
