# Copyright (C) 2012 Peter Teichman

import itertools
import logging
import math
import park

from cobe.analysis import (
    AccentNormalizer, StemNormalizer, WhitespaceAnalyzer)
from cobe.model import Model
from cobe.search import RandomWalkSearcher
from cobe.utils import itime

log = logging.getLogger(__name__)


class StandardAnalyzer(WhitespaceAnalyzer):
    """A basic analyzer for test purposes.

    This combines a whitespace tokenizer with an AccentNormalizer and
    English stemmer.

    """
    def __init__(self):
        super(StandardAnalyzer, self).__init__()

        self.add_token_normalizer(AccentNormalizer())
        self.add_token_normalizer(StemNormalizer("english"))


class Brain(object):
    """A simplified, cobe 2.x style interface.

    This behaves roughly like cobe 2.x with an English stemmer for
    now; more flexibility will come as the API is fleshed out.

    It generates replies with a random walk across the language model
    and scores candidate replies by entropy, with a penalty for
    too-long replies.

    """
    def __init__(self, filename):
        self.analyzer = StandardAnalyzer()

        store = park.SQLiteStore(filename)

        self.model = Model(self.analyzer, store)
        self.searcher = RandomWalkSearcher(self.model)

    def reply(self, text):
        # Create a search query from the input
        query = self.analyzer.query(text, self.model)

        # Track (and don't re-score) replies that have already been
        # seen. These are expected when using a random walk searcher,
        # but they're also useful when debugging searches.
        seen = set()

        join = self.analyzer.join
        entropy = self.model.entropy

        def score(reply):
            joined = join(reply)
            if joined in seen:
                return -1.0, joined

            seen.add(joined)
            n_tokens = len(reply)

            # Penalize longer replies (cobe 2.x compatibility)
            penalty = 1.0
            if n_tokens > 16:
                penalty = math.sqrt(n_tokens)
            elif n_tokens > 32:
                penalty = n_tokens

            joined = join(reply)
            return entropy(joined) / penalty, joined

        # This search is a generator; it doesn't start evaluating until read
        search = itime(self.searcher.search(query), 0.5)

        # Generate and score the search results.
        results = sorted(itertools.imap(score, search))

        if log.isEnabledFor(logging.DEBUG):
            for score, text in results:
                log.debug("%.4f %s", score, text)

            log.debug("made %d replies (%d unique)", len(results), len(seen))

        score, reply = results[-1]
        return reply

    def train(self, text):
        return self.model.train(text)

    def train_many(self, text_gen):
        return self.model.train_many(text_gen)
