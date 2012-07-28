# Copyright (C) 2012 Peter Teichman

import random


class Query(object):
    def __init__(self, tokens):
        self.tokens = tokens

    def terms(self):
        ret = []
        for index, token in enumerate(self.tokens):
            ret.append(dict(term=token, position=index))

        return ret


class Searcher(object):
    """Search and scoring."""
    def __init__(self, model):
        self.model = model

    def search(self, query):
        model = self.model
        terms = query.terms()

        # Pick a random term and find a random context that contains it.
        pivot = random.choice(terms)
        context = model.choose_random_context(pivot["term"])

        results = model.search_bfs(context, "")
        for result in results:
            yield result
