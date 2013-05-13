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
import itertools
import operator
import os

Line = collections.namedtuple("Line", "ngram count")


def token_ngrams(f, token):
    """Return all the ngrams starting with <token>"""
    prefix = ngram_join((token,))

    def line_ngram(line):
        return line_split(line).ngram

    return tuple(prefix_map(f, line_ngram, prefix))


def follow(f, ngram):
    prefix = ngram_join(ngram)

    def line_ngram(line):
        return line_split(line).ngram

    return tuple(prefix_map(f, line_ngram, prefix))


def follow_ngrams(f, ngram):
    return prefix_map(f, line_ngram, ngram + "\t")


def open_ngram_counts(fwdfile):
    revfile = "%s.rev" % fwdfile
    ensure_revfile(fwdfile, revfile)

    return open(fwdfile, "r"), open(revfile, "r")


def ensure_revfile(fwdfile, revfile):
    if not os.path.exists(revfile) \
            or os.path.getctime(fwdfile) > os.path.getctime(revfile):
        with open(fwdfile, "r") as fwd:
            with open(revfile, "w+b") as rev:
                rev.writelines(sorted(itertools.imap(reverse_line, fwd)))


def reverse_line(line):
    # "foo\tbar\tbaz\t1" => "bar\tbaz\tfoo\t1"
    token = line.find("\t")
    count = line.rfind("\t")

    return line[token+1:count+1] + line[:token] + line[count:]


def unreverse_ngram(ngram):
    index = ngram.rfind("\t")
    return ngram[index+1:] + "\t" + ngram[:index]


def next_tokens(f, ngram):
    prefix = ngram_join(ngram)
    prefix_len = len(prefix)

    def next_token(line):
        end = line.find("\t", prefix_len)
        return line[prefix_len:end]

    tokens = prefix_map(f, next_token, prefix)

    return tuple(set(tokens))


def count(f, ngram):
    """Count the times an ngram has been seen"""
    return sum(prefix_map(f, line_count, ngram_join(ngram)))


def line_count(line):
    """foo\tbar\tbaz\t10\n -> int(10)"""
    return int(line[line.rfind("\t")+1:-1])


def line_ngram(line):
    """foo\tbar\tbaz\t10\n -> foo\tbar\tbaz"""
    return line[:line.rfind("\t")]


def ngram_split(joined):
    """foo\tbar\tbaz -> tuple("foo", "bar", "baz")"""
    return tuple(joined.split("\t"))


def ngram_join(ngram):
    """tuple("foo", "bar", "baz") -> foo\tbar\tbaz\t"""
    return "\t".join(ngram) + "\t"


def prefix_map(f, func, prefix):
    # Map func over the lines in fd that start with <prefix>
    f.seek(search(f, prefix))

    cur = f.readline()
    while cur.startswith(prefix):
        yield func(cur)
        cur = f.readline()


def line_split(line):
    return Line(line_ngram(line), line_count(line))


def search(f, prefix):
    """Search f for the position of the first line beginning with <prefix>"""
    beg, end = 0, length(f)

    while beg <= end:
        mid = beg + ((end - beg) / 2)

        f.seek(mid)
        f.readline()

        line = f.readline()
        if line == "" or line >= prefix:
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
