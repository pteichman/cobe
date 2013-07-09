# Copyright (C) 2013 Peter Teichman
# coding=utf-8

import heapq
import itertools
import mmap
import os
import random

"""Functions for ngram storage and manipulation.

An ngram is represented in this module as a string of tab-delimited
tokens. A tab follows the last token. Here are a few examples:

* "row" (unigram) -> "row\t"
* "row row" (bigram) -> "row\trow\t"
* "row row row" (trigram) -> "row\trow\trow\t"
* "row row row your boat" (5-gram) -> "row\trow\trow\tyour\tboat\t"

These ngrams are byte strings and are Unicode agnostic. Unicode
encoding and decoding should be done at a level above this module.

This module also contains routines for working with sorted files of
ngram counts. One ngram count per line, tab delimited as above:

row	row	2
row	your	1
your	boat	1

The lines in an ngram count file must be sorted in increasing order.

This module follows a mostly functional style of programming and has
been influenced by Rich Hickey's talks on simplicity:

* "Simple Made Easy"
   http://www.infoq.com/presentations/Simple-Made-Easy-QCon-London-2012
* "The Value of Values"
   http://www.infoq.com/presentations/Value-Values

As a result, these functions return immutable data structures where
possible. They are explicit about using sets when order is not
important.

"""

START_TOKEN = u"<∅>".encode("utf-8")
END_TOKEN = u"</∅>".encode("utf-8")


def is_ngram(ngram):
    """True if ngram looks like a cobe ngram string"""
    return isinstance(ngram, unicode) and ngram.endswith("\t")


def ngrams(grams, n):
    """Yield successive n-length ranges from grams

    Args:
        grams: sliceable list of tokens
        n: integer

    >>> list(ngrams(["row", "row", "row", "your", "boat"], 3))
    [('row', 'row', 'row'), ('row', 'row', 'your'), ('row', 'your', 'boat')]

    >>> list(ngrams(["row", "row", "row", "your", "boat"], 2))
    [('row', 'row'), ('row', 'row'), ('row', 'your'), ('your', 'boat')]

    >>> list(ngrams(["row", "row", "row", "your", "boat"], 1))
    [('row',), ('row',), ('row',), ('your',), ('boat',)]

    If grams is too short to supply an n-length slice, nothing will be
    returned:

    >>> list(ngrams(["row", "row", "row", "your", "boat"], 6))
    []

    """
    for i in xrange(0, len(grams) - n + 1):
        yield tuple(grams[i:i+n])


def one_gram(token):
    return token + "\t"


def ngram(tokens):
    return u"\t".join(tokens) + u"\t"


def sentence(tokens, n):
    return [START_TOKEN] * n + tokens + [END_TOKEN] * n


def choice(collection):
    """Return a random item from a collection.

    This behaves like Python's random.choice(), but it works with
    collections that cannot be indexed (sets).

    """
    return random.choice(list(collection))


def open_ngram_counts(fwdfile):
    revfile = "%s.rev" % fwdfile
    ensure_revfile(fwdfile, revfile)

    return f_mmap(fwdfile), f_mmap(revfile)


def ensure_revfile(fwdfile, revfile):
    """Create a file of reversed ngrams (if it doesn't exist already)

    These can be used to walk a series of ngrams toward the beginning
    of a sentence.

    """
    def reverse_line(line):
        return reverse_ngram(line_ngram(line)) + str(line_count(line)) + "\n"

    if not os.path.exists(revfile) \
            or os.path.getctime(fwdfile) > os.path.getctime(revfile):
        with open(fwdfile, "rb") as fwd:
            with open(revfile, "w+b") as rev:
                rev.writelines(sorted(itertools.imap(reverse_line, fwd)))

    return revfile


def next_ngram_prefix(ngram):
    start = ngram.find("\t") + 1
    return ngram[start:]


def prev_ngram_prefix(ngram):
    end = ngram.rfind("\t", 0, -1)
    return ngram[:end]


def reverse_ngram(ngram):
    """foo\tbar\tbaz\t -> bar\tbaz\tfoo\t"""
    start = ngram.find("\t") + 1
    return ngram[start:] + ngram[:start]


def unreverse_ngram(ngram):
    """bar\tbaz\tfoo\t -> foo\tbar\tbaz\t"""
    start = ngram.rfind("\t", 0, -1) + 1
    return ngram[start:] + ngram[:start]


def join(fwd, rev):
    """Join together the forward and reverse paths of a search result

    Each argument is a sequence of n-grams visited on the way to the
    search end.

    Example: "The quick brown fox jumps over the lazy dog"

    If the initial search context was "jumps over", join() would be
    passed these lists:

    fwd: [('jumps', 'over'), ('over', 'the'), ('the', 'lazy'),
          ('lazy', 'dog'), ('dog', '</∅>')]
    rev: [('jumps', 'over'), ('fox', 'jumps'), ('brown', 'fox'),
          ('quick', 'brown'), ('The', 'quick'), ('<∅>', 'The')]

    This function reverses rev and joins the terms together, returning:
    ('<∅>', 'The', 'quick', 'brown', 'fox', 'jumps', 'over', 'the',
     'lazy', 'dog', '</∅>')

    """
    def terms(contexts):
        # yield the first term from each context
        for context in contexts:
            yield context[:context.find("\t")]

        # yield everything remaining in the last context
        for term in context[context.find("\t")+1:-1].split("\t"):
            yield term

    # Skip the first element of rev because it's also in fwd.
    return tuple(terms(itertools.chain(reversed(rev[1:]), fwd)))


def many_ngrams(grams, orders):
    return itertools.chain(*(ngrams(grams, o) for o in orders))


def iter_ngrams(tokenize, iterable, orders=(3,)):
    """Yield the ngrams found in iterable.

    Args:
        tokenize: a function that takes a string and returns a token list
        iterable: an iterable of tokenizable text

    """
    for text in iterable:
        for each in many_ngrams(tokenize(text), orders):
            yield each


def one_counts(iter):
    return ((item, 1) for item in iter)


def f_open(filename):
    """open a read-only ngram file"""
    return open(filename, "rb")


def f_mmap(filename):
    """mmap a read-only ngram file"""
    with f_open(filename) as fd:
        return mmap.mmap(fd.fileno(), 0, prot=mmap.PROT_READ)


def f_count(f, ngram):
    """Count the times an ngram has been seen"""
    return sum(f_prefix_map(f, line_count, ngram))


def f_prefix_map(f, func, prefix):
    # Map func over the lines in fd that start with <prefix>
    f.seek(f_bisect(f, prefix))

    cur = f.readline()
    while cur.startswith(prefix):
        yield func(cur)
        cur = f.readline()


def line_count(line):
    """foo\tbar\tbaz\t10\n -> int(10)"""
    return int(line[line.rfind("\t")+1:-1])


def line_ngram(line):
    """foo\tbar\tbaz\t10\n -> foo\tbar\tbaz\t"""
    return line[:line.rfind("\t")+1]


def line_reverse(line):
    """foo\tbar\tbaz\t10 -> bar\tbaz\tfoo\t10"""
    token = line.find("\t")
    count = line.rfind("\t")

    return line[token+1:count+1] + line[:token] + line[count:]


def f_bisect(f, prefix):
    """Search fd for the position of the first line beginning with <prefix>"""
    beg, end = 0, f_length(f)

    while beg <= end:
        mid = beg + ((end - beg) / 2)

        f.seek(mid)
        f.readline()

        line = f.readline()
        if line == "" or line > prefix:
            end = mid - 1
        else:
            beg = mid + 1

    f.seek(beg)
    f.readline()

    return f.tell()


def f_length(f):
    old_pos = f.tell()

    try:
        f.seek(0, 2)
        return f.tell()
    finally:
        f.seek(old_pos, 0)


def f_complete(f, prefix):
    """Return the complete ngrams that start with <prefix>"""
    return tuple(f_prefix_map(f, line_ngram, prefix))


def search_bfs(followfunc, costfunc, contexts, finishfunc):
    """A breadth-first search across an adjacency list

    Args:
        followfunc: a function to map (n-gram) -> [(next ngram), (next ngram)]
        costfunc: a callback to evaluate the cost of a context
        context: the initial context to start the search
        end: the end token for the search

    This is a generator, and yields all possible search paths in
    ascending order of cost. A typical n-gram graph is cyclic, so this
    can mean infinite results.

    """
    heappop = heapq.heappop

    left = [(0.0, context, [context]) for context in contexts]
    while left:
        cost, context, path = heappop(left)

        if finishfunc(context):
            yield path
            continue

        for newcontext in followfunc(context):
            newpath = path + [newcontext]
            newcost = costfunc(context, newcontext)

            if newcost is not None:
                heapq.heappush(left, (cost + newcost, newcontext, newpath))


def merge_counts(*iters):
    """Merge the counts of already-sorted iterators of (item, count) pairs"""
    merge = heapq.merge(*iters)
    prev, accum = next(merge)

    for item, count in merge:
        if item == prev:
            accum += count
        else:
            yield prev, accum
            prev = item
            accum = count

    yield prev, accum
