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
from cobe import utils


def touch(filename):
    with open(filename, "a"):
        os.utime(filename, None)


def lines(filename):
    with open(filename, "r") as fd:
        return [line[:-1] for line in fd.readlines()]


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

        ngram_files = [os.path.join(path, line) for line in lines(ngrams_idx)]
        self.ngrams = model.Ngrams.open(ngrams_log, ngram_files)

        return self

    def learn(self, text):
        tokens = unicode.split(text)

        for ngram in ng.ngrams(ng.sentence(tokens, 3), 3):
            self.ngrams.observe(ng.ngram(ngram))

    def replies(self, starts):
        # generate replies with a random walk
        scorer = lambda context, newcontext: random.random()

        fwd_complete = lambda ngram: self.ngrams.fwd_complete(
            ng.next_ngram_prefix(ngram))

        rev_complete = lambda ngram: self.ngrams.rev_complete(
            ng.next_ngram_prefix(ngram))

        fwd_iter = ng.search_bfs(self.fwd_chain_follow(fwd_follow), scorer,
                                 pivot_ngram, ng.END_TOKEN)
        rev_iter = ng.search_bfs(self.rev_chain_follow(rev_follow), scorer,
                                 pivot_ngram, ng.START_TOKEN)

        fwd = next(fwd_iter)
        rev = next(rev_iter)

        fwd_end = ng.one_gram(ng.END_TOKEN)
        fwd_finish = lambda ngram: ngram.endswith(fwd_end)

        rev_end = ng.one_gram(ng.START_TOKEN)
        rev_finish = lambda ngram: ngram.startswith(rev_end)

        fwd_iter = ng.search_bfs(fwd_complete, scorer, starts, fwd_finish)
        rev_iter = ng.search_bfs(rev_complete, scorer, path[0], rev_finish)

    def random_walk(self, context, newcontext):
        return random.random()

    def reply(self, text):
        tokens = unicode.split(text)

        pivot = ng.choice(tokens).encode("utf-8")
        pivots = self.ngrams.fwd_complete(ng.one_gram(pivot))

        if not pivots:
            # babble: pick a random pivot
            print "got no pivots!", [pivot]

        pivot_ngram = ng.choice(pivots)

        print "pivot_ngram is", [pivot_ngram]

        fwd_iter = self.fwd_replies(pivot_ngram)
        rev_iter = self.rev_replies(pivot_ngram)

        fwd = next(fwd_iter)
        rev = next(rev_iter)

        return self.join(rev, fwd)

    def fwd_replies(self, ngram):
        """Yield paths from ngram to END_TOKEN"""
        next_ngrams = lambda ngram: self.ngrams.fwd_complete(
            ng.next_ngram_prefix(ngram))

        end = 3 * (ng.END_TOKEN + "\t")
        finish = lambda ngram: ngram == end

        for path in ng.search_bfs(
            next_ngrams, self.random_walk, [ngram], finish):
            yield path

    def rev_replies(self, ngram):
        """Yield paths from START_TOKEN to ngram"""
        next_ngrams = lambda ngram: self.ngrams.rev_complete(
            ng.prev_ngram_prefix(ngram))

        end = 3 * (ng.START_TOKEN + "\t")
        finish = lambda ngram: ngram == end

        for path in ng.search_bfs(
            next_ngrams, self.random_walk, [ngram], finish):
            yield list(reversed(path))

    def join(self, rev, fwd):
        # skip the last ngram in rev, which is already shared with fwd
        ngrams = rev[:-1] + fwd

        skip = [ng.START_TOKEN, ng.END_TOKEN]

        def words(ngrams):
            for ngram in ngrams:
                word = ngram[:ngram.find("\t")]
                if word not in skip:
                    yield word

        return " ".join(words(ngrams))


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
