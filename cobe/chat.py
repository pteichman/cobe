# Copyright (C) 2013 Peter Teichman
# coding=utf-8

import collections
import itertools
import logging
import math

from cobe import ng
from cobe import skiplist
from cobe import tokens


class Model(object):
    def __init__(self, order=3):
        self.order = order
        self.mem_counts = skiplist.Skiplist()

    def get_count(self, ngram):
        return self.mem_counts.get(ngram, 0)

    def update_counts(self, counts):
        # counts is a set of tokens.PosToken
        mem_counts = self.mem_counts
        for ngc in counts:
            count = mem_counts.get(ngc.ngram, 0)
            mem_counts.insert(ngc.ngram, count + ngc.count)

        for ngram, count in mem_counts.items():
            print "%s\t%d" % ("\t".join(ngram), count)
