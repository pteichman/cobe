# Copyright (C) 2012 Peter Teichman

import math


class Scorer:
    def __init__(self):
        self.cache = {}

    def end(self, reply):
        self.cache = {}

    def normalize(self, score):
        # map high-valued scores into 0..1
        if score < 0:
            return score

        return 1.0 - 1.0 / (1.0 + score)

    def score(self, reply):
        return NotImplementedError


class ScorerGroup:
    def __init__(self):
        self.scorers = []

    def add_scorer(self, weight, scorer):
        # add a scorer with a negative weight if you want to reverse
        # its impact
        self.scorers.append((weight, scorer))

        total = 0.
        for weight, scorers in self.scorers:
            total += abs(weight)
        self.total_weight = total

    def end(self, reply):
        for scorer in self.scorers:
            scorer[1].end(reply)

    def score(self, reply):
        # normalize to 0..1
        score = 0.
        for weight, scorer in self.scorers:
            s = scorer.score(reply)

            # make sure score is in our accepted range
            assert 0.0 <= score <= 1.0

            if weight < 0.0:
                s = 1.0 - s

            score += abs(weight) * s

        return score / self.total_weight


class CobeScorer(Scorer):
    """Classic Cobe scorer"""
    def score(self, reply):
        edge_ids = reply.edge_ids
        info = 0.

        logprob_cache = self.cache.setdefault("logprob", {})
        space_cache = self.cache.setdefault("has_space", {})

        get_edge_logprob = reply.graph.get_edge_logprob
        has_space = reply.graph.has_space

        # Calculate the information content of the edges in this reply.
        for edge_id in edge_ids:
            if edge_id not in logprob_cache:
                logprob_cache[edge_id] = get_edge_logprob(edge_id)

            info -= logprob_cache[edge_id]

        # Approximate the number of cobe 1.2 contexts in this reply, so the
        # scorer will have similar results.

        # First, we have (graph.order - 1) extra edges on either end of the
        # reply, since cobe 2.0 learns from (_END_TOKEN, _END_TOKEN, ...).
        n_words = len(edge_ids) - (reply.graph.order - 1) * 2

        # Add back one word for each space between edges, since cobe 1.2
        # treated those as separate parts of a context.
        for edge_id in edge_ids:
            if edge_id not in space_cache:
                space_cache[edge_id] = has_space(edge_id)

            if space_cache[edge_id]:
                n_words += 1

        # Double the score, since Cobe 1.x scored both forward and backward
        info *= 2.0

        # Comparing to Cobe 1.x scoring:
        # At this point we have an extra count for every space token
        # that adjoins punctuation. I'm tweaking the two checks below
        # for replies longer than 16 and 32 tokens (rather than our
        # original 8 and 16) as an adjustment. Scoring is an ongoing
        # project.

        if n_words > 16:
            info /= math.sqrt(n_words - 1)
        elif n_words >= 32:
            info /= n_words

        return self.normalize(info)


class InformationScorer(Scorer):
    """Score based on the information of each edge in the graph"""
    def score(self, reply):
        edge_ids = reply.edge_ids
        info = 0.

        logprob_cache = self.cache.setdefault("logprob", {})

        get_edge_logprob = reply.graph.get_edge_logprob

        # Calculate the information content of the edges in this reply.
        for edge_id in edge_ids:
            if edge_id not in logprob_cache:
                logprob_cache[edge_id] = get_edge_logprob(edge_id)

            info -= logprob_cache[edge_id]

        return self.normalize(info)


class LengthScorer(Scorer):
    def score(self, reply):
        return self.normalize(len(reply.edge_ids))
