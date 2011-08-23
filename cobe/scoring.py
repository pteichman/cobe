# Copyright (C) 2011 Peter Teichman

import math
import re


class Scorer:
    def __init__(self, reverse=False):
        self.reverse = reverse

    def finish(self, score):
        if self.reverse:
            score = 1.0 - score

        return score

    def normalize(self, score):
        # map high-valued scores into 0..1
        if score < 0:
            return score

        return 1.0 - 1.0 / (1.0 + score)

    def score(self, input_tokens, output_tokens, db_cache):
        return NotImplementedError


class ScorerGroup:
    def __init__(self):
        self.scorers = []

    def add_scorer(self, weight, scorer):
        self.scorers.append((weight, scorer))

    def score(self, input_tokens, output_tokens, db):
        score = 0.

        for weight, scorer in self.scorers:
            score += weight * scorer.score(input_tokens, output_tokens, db)

        return score


class CobeScorer(Scorer):
    """Classic Cobe scorer, similar to MegaHAL's scorer but with bugs"""
    def __init__(self, order, **kwargs):
        Scorer.__init__(self, **kwargs)
        self.order = order

    def score(self, input_tokens, output_tokens, db):
        # If input_tokens is empty (i.e. we didn't know any words in
        # the input), use output == input to make sure we still check
        # scoring
        if len(input_tokens) == 0:
            input_tokens = output_tokens

        score = 0.

        # evaluate forward probabilities
        for output_idx in xrange(len(output_tokens) - self.order):
            output_token = output_tokens[output_idx + self.order]
            if output_token in input_tokens:
                expr = output_tokens[output_idx:output_idx + self.order]

                p = db.get_expr_token_probability("next_token", expr,
                                                  output_token)

                if p > 0:
                    score -= math.log(p, 2)

        # evaluate reverse probabilities
        for output_idx in xrange(len(output_tokens) - self.order):
            output_token = output_tokens[output_idx]
            if output_token in input_tokens:
                start = output_idx + 1
                end = start + self.order

                expr = output_tokens[start:end]

                p = db.get_expr_token_probability("prev_token", expr,
                                                  output_token)

                if p > 0:
                    score -= math.log(p, 2)

        raw_score = score

        # Prefer smaller replies. This behavior is present but not
        # documented in recent MegaHAL.
        score_divider = 1
        n_tokens = len(output_tokens)
        if n_tokens >= 8:
            score_divider = math.sqrt(n_tokens - 1)
        elif n_tokens >= 16:
            score_divider = n_tokens

        score = score / score_divider

        return self.finish(self.normalize(score))
