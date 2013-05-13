# Copyright (C) 2013 Peter Teichman
# coding=utf-8

import collections
import heapq
import functools
import io
import itertools
import logging
import math
import operator
import os
import random
import re
import struct
import tempfile
import varint

from cobe import mem

START_TOKEN = u"<∅>"
END_TOKEN = u"</∅>"

Terms = collections.namedtuple("Terms", "tid_by_term term_by_tid")
Adjmap = collections.namedtuple("Adjmap", "next prev")

Brain = collections.namedtuple("Brain", "model tokenizer joiner")
NgramCount = collections.namedtuple("NgramCount", "ngram count")
QueryTerm = collections.namedtuple("QueryTerm", "term pos")


def register(terms, term):
    tid_by_term, term_by_tid = terms

    if term not in tid_by_term:
        tid = len(term_by_tid)
        term_by_tid.append(term)
        tid_by_term[term] = tid

    return tid_by_term[term]


def adjmap_add(adjlist, terms, ngram):
    """Add an ngram (if not already present) to an adjacency map

    add(("foo", "bar", "baz")) -> adjlist[("foo", "bar")].add("baz")

    """
    one, two = tuple(ngram[:-1]), tuple(ngram[1:])

    def listadd(l, elt):
        if elt not in l:
            l.append(elt)

    listadd(adjlist.next.setdefault(one, []), two)
    listadd(adjlist.prev.setdefault(two, []), one)

    return adjlist


def search_bfs(followfunc, costfunc, context, end):
    """A breadth-first search across an adjacency list

    Args:
        chain: a map of (n-gram context) -> [(next context 1), (next context 2)]
        costfunc: a callback to evaluate the cost of a context
        context: the initial context to start the search
        end: the end token for the search

    This is a generator, and yields all possible search paths in
    ascending order of cost. A typical n-gram graph is cyclic, so this
    can mean infinite results.

    """
    heappop = heapq.heappop

    left = [(0.0, context, [context])]
    while left:
        cost, context, path = heappop(left)
        if end in context:
            yield path
            continue

        for newcontext in followfunc(context):
            newpath = path + [newcontext]
            newcost = costfunc(context, newcontext)

            if newcost is not None:
                heapq.heappush(left, (cost + newcost, newcontext, newpath))


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


def ngram_counts(grams, orders):
    c = collections.Counter(many_ngrams(grams, orders))

    return frozenset(itertools.starmap(NgramCount, c.iteritems()))


def tokenize(text):
    return sentence(text.split())


def sentence(grams):
    """Wrap a sequence of grams in sentence start and end tokens

    >>> sentence(("row", "row", "row", "your", "boat"))
    (u'<\u2205>', 'row', 'row', 'row', 'your', 'boat', u'</\u2205>')

    """
    return (START_TOKEN,) + tuple(grams) + (END_TOKEN,)


def train(brain, text):
    t = sentence(brain.tokenizer(unicode(text)))

    counts = ngram_counts(t, range(1, brain.model.order + 1))

    brain.model.update_counts(counts)


def entropy(brain, text):
    t = sentence(brain.tokenizer(unicode(text)))

    log = math.log
    count = brain.model.get_count

    def logprob(ngram):
        return log(count(ngram[:-1])) - log(count(ngram))

    return sum(map(logprob, ngrams(t, brain.model.order)))


def query(brain, text):
    t = brain.tokenizer(unicode(text))

    base = (QueryTerm(term=term, pos=i) for i, term in enumerate(t))

    # TODO: conflate terms to synonyms (filtering unknown words)
    # TODO: filter stop words

    return frozenset(base)


def replies(adjmap, context):
    random_walk = lambda a, b: random.random()

    # Search the forward graph until END_TOKEN and reverse until START_TOKEN
    fwd = search_bfs(adjmap.next, random_walk, context, END_TOKEN)
    rev = search_bfs(adjmap.prev, random_walk, context, START_TOKEN)

    for fwdparts, revparts in itertools.izip(fwd, rev):
        # Generate one search result forward and one in reverse
        yield join(fwdparts, revparts)


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
            yield context[0]

        # yield everything remaining in the last context
        for term in context[1:]:
            yield term

    # Skip the first element of rev because it's also in fwd.
    return tuple(terms(itertools.chain(reversed(rev[1:]), fwd)))


def reply_one(brain, query):
    pivot = random.choice(list(query))

    # choose a random ngram starting with pivot
    # follow that context to the end
    # follow that context to the beginning

    return [pivot.term]


def reply(brain, text):
    q = query(brain, text)

    reply = reply_one(brain, q)

    return brain.joiner(reply)


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


def dict_counts(dictionary):
    """Return sorted item, count tuples from a dict of item -> count"""
    return sorted(dictionary.iteritems(), key=operator.itemgetter(0))


def transactions(generator):
    """yield ngram transactions, as bracketed by <∅> and </∅>"""
    pending = []

    for ngram in generator:
        if ngram[0] == START_TOKEN and len(pending) > 0:
            logging.warn("Skipping incomplete ngram transaction")
            pending = []

        pending.append(ngram)

        if ngram[-1] == END_TOKEN:
            yield pending
            pending = []

    if len(pending) > 0:
        logging.warn("Skipping incomplete ngram transaction at end")


def build_index(ngrams):
    #
    pass


def merge_counts(*iters):
    """Merge the counts on already-sorted iterators of (item, count) pairs"""
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


def choice(collection):
    return random.choice(list(collection))


def _flush_chunk(strs):
    fd, _ = tempfile.mkstemp()
    out = io.open(fd, mode="w+b")

    for s in strs:
        varint.write_one(len(s), out)
        out.write(s)

    # seek automatically writes the io stream's buffer
    out.seek(0)
    return out


def _read_chunk(fd):
    while 1:
        # read string length, then string
        l = varint.read_one(fd)
        if l is None:
            break
        yield fd.read(l)


def sorted_external(strs):
    """Sort the strings yielded by an iterable

    This operates externally when necessary, so the items need not fit
    into memory.

    """
    memitems = []
    chunks = []

    def close_after(iterable, chunks):
        try:
            for item in iterable:
                yield item
        finally:
            for c in chunks:
                c.close()

    for s in strs:
        if len(memitems) > 10000000:
            print "chunk"
            chunks.append(_flush_chunk(sorted(memitems)))
            memitems = []

    print "sorting"
    iters = [sorted(memitems)]
    iters.extend(_read_chunk(c) for c in chunks)

    print "merging"
    return close_after(heapq.merge(*iters), chunks)


def is_irssi_message(line):
    return re.match(r"\d\d:\d\d <", line)
