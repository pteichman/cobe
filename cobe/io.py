# Copyright (C) 2013 Peter Teichman
# coding=utf-8

"""I/O routines for cobe: n-gram file searches and indexing"""

# The two main questions that need to be answered by this database
# are:
#
# 1) What are the tokens that can follow an ngram (n1, n2)?
# (effectively: search for (n1, n2) and enumerate the next token)
#
# 2) How many times has ngram (n1, n2) been counted? (effectively: sum
# the counts for any line beginning "n1<tab>n2<tab>")

import collections
import operator

Line = collections.namedtuple("Line", "ngram count")


def token_ngrams(f, token):
    """Return all the ngrams starting with <token>"""
    prefix = line_prefix((token,))

    def line_ngram(line):
        return tuple(line_split(line).ngram.split("\t"))

    return frozenset(prefix_map(f, line_ngram, prefix))


def next_tokens(f, ngram):
    prefix = line_prefix(ngram)
    prefix_len = len(prefix)

    def next_token(line):
        rest = line[prefix_len:]
        return rest.split("\t", 1)[0]

    tokens = prefix_map(f, next_token, prefix)

    return frozenset(tokens)


def count(f, ngram):
    """Count the times an ngram has been seen"""
    def line_count(line):
        return line_split(line).count

    counts = prefix_map(f, line_count, line_prefix(ngram))

    return sum(counts)


def prefix_map(f, func, prefix):
    # Map func over the lines in fd that start with <prefix>
    search(f, prefix)

    cur = f.readline()
    while cur.startswith(prefix):
        yield func(cur)
        cur = f.readline()


def line_prefix(ngram):
    return "\t".join(ngram) + "\t"


def line_split(line):
    prefix, count = line.rsplit("\t", 1)
    return Line(prefix, int(count))


def search(f, prefix):
    """Search f for the position of the first line beginning with <prefix>"""
    beg, end = 0, length(f)

    while beg <= end:
        mid = beg + ((end - beg) / 2)

        f.seek(mid)
        f.readline()

        line = f.readline()
        if line >= prefix:
            end = mid - 1
        else:
            beg = mid + 1

    f.seek(beg)
    f.readline()

    return f.tell()


def length(f):
    old_pos = f.tell()

    try:
        f.seek(0, 2)
        return f.tell()
    finally:
        f.seek(old_pos, 0)
