# Copyright (C) 2012 Peter Teichman

import collections
import logging
import math
import random
import varint

from .counter import MergeCounter

logger = logging.getLogger(__name__)


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

        # Log newly created tokens, so they can be flushed to the database
        self.token_log = []

    def load(self, tokens):
        """Load (token_id, token) pairs from an iterable."""
        for token_id, token in tokens:
            self._put(token_id, token)

    def _put(self, token_id, token):
        self.token_ids[token] = token_id
        self.tokens[token_id] = token

    def get_id(self, token):
        """Get the id associated with a token.

        This registers the token if is has not already been seen and
        returns the new token id.

        Args:
            token: A token string. Unicode and binary safe.
        """

        if token not in self.token_ids:
            # Register the token, assigning the next available integer
            # as its id.
            token_id = varint.encode_one(len(self.tokens))

            self._put(token_id, token)
            self.token_log.append((token, token_id))

        return self.token_ids[token]

    def get_token(self, token_id):
        """Get the token associated with an id.

        Raises: KeyError if the token_id doesn't correspond to a
            registered token.
        """
        return self.tokens[token_id]


class Model(object):
    """An n-gram language model for online learning and text generation.

    cobe's Model is an unsmoothed n-gram language model stored in a
    LevelDB database.

    Most language models focus on fast lookup and compact
    representation after a single massive training session. This one
    is designed to be incrementally trained throughout its useful
    life, retaining fast lookup with a less compact format on disk.

    This model is also designed for rapid generation of new sentences
    by following n-gram chains.

    Model attempts to provide API compatibility with NLTK's ModelI and
    NgramModel.
    """

    def __init__(self, analyzer, store, n=3):
        self.analyzer = analyzer
        self.store = store

        # Count n-grams, (n-1)-grams, ..., bigrams, unigrams
        # P(wordN|word1,word2,...,wordN-1)
        self.orders = tuple(range(n, 0, -1))

        self.tokens = TokenRegistry()

        # Leverage LevelDB's sorting to extract all tokens (the things
        # prefixed with the token key for an empty string)
        all_tokens = self._prefix_items(self._token_key(""),
                                        skip_prefix=True)
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

            for token, token_id in self.tokens.token_log:
                yield self._token_key(token_id), token
            self.tokens.token_log[:] = []

            # Then merge in-memory n-gram counts with the database
            logger.info("merging counts")

            for key, count in counts:
                val = self.store.get(key, default=None)
                if val is not None:
                    count += varint.decode_one(val)

                yield key, varint.encode_one(count)

        self.store.put_many(kv_pairs())

    def _ngram_keys_and_counts(self, tokens):
        # As each series of tokens is learned, pad the beginning and
        # end of phrase with n-1 empty strings.
        padding = [self.tokens.get_id("")] * (self.orders[0] - 1)

        token_ids = map(self.tokens.get_id, tokens)
        max_order = max(self.orders)

        for order in self.orders:
            to_train = padding[:order - 1] + token_ids + padding[:order - 1]

            # Count each n-gram we've seen
            for ngram in self._ngrams(to_train, order):
                yield self._tokens_count_key(ngram), 1

                if order == max_order:
                    # For the highest-order n-grams, also train their
                    # reverse. This allows dicovery of which tokens
                    # precede others. But don't bother tracking counts.
                    yield self._tokens_reverse_train_key(ngram), 0

    def train(self, text):
        self.train_many([text])

    def train_many(self, text_gen):
        tokenize = self.analyzer.tokens
        normalize = self.analyzer.normalize_token

        def ngram_counts():
            for text in text_gen:
                tokens = tokenize(text)

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
        token_id = self.tokens.get_id(token)

        prefix = self._tokens_count_key((token_id,), self.orders[0])
        items = list(self._prefix_keys(prefix, skip_prefix=True))

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

        items = list(self._prefix_keys(key, skip_prefix=True))

        if len(items):
            token_id = rng.choice(items)
            return self.tokens.get_token(token_id)

    def prob(self, token, context):
        """Calculate the conditional probability P(token|context)"""
        count = self.ngram_count(context + [token])
        count_all = self.ngram_count(context)

        return float(count) / count_all

    def logprob(self, token, context):
        """The negative log probability of this token in this context."""
        return self._logcount(context) - self._logcount(context + [token])

    def _logcount(self, tokens):
        return math.log(self.ngram_count(tokens), 2)

    def ngram_count(self, tokens):
        token_ids = map(self.tokens.get_id, tokens)

        key = self._tokens_count_key(token_ids)
        count = varint.decode_one(self.store.get(key, default="\0"))

        return count

    def _prefix_items(self, prefix, skip_prefix=False):
        """yield all (key, value) pairs from keys that begin with $prefix"""
        items = self.store.items(key_from=prefix)

        start = 0
        if skip_prefix:
            start = len(prefix)

        for key, value in items:
            if not key.startswith(prefix):
                break
            yield key[start:], value

    def _prefix_keys(self, prefix, skip_prefix=False):
        """yield all keys that begin with $prefix"""
        keys = self.store.keys(key_from=prefix)

        start = 0
        if skip_prefix:
            start = len(prefix)

        for key in keys:
            if not key.startswith(prefix):
                break
            yield key[start:]

    def _norm_key(self, prefix, norm, token=None):
        if token is None:
            token = ""
        else:
            token = self.tokens.get_id(token)

        return "/".join(("n", prefix, norm, token))

    def get_norm_tokens(self, prefix, norm):
        # Get any tokens that normalize to the same thing as norm
        key = self._norm_key(prefix, norm)
        get_token = self.tokens.get_token

        for token_id in self._prefix_keys(key, skip_prefix=True):
            yield get_token(token_id)

    def search_bfs(self, context, end, reverse=False):
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

            for next_token in self._prefix_keys(key, skip_prefix=True):
                left.append(path + (next_token,))

    def search_bfs_reverse(self, context, end):
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

            for prev_token in self._prefix_keys(key, skip_prefix=True):
                left.append((prev_token,) + path)
