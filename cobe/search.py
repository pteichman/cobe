# Copyright (C) 2012 Peter Teichman

import abc
import itertools
import operator
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
    def pivots(self, terms):
        """Generate pivots randomly chosen from query terms.

        If no terms from the query have been learned by the model,
        choose a random token from its token list.

        Yields:
            An infinite series of randomly chosen pivot terms.
        """
        model = self.model
        token_ids = model.tokens.token_ids

        texts = itertools.imap(operator.itemgetter("term"), terms)

        # Limit the choices to tokens that exist in the model. If none
        # have been seen, use all tokens.
        choices = [text for text in texts if text in token_ids]
        if not choices:
            choices = model.tokens.all_tokens

        choice = random.choice
        while True:
            yield choice(choices)

    def list_strip(self, items, ltoken, rtoken):
        """Strip tokens from the beginning and end of a list of items."""
        start = 0
        end = len(items)

        while items[start] == ltoken:
            start += 1

        while items[end - 1] == rtoken:
            end -= 1

        return items[start:end]

    def search(self, query):
        model = self.model
        start, end = model.TRAIN_START, model.TRAIN_END

        terms = query.terms

        def combine(prev_tokens, next_tokens):
            # The two overlap by len(context) tokens. Remove the
            # overlapping tokens and strip any extra leading/trailing
            # end tokens from the response.
            path = prev_tokens[1:] + next_tokens[len(context):-1]
            return self.list_strip(path, model.TRAIN_START, model.TRAIN_END)

        def random_walk(tokens):
            # walk randomly by choosing one random token at each
            # branch of the search tree.
            return [random.choice(tokens)]

        pivots = self.pivots(terms)

        while True:
            pivot = pivots.next()
            context = model.choose_random_context(pivot)

            next = model.search_bfs(context, end, filter=random_walk)
            prev = model.search_bfs_reverse(context, start, filter=random_walk)

            yield combine(prev.next(), next.next())
