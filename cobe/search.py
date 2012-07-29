# Copyright (C) 2012 Peter Teichman

import random


class Query(object):
    def __init__(self, terms):
        self.terms = terms


class Searcher(object):
    """Search and scoring."""
    def __init__(self, model):
        self.model = model

    def search(self, query):
        model = self.model
        terms = query.terms

        # Pick a random term and find a random context that contains it.
        pivot = random.choice(terms)
        context = model.choose_random_context(pivot["term"])

        next = model.search_bfs(context, "")
        prev = model.search_bfs_reverse(context, "")

        def combine(prev_tokens, next_tokens):
            # the two overlap by len(context) tokens
            return prev_tokens[1:] + next_tokens[len(context):-1]

        yield combine(prev.next(), next.next())
