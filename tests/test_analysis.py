# Copyright (C) 2012 Peter Teichman
# coding=utf8

import unittest2 as unittest

from cobe import analysis
from cobe import kvstore
from cobe import model
from cobe import search


class LowercaseNormalizerTest(unittest.TestCase):
    def test_prefix(self):
        # Make sure the prefix of a TokenNormalizer subclass is
        # derived from the subclass's name.
        norm = analysis.LowercaseNormalizer()
        self.assertEqual("LowercaseNormalizer", norm.prefix)

        norm = analysis.LowercaseNormalizer(prefix="asdf")
        self.assertEqual("asdf", norm.prefix)

    def test_lowercase(self):
        norm = analysis.LowercaseNormalizer()

        self.assertEqual(u"foo", norm.normalize(u"foo"))
        self.assertEqual(u"foo", norm.normalize(u"Foo"))
        self.assertEqual(u"foo", norm.normalize(u"FOO"))

        # Make sure accents are preserved, in contrast to AccentNormalizer
        self.assertEqual(u"foö", norm.normalize(u"foö"))

        self.assertEqual(u"foo\nbar", norm.normalize(u"FOO\nBar"))


class TestAccentNormalizer(unittest.TestCase):
    def test_normalize(self):
        norm = analysis.AccentNormalizer()

        self.assertEqual(u"foo", norm.normalize(u"foö"))


class AnalyzerTest(unittest.TestCase):
    def test_normalizer(self):
        class PrefixNormalizer(analysis.TokenNormalizer):
            def __init__(self, length, prefix=None):
                self.length = length
                super(PrefixNormalizer, self).__init__(prefix=prefix)

            def normalize(self, token):
                return token[:self.length]

        # Create an analyzer and add a LowercaseNormalizer and this
        # PrefixNormalizer.
        analyzer = analysis.WhitespaceAnalyzer()

        ret = analyzer.add_token_normalizer(PrefixNormalizer(3))
        ret = analyzer.add_token_normalizer(analysis.LowercaseNormalizer())

        # Make sure add_token_normalizer returns the analyzer, for chaining
        self.assertIs(analyzer, ret)

        expected = [
            ("PrefixNormalizer", u"Foo"),
            ("LowercaseNormalizer", u"foobarbaz")
            ]

        result = analyzer.normalize_token(u"Foobarbaz")

        self.assertListEqual(expected, result)

    def test_normalizer_str(self):
        analyzer = analysis.WhitespaceAnalyzer()

        with self.assertRaises(TypeError):
            analyzer.normalize_token("non-unicode")

    def test_normalizer_returns_none(self):
        class NoneNormalizer(analysis.TokenNormalizer):
            def normalize(self, token):
                return None

        analyzer = analysis.WhitespaceAnalyzer()
        analyzer.add_token_normalizer(NoneNormalizer())

        result = analyzer.normalize_token(u"Foobarbaz")
        self.assertListEqual([], result)

    def test_conflated_query(self):
        analyzer = analysis.WhitespaceAnalyzer()
        analyzer.add_token_normalizer(analysis.LowercaseNormalizer())

        m = model.Model(analyzer, kvstore.SqliteStore(":memory:"))
        m.train(u"This is a test")
        m.train(u"this is a test")

        query = analyzer.query(u"this is a query", m)

        expected = [
            dict(term="this", pos=0),
            dict(term="This", pos=0),
            dict(term="is", pos=1),
            dict(term="a", pos=2),
            dict(term="query", pos=3)
            ]

        self.assertListEqual(expected, query.terms)


class WhitespaceAnalyzerTest(unittest.TestCase):
    def test_tokens_str(self):
        analyzer = analysis.WhitespaceAnalyzer()

        with self.assertRaises(TypeError):
            analyzer.tokens("non-unicode string")

    def test_tokens(self):
        analyzer = analysis.WhitespaceAnalyzer()

        # WhitespaceAnalyzer simply splits on whitespace.
        expected = ["foo", "bar", "baz"]

        self.assertListEqual(expected, analyzer.tokens(u"foo bar baz"))
        self.assertListEqual(expected, analyzer.tokens(u"foo  bar baz"))
        self.assertListEqual(expected, analyzer.tokens(u" foo bar baz"))
        self.assertListEqual(expected, analyzer.tokens(u"foo bar baz "))
        self.assertListEqual(expected, analyzer.tokens(u"foo bar baz\n"))
        self.assertListEqual(expected, analyzer.tokens(u"foo\nbar baz"))
        self.assertListEqual(expected, analyzer.tokens(u"\nfoo bar baz"))

    def test_join(self):
        analyzer = analysis.WhitespaceAnalyzer()
        self.assertEqual("foo bar baz", analyzer.join(["foo", "bar", "baz"]))

    def test_query(self):
        analyzer = analysis.WhitespaceAnalyzer()

        query = analyzer.query(u"foo bar baz")

        self.assertIsInstance(query, search.Query)

        expected_terms = [
            dict(term="foo", pos=0),
            dict(term="bar", pos=1),
            dict(term="baz", pos=2)
            ]

        self.assertItemsEqual(expected_terms, query.terms)


class TestMegaHALAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = analysis.MegaHALAnalyzer()

    def test_query(self):
        # MegaHALAnalyzer strips any non-word tokens when building its
        # query. None of the whitespace or punctuation tokens should
        # show up in the query.
        query = self.analyzer.query(u"this is a... test")

        expected = [dict(pos=0, term="THIS"),
                    dict(pos=2, term="IS"),
                    dict(pos=4, term="A"),
                    dict(pos=6, term="TEST")]

        self.assertEquals(expected, query.terms)
