# Copyright (C) 2013 Peter Teichman

import itertools
import functools
import logging
import math
import os
import random
import string

from cobe import model
from cobe import ng


def touch(filename):
    with open(filename, "a"):
        os.utime(filename, None)


def lines(filename):
    with open(filename, "r") as fd:
        return fd.readlines()


class Brain(object):
    def __init__(self):
        self.path = None
        self.ngrams = model.Ngrams()

    @classmethod
    def open(cls, path):
        self = cls()
        self.path = os.path.normpath(path)

        def ensure(filename):
            fullpath = os.path.join(path, filename)
            touch(fullpath)
            return fullpath

        if not os.path.exists(path):
            os.makedirs(path)

        ngrams_log, ngrams_idx = map(ensure, ("ngrams.log", "ngrams.idx"))

        self.ngrams = model.Ngrams.open(ngrams_log, lines(ngrams_idx))

        return self

    def learn(self, text):
        tokens = unicode.split(text)

        for ngram in ng.ngrams(ng.sentence(tokens, 3), 3):
            self.ngrams.observe(ng.ngram(ngram))


class OldBrain(object):
    def __init__(self, path):
        if not os.path.isdir(path):
            os.mkdirs(path)

        fwd_fd, rev_fd = ng.open_ngram_counts(os.path.join(path, "ngrams"))

        def complete(fd):
            return functools.partial(ng.f_complete, fd)

        self.fwd_follow = frozenset([complete(fwd_fd)])
        self.rev_follow = frozenset([complete(rev_fd)])

    def reply(self, text):
        tokens = text.split()

        fwd_follow = self.follow_all(self.fwd_follow)
        rev_follow = self.follow_all(self.rev_follow)

        pivot = ng.choice(tokens)
        pivot_ngram = ng.choice(fwd_follow(pivot))

        # random walk
        scorer = lambda ng1, ng2: random.random()

        fwd_iter = ng.search_bfs(self.fwd_chain_follow(fwd_follow), scorer,
                                 pivot_ngram, ng.END_TOKEN)
        rev_iter = ng.search_bfs(self.rev_chain_follow(rev_follow), scorer,
                                 pivot_ngram, ng.START_TOKEN)

        fwd = next(fwd_iter)
        rev = next(rev_iter)

        return " ".join(ng.reply_join(fwd, rev)).decode("utf-8")

    def follow_all(self, funcs):
        def follow(ngram):
            all_ngrams = itertools.chain.from_iterable(
                func(ngram) for func in funcs)

            return frozenset(all_ngrams)

        return follow

    def fwd_chain_follow(self, followfunc):
        def chain_follow(ngram):
            return followfunc(ngram[ngram.find("\t") + 1:])

        return chain_follow

    def rev_chain_follow(self, followfunc):
        @functools.wraps(followfunc)
        def unreverse_set(ngram):
            return frozenset(map(ng.unreverse_ngram, followfunc(ngram)))

        def chain_follow(ngram):
            return unreverse_set(ngram[:ngram.rfind("\t", 0, -1) + 1])

        return chain_follow
