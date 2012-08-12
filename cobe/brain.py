# Copyright (C) 2012 Peter Teichman

import itertools
import logging

from cobe.analysis import (
    AccentNormalizer, StemNormalizer, TokenNormalizer, WhitespaceAnalyzer)
from cobe.kvstore import SqliteStore
from cobe.model import Model
from cobe.search import RandomWalkSearcher

log = logging.getLogger(__name__)


class StandardAnalyzer(WhitespaceAnalyzer):
    """A basic analyzer for test purposes.

    This combines a whitespace tokenizer with AccentNormalizer.

    """
    def __init__(self):
        super(StandardAnalyzer, self).__init__()

        self.add_token_normalizer(AccentNormalizer())
        self.add_token_normalizer(StemNormalizer("english"))


class Brain(object):
    """The all-in-one interface to a cobe stack."""
    def __init__(self, filename):
        self.analyzer = StandardAnalyzer()

        store = SqliteStore(filename)

        self.model = Model(self.analyzer, store)
        self.searcher = RandomWalkSearcher(self.model)

    def reply(self, text):
        # Create a search query from the input
        query = self.analyzer.query(text, self.model)

        result = itertools.islice(self.searcher.search(query), 1).next()
        return self.analyzer.join(result)

    def train(self, text):
        pass
