# Copyright (C) 2012 Peter Teichman
# coding=utf8

import park
import unittest2 as unittest

from cobe import analysis
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

        self.assertEqual([u"foo"], list(norm.normalize(u"foo")))
        self.assertEqual([u"foo"], list(norm.normalize(u"Foo")))
        self.assertEqual([u"foo"], list(norm.normalize(u"FOO")))

        # Make sure accents are preserved, in contrast to AccentNormalizer
        self.assertEqual([u"foö"], list(norm.normalize(u"foö")))

        self.assertEqual([u"foo\nbar"], list(norm.normalize(u"FOO\nBar")))


class TestAccentNormalizer(unittest.TestCase):
    def test_normalize(self):
        norm = analysis.AccentNormalizer()

        self.assertEqual([u"foo"], list(norm.normalize(u"foö")))


class TestStemNormalizer(unittest.TestCase):
    def test_stemmer(self):
        norm = analysis.StemNormalizer("english")

        self.assertEqual(["foo"], list(norm.normalize("foo")))
        self.assertEqual(["jump"], list(norm.normalize("jumping")))
        self.assertEqual(["run"], list(norm.normalize("running")))

    def test_stemmer_case(self):
        norm = analysis.StemNormalizer("english")

        self.assertEqual(["foo"], list(norm.normalize("Foo")))
        self.assertEqual(["foo"], list(norm.normalize("FOO")))

        self.assertEqual(["foo"], list(norm.normalize("FOO'S")))
        self.assertEqual(["foo"], list(norm.normalize("FOOING")))
        self.assertEqual(["foo"], list(norm.normalize("Fooing")))


class AnalyzerTest(unittest.TestCase):
    def test_normalizer(self):
        class PrefixNormalizer(analysis.TokenNormalizer):
            def __init__(self, length, prefix=None):
                self.length = length
                super(PrefixNormalizer, self).__init__(prefix=prefix)

            def normalize(self, token):
                yield token[:self.length]

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

        self.assertEqual(expected, result)

    def test_normalizer_multiple(self):
        # Test a normalizer that maps a token to multiple things
        class BigramNormalizer(analysis.TokenNormalizer):
            def normalize(self, token):
                # Yield all 2-character sequences in token
                for i in xrange(len(token) - 1):
                    yield token[i:i + 2]

        norm = BigramNormalizer()
        self.assertEqual(["te", "er", "rm"], list(norm.normalize(u"term")))

        analyzer = analysis.WhitespaceAnalyzer()
        analyzer.add_token_normalizer(norm)

        expected = [
            ("BigramNormalizer", u"te"),
            ("BigramNormalizer", u"er"),
            ("BigramNormalizer", u"rm")
        ]

        self.assertEqual(expected, analyzer.normalize_token(u"term"))

    def test_normalizer_str(self):
        analyzer = analysis.WhitespaceAnalyzer()

        with self.assertRaises(TypeError):
            analyzer.normalize_token("non-unicode")

    def test_empty_normalizer(self):
        class EmptyNormalizer(analysis.TokenNormalizer):
            def normalize(self, token):
                # yield nothing
                return (i for i in [])

        analyzer = analysis.WhitespaceAnalyzer()
        analyzer.add_token_normalizer(EmptyNormalizer())

        self.assertEqual([], list(analyzer.normalize_token(u"Foobarbaz")))

    def test_conflated_query(self):
        analyzer = analysis.WhitespaceAnalyzer()
        analyzer.add_token_normalizer(analysis.LowercaseNormalizer())

        m = model.Model(analyzer, park.SQLiteStore(":memory:"))
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
