# Copyright (C) 2013 Peter Teichman

import collections
import itertools
import logging
import math
import os
import random
import types
import varint

from cobe import io
from cobe import ng
from cobe import skiplist

from .counter import MergeCounter

logger = logging.getLogger(__name__)


def touch(filename):
    with open(filename, "w") as fd:
        pass


def lines(filename):
    with open(filename, "r") as fd:
        return fd.readlines()


def flatten(iters):
    return (elem for item in iters for elem in item)


class TokenLog(object):
    """An on-disk persisted set of Unicode token strings"""
    def __init__(self):
        self.tokens = set()
        self.log = None

    @classmethod
    def open(cls, filename):
        self = cls()
        self.log = io.open_linelog(filename, self.tokens.add)
        return self

    def close(self):
        if self.log is not None:
            self.log = None

    def add(self, token):
        if not isinstance(token, unicode):
            raise TypeError("token must be unicode")

        if token not in self.tokens:
            self.tokens.add(token)
            self.log(token)
            return True


class MemCounts(skiplist.Skiplist):
    """An in-memory data structure for online counting of observed ngrams

    This must be able to provide the same data as a sorted ngram file:

    1) observed counts of each ngram
    2) given a prefix (n-1)-gram, the list of ngrams with that prefix
    3) given a suffix (n-1)-gram, the list of ngrams with that suffix

    It's currently implemented with two skiplists: one for prefix
    queries and one for suffix queries. This provides O(lg N) lookups
    for counts and O(n) ngram enumeration after an O(lg N) search for
    the prefix/suffix queries.

    """
    def observe(self, ngram):
        assert ng.is_ngram(ngram)
        self.insert(ngram, self.get(ngram, 0) + 1)

    def get_count(self, ngram):
        return self.get(ngram, 0)

    def complete(self, prefix):
        node = self._find_prev(prefix)

        while node is not None and node[0].startswith(prefix):
            yield node[0]
            node = node[2]


class Ngrams(object):
    def __init__(self):
        self.log = None
        self.fwd_mem = MemCounts()
        self.rev_mem = MemCounts()

        self.files = []
        self.fwd_fds = []
        self.rev_fds = []

    @classmethod
    def open(cls, ngrams_log, files):
        self = cls()

        self.files = files
        self.fwd_fds, self.rev_fds = zip(*map(ng.open_ngram_counts, self.files))

        # replay any logged ngrams into MemCounts
        def insert_ngram(ngram):
            self.fwd_mem.observe(ngram)
            self.rev_mem.observe(ng.reverse_ngram(ngram))

        self.log = io.open_linelog(ngrams_log, insert_ngram)

        return self

    def close(self):
        self.log.close()
        for fd in self.fwd_fds:
            fd.close()

    def observe(self, ngram):
        assert ng.is_ngram(ngram)

        encoded = ngram.encode("utf-8")
        self.log(ngram)
        self.fwd_mem.observe(encoded)
        self.rev_mem.observe(ng.reverse_ngram(encoded))

    def get_count(self, ngram):
        return self.fwd.get(ngram, 0) + \
            sum(ng.f_count(fd, ngram) for fd in self.fwd_fds)

    def fwd_complete(self, ngram):
        return set(ng.f_complete(self.fwd_fds[0], ngram))

    def rev_complete(self, ngram):
        rev_ngrams = ng.f_complete(self.rev_fds[0], ngram)
        return set(map(ng.unreverse_ngram, rev_ngrams))


class TokenRegistry(object):
    """Token registry for mapping strings to shorter values.

    TokenRegistry assigns each unique token it sees an opaque token
    id. These are allocated in the order the tokens are registered,
    and they will increase in length as more tokens are known.

    The opaque token ids are currently strings.

    """

    def __init__(self):
        # Two-way maps: token text to token id and back.
        self.token_ids = {}
        self.tokens = {}

        # Maintain a list of all the token texts, so a random walk can
        # quickly pick a random learned token. This skips the empty
        # token "", used for signaling the end of trained text.
        self.all_tokens = []

        # Log newly created tokens, so they can be flushed to the
        # database. This class handles converting the Unicode tokens
        # to and from bytes.
        self.token_log = []

    def load(self, tokens):
        """Load (token_id, token) pairs from an iterable."""
        for token_id, token in tokens:
            self._put(token_id, token.decode("utf-8"))

    def _put(self, token_id, token):
        self.token_ids[token] = token_id
        self.tokens[token_id] = token

        # Skip the empty token in all_tokens
        if token != "":
            self.all_tokens.append(token)

    def get_id(self, token):
        """Get the id associated with a token.

        This registers the token if is has not already been seen and
        returns the new token id.

        Args:
            token: A token string. Unicode and binary safe.
        """

        if not isinstance(token, types.UnicodeType):
            raise TypeError("token must be Unicode")

        if token not in self.token_ids:
            # Register the token, assigning the next available integer
            # as its id.
            token_id = varint.encode_one(len(self.tokens))

            self._put(token_id, token)
            self.token_log.append((token.encode("utf-8"), token_id))

        return self.token_ids[token]

    def get_token(self, token_id):
        """Get the token associated with an id.

        Raises: KeyError if the token_id doesn't correspond to a
            registered token.

        """
        return self.tokens[token_id]


class Model(object):
    """An n-gram language model for online learning and text generation.

    cobe's Model is an unsmoothed n-gram language model keptb in a
    key-value store.

    Most language models focus on fast lookup and compact
    representation after a single massive training session. This one
    is designed to be incrementally trained throughout its useful
    life, retaining fast lookup with a less compact format on disk.

    This model is also designed for rapid generation of new sentences
    by following n-gram chains.

    Model attempts to provide API compatibility with NLTK's ModelI and
    NgramModel.

    """

    # Reserve two tokens that will be inserted before & after every
    # bit of trained text. These can be used by a search to find the
    # beginning or end of trained data.

    # Use binary values 0x02 (start of text) and 0x03 (end of text)
    # since they're unlikely to be used in this otherwise
    # text-oriented language model.
    TRAIN_START = u"\x02"
    TRAIN_END = u"\x03"

    def __init__(self, analyzer, store, n=3):
        self.analyzer = analyzer
        self.store = store

        # Count n-grams, (n-1)-grams, ..., bigrams, unigrams
        # P(wordN|word1,word2,...,wordN-1)
        self.orders = tuple(range(n, 0, -1))

        self.tokens = TokenRegistry()

        # Leverage LevelDB's sorting to extract all tokens (the things
        # prefixed with the token key for an empty string)
        token_prefix = self._token_key("")
        all_tokens = self.store.prefix_items(token_prefix, strip_prefix=True)

        self.tokens.load(all_tokens)

    def _token_key(self, token_id):
        return "t" + token_id

    def _tokens_count_key(self, token_ids, n=None):
        # Allow n to be overridden to look for keys of higher orders
        # that begin with these token_ids
        if n is None:
            n = len(token_ids)
        return str(n) + "".join(token_ids)

    def _tokens_reverse_train_key(self, token_ids):
        # token_ids are e.g. [ token1, token2, token3 ]. Rotate the
        # tokens to [ token2, token3, token1 ] so the tokens that
        # precede [ token2, token3 ] can be enumerated.
        return "r" + "".join(token_ids[1:]) + token_ids[0]

    def _tokens_reverse_key(self, token_ids):
        # token_ids are e.g. [ token1, token2, token3 ]. Rotate the
        # tokens to [ token2, token3, token1 ] so the tokens that
        # precede [ token2, token3 ] can be enumerated.
        return "r" + "".join(token_ids)

    def _ngrams(self, grams, n):
        for i in xrange(0, len(grams) - n + 1):
            yield grams[i:i + n]

    def _save(self, counts):
        def kv_pairs():
            # First, flush any new token ids to the database
            logger.info("flushing new tokens")

            token_key = self._token_key
            for token, token_id in self.tokens.token_log:
                yield token_key(token_id), token
            self.tokens.token_log[:] = []

            # Then merge in-memory n-gram counts with the database
            logger.info("merging counts")

            get = self.store.get
            decode_one = varint.decode_one
            encode_one = varint.encode_one

            for key, count in counts:
                val = get(key, default=None)
                if val is not None:
                    count += decode_one(val)

                yield key, encode_one(count)

        self.store.put_many(kv_pairs())

    def _ngram_keys_and_counts(self, tokens):
        # As each series of tokens is learned, pad the beginning and
        # end of phrase with start and end tokens.
        token_ids = map(self.tokens.get_id, tokens)

        max_order = max(self.orders)
        pad_start = [self.tokens.get_id(self.TRAIN_START)] * max_order
        pad_end = [self.tokens.get_id(self.TRAIN_END)] * max_order

        padded = pad_start + token_ids + pad_end

        for order in self.orders:
            # For each order smaller than our longest order, skip the
            # first few tokens in the list. This is to solve problems
            # of duplicate counts:
            #
            # [ TRAIN_START, TRAIN_START, TRAIN_START, "foo", "bar", ... ]
            #
            # Without skipping, training the above would count the
            # bigram [ TRAIN_START, TRAIN_START ] twice, breaking the
            # probability calculations for P(foo|TRAIN_START,TRAIN_START).

            to_train = padded

            to_skip = max_order - order
            if to_skip > 0:
                to_train = to_train[to_skip:-to_skip]

            # Emit a count of 1 for each n-gram in the training list
            for ngram in self._ngrams(to_train, order):
                yield self._tokens_count_key(ngram), 1

                if order == max_order:
                    # For the highest-order n-grams, also train their
                    # reverse. This allows dicovery of which tokens
                    # precede others. But don't bother tracking counts.
                    yield self._tokens_reverse_train_key(ngram), 0

    def train(self, text):
        if not isinstance(text, types.UnicodeType):
            raise TypeError("Training text must be Unicode")

        self.train_many([text])

    def train_many(self, text_gen):
        tokenize = self.analyzer.tokens
        normalize = self.analyzer.normalize_token
        max_order = max(self.orders)

        def ngram_counts():
            for text in text_gen:
                if not isinstance(text, types.UnicodeType):
                    raise TypeError("Training text must be Unicode")

                tokens = tokenize(text)

                # Don't bother learning text that's shorter than our
                # longest order. This is traditional cobe behavior and
                # may not be right if using Model as a language model.
                if len(tokens) < max_order:
                    continue

                # Register the normalizations of any new tokens
                for token in tokens:
                    if token not in self.tokens.token_ids:
                        for prefix, norm in normalize(token):
                            yield self._norm_key(prefix, norm, token), 0

                for item in self._ngram_keys_and_counts(tokens):
                    yield item

        counts = MergeCounter().count(ngram_counts())
        self._save(counts)

    def choose_random_context(self, token, rng=random):
        if not isinstance(token, types.UnicodeType):
            raise TypeError("token must be Unicode")

        token_id = self.tokens.get_id(token)

        prefix = self._tokens_count_key((token_id,), self.orders[0])
        items = list(self.store.prefix_keys(prefix, strip_prefix=True))

        if len(items):
            context = rng.choice(items)

            # FIXME: this is a terrible way to split the token ids
            token_ids = map(varint.encode_one, varint.decode(context))

            return [token] + map(self.tokens.get_token, token_ids)

    def choose_random_word(self, context, rng=random):
        token_ids = map(self.tokens.get_id, context)

        # Look for the keys that have one more token but are prefixed
        # with the key for token_ids
        key = self._tokens_count_key(token_ids, len(token_ids) + 1)

        items = list(self.store.prefix_keys(key, strip_prefix=True))

        if len(items):
            token_id = rng.choice(items)
            return self.tokens.get_token(token_id)

    def prob(self, token, context):
        """Calculate the conditional probability P(token|context)."""
        count = self.ngram_count(context + [token])
        count_all = self.ngram_count(context)

        return float(count) / count_all

    def logprob(self, token, context):
        """The negative log probability of this token in this context."""
        return self._logcount(context) - self._logcount(context + [token])

    def _logcount(self, tokens):
        return math.log(self.ngram_count(tokens), 2)

    def entropy(self, text):
        """Evaluate the total entropy of a text with respect to the model.

        This is the sum of the log probability of each token in the text.

        """
        if not isinstance(text, types.UnicodeType):
            raise TypeError("text must be Unicode")

        # Pad the beginning and end of the list with max_order-1 empty
        # strings. This allows us to get the probabilities for the
        # beginning and end of the phrase.
        max_order = max(self.orders)

        pad_start = [self.TRAIN_START] * (max_order - 1)
        pad_end = [self.TRAIN_END] * (max_order - 1)

        tokens = pad_start + self.analyzer.tokens(text) + pad_end

        context_len = max_order - 1

        entropy = 0.
        for index in xrange(len(tokens) - max_order):
            token = tokens[index + context_len]
            context = tokens[index:index + context_len]

            entropy += self.logprob(token, context)

        return entropy

    def ngram_count(self, tokens):
        token_ids = map(self.tokens.get_id, tokens)

        key = self._tokens_count_key(token_ids)
        count = varint.decode_one(self.store.get(key, default="\0"))

        return count

    def _norm_key(self, prefix, norm, token=None):
        if token is None:
            token = ""
        else:
            token = self.tokens.get_id(token)

        if isinstance(norm, types.UnicodeType):
            # For convenience, a normalizer may emit unicode norms
            # (this makes it easy to normalize on e.g. token.lower()).
            # Encode unicode norms to strings before putting them in the
            # store.
            norm = norm.encode("utf-8")

        return "/".join(("n", prefix, norm)) + chr(0) + token

    def get_norm_tokens(self, prefix, norm):
        # Get any tokens that normalize to the same thing as norm
        key = self._norm_key(prefix, norm)
        get_token = self.tokens.get_token

        for token_id in self.store.prefix_keys(key, strip_prefix=True):
            yield get_token(token_id)

    def search_bfs(self, context, end, filter=None):
        if not isinstance(end, types.UnicodeType):
            raise TypeError("end token must be Unicode")

        end_token = self.tokens.get_id(end)

        token_ids = tuple(map(self.tokens.get_id, context))

        left = collections.deque([token_ids])
        n = self.orders[0] - 1

        while left:
            path = left.popleft()
            if path[-1] == end_token:
                yield map(self.tokens.get_token, path)
                continue

            # Get the n-length key prefix for the last (n-1) tokens in
            # the current path
            token_ids = path[-n:]
            key = self._tokens_count_key(token_ids, len(token_ids) + 1)

            next_tokens = list(self.store.prefix_keys(key, strip_prefix=True))
            if next_tokens and filter is not None:
                next_tokens = filter(next_tokens)

            for next_token in next_tokens:
                left.append(path + (next_token,))

    def search_bfs_reverse(self, context, end, filter=None):
        if not isinstance(end, types.UnicodeType):
            raise TypeError("end token must be Unicode")

        end_token = self.tokens.get_id(end)

        token_ids = tuple(map(self.tokens.get_id, context))

        left = collections.deque([token_ids])
        n = self.orders[0] - 1

        while left:
            path = left.popleft()
            if path[0] == end_token:
                yield map(self.tokens.get_token, path)
                continue

            token_ids = path[:n]
            key = self._tokens_reverse_key(token_ids)

            prev_tokens = list(self.store.prefix_keys(key, strip_prefix=True))
            if prev_tokens and filter is not None:
                prev_tokens = filter(prev_tokens)

            for prev_token in prev_tokens:
                left.append((prev_token,) + path)
