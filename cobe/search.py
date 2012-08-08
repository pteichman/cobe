# Copyright (C) 2012 Peter Teichman

import abc
import random


class Query(object):
    def __init__(self, terms):
        self.terms = terms


class Searcher(object):
    """An abstract class for searching a language model."""
    __metaclass__ = abc.ABCMeta

    def __init__(self, model):
        self.model = model

    @abc.abstractmethod
    def search(self, query):  # pragma: no cover
        pass


class RandomWalkSearcher(Searcher):
    """Search the language model by randomly choosing next words.

    This searcher behaves similarly to MegaHAL and creates its search
    results using the following procedure:

    1) Choose a random term from the input query.

    2) Choose a random n-gram context from the model that includes the term.

    3) From that context, follow the model's forward chain and
       generate the end of the response. At each stage of the chain,
       choose the next token randomly.

    4) Use the same procedure to walk the model's reverse chain to
       generate the beginning of the reponse.

    Yields:
        An infinite series of randomly generated responses to the query.
    """
    def search(self, query):
        model = self.model
        terms = query.terms

        def combine(prev_tokens, next_tokens):
            # the two overlap by len(context) tokens
            return prev_tokens[1:] + next_tokens[len(context):-1]

        def random_walk(tokens):
            # walk randomly by choosing one random token at each
            # branch of the search tree.
            return [random.choice(tokens)]

        while True:
            pivot = random.choice(terms)
            context = model.choose_random_context(pivot["term"])

            next = model.search_bfs(context, "", filter=random_walk)
            prev = model.search_bfs_reverse(context, "", filter=random_walk)

            yield combine(prev.next(), next.next())
