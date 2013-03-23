# Copyright (C) 2013 Peter Teichman

import collections
import string


PosToken = collections.namedtuple("PosToken", "pos token")
NgramCount = collections.namedtuple("NgramCount", "ngram count")


def typedfilter(func, iterable):
    ret = filter(func, iterable)
    return type(iterable)(ret)


def tokenize_whitespace(s):
    return tuple(string.split(string.strip(s)))


def position(tokens):
    items = [PosToken(pos, token) for pos, token in enumerate(tokens)]
    return frozenset(items)
