# Copyright (C) 2012 Peter Teichman

import unittest2 as unittest

from cobe import search


class QueryTest(unittest.TestCase):
    def test_terms(self):
        tokens = "foo bar baz".split()
        query = search.Query(tokens)

        expected_terms = [
            dict(term="foo", position=0),
            dict(term="bar", position=1),
            dict(term="baz", position=2)
            ]

        self.assertItemsEqual(expected_terms, query.terms())
