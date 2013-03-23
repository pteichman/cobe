# Copyright (C) 2013 Peter Teichman

import array
import codecs
import heapq
import itertools
import math
import os
import struct
import types

from collections import defaultdict

from cobe import ng
#from cobe.model import TokenRegistry


class Tokenizer(object):
    def split(self, text):
        return text.split()

    def join(self, tokens):
        return " ".join(tokens)


class Model(object):
    """An ngram language model.

    Model is trained via its API and will reload itself on restart. It
    can be compactly frozen to disk.

    """
    def __init__(self, path, order):
        self.path = path
        self.order = order
        self.tokenizer = Tokenizer()

        self.counts = [defaultdict(int) for _ in xrange(order)]

        if not os.path.exists(path):
            os.makedirs(path)

        self.tokens = TokenRegistry(os.path.join(path, "tokens.log"))

        self.ngram_log = self._replay_ngram_log()

    def _replay_ngram_log(self):
        # replay the ngram log file and leave it open for appending
        filename = os.path.join(self.path, "ngram.log")

        def split(line):
            return line.split("\t")

        if os.path.exists(filename):
            with codecs.open(filename, "r", "utf-8") as fd:
                for ngrams in ng.transactions(itertools.imap(split, fd)):
                    map(self._train_ngrams, ngrams)

        return codecs.open(filename, "a", "utf-8")

    def _seen_ngram(self, ngram):
        self.counts[len(ngram) - 1][tuple(ngram)] += 1

    def _train_ngrams(self, grams):
        for ngram in ng.many_ngrams(grams, range(1, self.order + 1)):
            self._seen_ngram(ngram)

    def get_ngram_count(self, ngram):
        order = len(ngram)
        if not 0 < order <= self.order:
            raise ValueError("count for untracked ngram length: %d" % order)

        return self.counts[order - 1][tuple(ngram)]

    def train(self, text):
        if type(text) is not types.UnicodeType:
            raise TypeError("can only train Unicode text")

        # add beginning & end tokens and extract ngrams from text
        grams = [ng.START_TOKEN] + self.tokenizer.split(text) + [ng.END_TOKEN]

        for token in grams:
            # Make sure all tokens are in the token registry
            self.tokens.get_id(token)

        # Write the highest order ngrams to the log. The rest can be
        # recovered from those.
        for ngram in ng.ngrams(grams, self.order):
            # If we want to make the log robust to arbitrarily removed
            # lines, add an ngram sequence number to each line.
            self.ngram_log.write(u"\t".join(ngram) + "\n")

        self._train_ngrams(grams)

    def counts(self):
        return heapq.merge(self.mem_counts(), self.disk_counts())

    def disk_counts(self):
        pass

    def mem_counts(self):
        iters = [sorted(counts.iteritems()) for counts in self.counts]
        return heapq.merge(*iters)

    def freeze(self, ngram_counts):
        rec = struct.Struct(">III")
        buf = array.array("c", " " * rec.size)

        # Open a file for each set of n-grams and track the current
        # line number on each (1-indexed)
        def open_grams(n):
            fd = open(os.path.join(self.path, "%dgrams" % n), "w")

            # write a header record, junk for now
            head = "".join(itertools.islice(itertools.cycle("cobe"), rec.size))
            fd.write(head)
            return fd

        fds = [open_grams(n+1) for n in xrange(self.order)]

        # Current record number for each ngram file
        recnos = [0 for _ in xrange(self.order)]

        for ngram, count in ngram_counts:
            n = len(ngram)

            # write unigrams to 1grams.txt, bigrams to 2grams.txt, etc
            fd = fds[n-1]

            # increment the record count of the current file
            recnos[n-1] += 1

            # 1-grams have no context, but write zero for convenience.
            context = 0
            if len(ngram) > 1:
                # For 2-grams and above, this ngram's context is the
                # previous order's current record.
                context = recnos[n-2]

            token = ngram[-1]

            token_id = self.tokens.get_id(token)
            s = rec.pack_into(buf, 0, context, token_id, count)
            buf.tofile(fd)

        for fd in fds:
            fd.close()
