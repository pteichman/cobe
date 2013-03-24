# Copyright (C) 2013 Peter Teichman
# coding=utf-8

import unittest2 as unittest

from cobe import ng

def tuplesplit(text):
    return tuple(text.split())


class TestNgrams(unittest.TestCase):
    def test_ngrams(self):
        tokens = "this is a test string for n-grams".split()

        # Test n=3
        ngrams = list(ng.ngrams(tokens, 3))
        expected = [("this", "is", "a"),
                    ("is", "a", "test"),
                    ("a", "test", "string"),
                    ("test", "string", "for"),
                    ("string", "for", "n-grams")]

        self.assertEquals(expected, ngrams)

        # Test n=2
        ngrams = list(ng.ngrams(tokens, 2))
        expected = [("this", "is"),
                    ("is", "a"),
                    ("a", "test"),
                    ("test", "string"),
                    ("string", "for"),
                    ("for", "n-grams")]

        self.assertEquals(expected, ngrams)

        # Test unigrams
        ngrams = list(ng.ngrams(tokens, 1))
        expected = [("this",), ("is",), ("a",), ("test",), ("string",),
                    ("for",), ("n-grams",)]

        self.assertEquals(expected, ngrams)

    def test_ngrams_short(self):
        tokens = "this is".split()

        # Test n=3 with a string that doesn't have any 3-grams
        ngrams = list(ng.ngrams(tokens, 3))
        expected = []

        self.assertEquals(expected, ngrams)


class TestCounts(unittest.TestCase):
    def test_dict_counts(self):
        # dict_counts returns the lexically sorted item tuples from
        # its argument. Use n-grams from cobe's README as test data.
        expected = [
            ("an", 1),
            ("an on-disk", 1),
            ("an on-disk data", 1),
            ("can", 3),
            ("can read", 2),
            ("can read about", 1),
            ("can read about its", 1)
        ]

        counts = ng.dict_counts(dict(expected))

        self.assertEqual(expected, counts)

    def test_merge_counts(self):
        expected = [
            ("an", 1),
            ("an on-disk", 1),
            ("an on-disk data", 1),
            ("can", 3),
            ("can read", 2),
            ("can read about", 1),
            ("can read about its", 1)
        ]

        items = dict(expected)

        # Merge a single source's items
        merge = ng.merge_counts(ng.dict_counts(items))
        self.assertEqual(expected, list(merge))

        items = {
            "one": 1,
            "two": 2
        }

        expected = [("one", 2), ("two", 4)]

        # Merge these items twice
        merge = ng.merge_counts(ng.dict_counts(items), ng.dict_counts(items))
        self.assertEqual(expected, list(merge))


class TestTransaction(unittest.TestCase):
    def test_transaction(self):
        ngrams = ng.ngrams(u"<∅> these are ngrams </∅>".split(), 3)

        expected = [
            [tuplesplit(u"<∅> these are"),
             tuplesplit(u"these are ngrams"),
             tuplesplit(u"are ngrams </∅>")]
            ]

        self.assertEqual(expected, list(ng.transactions(ngrams)))

        ngrams = ng.ngrams(
            u"<∅> these are ngrams </∅> <∅> these are more </∅>".split(), 3)

        expected = [
            [tuplesplit(u"<∅> these are"),
             tuplesplit(u"these are ngrams"),
             tuplesplit(u"are ngrams </∅>")],
            [tuplesplit(u"<∅> these are"),
             tuplesplit(u"these are more"),
             tuplesplit(u"are more </∅>")]
            ]

        self.assertEqual(expected, list(ng.transactions(ngrams)))

    def test_short_transaction(self):
        ngrams = ng.ngrams(u"<∅> these are ngrams".split(), 3)

        expected = []

        self.assertEqual(expected, list(ng.transactions(ngrams)))

    def test_restarted_transaction(self):
        ngrams = ng.ngrams(u"<∅> these <∅> these are ngrams </∅>".split(), 3)

        expected = [
            [tuplesplit(u"<∅> these are"),
             tuplesplit(u"these are ngrams"),
             tuplesplit(u"are ngrams </∅>")]
            ]

        self.assertEqual(expected, list(ng.transactions(ngrams)))
