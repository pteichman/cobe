# Copyright (C) 2012 Peter Teichman

import park
import unittest2 as unittest

from cobe import analysis
from cobe import model
from cobe import search


class QueryTest(unittest.TestCase):
    def test_terms(self):
        terms = [
            dict(term="foo", position=0),
            dict(term="bar", position=1),
            dict(term="baz", position=2)
        ]

        query = search.Query(terms)
        self.assertEqual(terms, query.terms)


class RandomWalkSearcherTest(unittest.TestCase):
    def setUp(self):
        self.analyzer = analysis.WhitespaceAnalyzer()
        self.store = park.SQLiteStore(":memory:")
        self.model = model.Model(self.analyzer, self.store)

    def test_list_strip(self):
        searcher = search.RandomWalkSearcher(self.model)

        items = ["foo", "bar", "baz"]

        expected = ["foo", "bar", "baz"]
        self.assertListEqual(expected, searcher.list_strip(items, "", ""))

        expected = ["bar", "baz"]
        self.assertListEqual(expected,
                             searcher.list_strip(items, "foo", "foo"))

        expected = ["foo", "bar"]
        self.assertListEqual(expected,
                             searcher.list_strip(items, "baz", "baz"))

        items = ["foo", "bar", "baz", "foo"]
        expected = ["bar", "baz"]
        self.assertListEqual(expected,
                             searcher.list_strip(items, "foo", "foo"))

        items = ["foo", "foo", "bar", "baz", "foo", "foo"]
        expected = ["bar", "baz"]
        self.assertListEqual(expected,
                             searcher.list_strip(items, "foo", "foo"))

        items = ["foo", "foo", "bar", "baz", "foo", "bar"]
        expected = ["bar", "baz", "foo"]
        self.assertListEqual(expected,
                             searcher.list_strip(items, "foo", "bar"))

    def test_pivots(self):
        self.model.train(u"foo bar baz quux quuux")

        terms = [
            dict(term=u"foo", position=0),
            dict(term=u"bar", position=1),
            dict(term=u"baz", position=2)
        ]

        searcher = search.RandomWalkSearcher(self.model)

        # Make sure that a query with known terms doesn't pivot on
        # the other terms in the model (quux, quuux).
        pivots = searcher.pivots(terms)
        expected = self.analyzer.tokens(u"foo bar baz")

        for i in xrange(100):
            self.assertIn(pivots.next(), expected)

        # Make sure that a query with unknown terms can return any
        # token from the model.
        pivots = searcher.pivots([dict(term=u"unknown", position=0)])
        expected = self.analyzer.tokens(u"foo bar baz quux quuux")

        # model.TRAIN_START and model.TRAIN_END may also be picked up
        # as random pivots.
        expected.extend([self.model.TRAIN_START, self.model.TRAIN_END])

        for i in xrange(100):
            self.assertIn(pivots.next(), expected)

        # Make sure that a query with no terms can return any token
        # from the model.
        pivots = searcher.pivots([])

        for i in xrange(100):
            self.assertIn(pivots.next(), expected)

    def test_search(self):
        # Test random walk search by training a minimal set of data
        # and making sure each response is the only possible one.
        text = u"foo bar baz quux quuux"
        self.model.train(text)
        expected = self.analyzer.tokens(text)

        searcher = search.RandomWalkSearcher(self.model)

        query = search.Query([dict(term=u"foo", position=0)])
        self.assertEqual(expected, searcher.search(query).next())

        query = search.Query([dict(term=u"bar", position=0)])
        self.assertEqual(expected, searcher.search(query).next())

        query = search.Query([dict(term=u"quuux", position=0)])
        self.assertEqual(expected, searcher.search(query).next())
