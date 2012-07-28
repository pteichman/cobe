# Copyright (C) 2012 Peter Teichman

import unittest2 as unittest

from cobe import analysis
from cobe import search


class WhitespaceAnalyzerTest(unittest.TestCase):
    def test_tokens(self):
        analyzer = analysis.WhitespaceAnalyzer()

        # WhitespaceAnalyzer simply splits on whitespace.
        expected = ["foo", "bar", "baz"]

        self.assertListEqual(expected, analyzer.tokens("foo bar baz"))
        self.assertListEqual(expected, analyzer.tokens("foo  bar baz"))
        self.assertListEqual(expected, analyzer.tokens(" foo bar baz"))
        self.assertListEqual(expected, analyzer.tokens("foo bar baz "))
        self.assertListEqual(expected, analyzer.tokens("foo bar baz\n"))
        self.assertListEqual(expected, analyzer.tokens("foo\nbar baz"))
        self.assertListEqual(expected, analyzer.tokens("\nfoo bar baz"))

    def test_join(self):
        analyzer = analysis.WhitespaceAnalyzer()
        self.assertEqual("foo bar baz", analyzer.join(["foo", "bar", "baz"]))

    def test_query(self):
        analyzer = analysis.WhitespaceAnalyzer()

        tokens = analyzer.tokens("foo bar baz")
        query = analyzer.query(tokens)

        self.assertIsInstance(query, search.Query)

        expected_terms = [
            dict(term="foo", position=0),
            dict(term="bar", position=1),
            dict(term="baz", position=2)
            ]

        self.assertItemsEqual(expected_terms, query.terms())
