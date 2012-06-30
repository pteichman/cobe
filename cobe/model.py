# Copyright (C) 2012 Peter Teichman

import leveldb
import logging
import math
import random
import varint

logger = logging.getLogger("cobe.model")


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
        """Load (token_text, token_id) pairs from an iterable."""
        for token, token_id in tokens:
            self._put(token, token_id)

    def _put(self, token, token_id):
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

            self._put(token, token_id)
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

    # Number of new logged n-grams before autosave forces a save
    SAVE_THRESHOLD = 300000

    def __init__(self, dbdir, orders=None):
        self.kv = leveldb.LevelDB(dbdir)

        if orders is None:
            # By default, count trigrams, bigrams, and unigrams
            orders = tuple(range(3, 0, -1))

        self.orders = orders

        self.tokens = TokenRegistry()
        self.counts_log = {}

        self.tokens.load(self._prefix_items("t/", skip_prefix=True))

    def _autosave(self):
        if len(self.counts_log) > self.SAVE_THRESHOLD:
            logging.info("Autosave triggered save")
            self.save()

    def _tokens_count_key(self, token_ids):
        return "c/" + "".join(token_ids)

    def _ngrams(self, grams, n):
        for i in xrange(0, len(grams) - n + 1):
            yield grams[i:i + n]

    def save(self):
        batch = leveldb.WriteBatch()

        logging.info("flushing new tokens")
        # First, flush any new token ids to the database
        for token, token_id in self.tokens.token_log:
            batch.Put("t/" + token, token_id)
        self.tokens.token_log[:] = []

        logging.info("merging counts")
        # Then merge in-memory ngram counts with the database
        for key, count in self.counts_log.iteritems():
            dbcount = varint.decode_one(self.kv.Get(key, default="\0"))
            batch.Put(key, varint.encode_one(dbcount + count))
        self.counts_log.clear()

        logging.info("writing batch")
        self.kv.Write(batch)

    def _train_sentence(self, tokens):
        tokens = ["<S>"] + tokens + ["</S>"]
        token_ids = map(self.tokens.get_id, tokens)

        counts_log = self.counts_log

        for order in self.orders:
            for ngram in self._ngrams(token_ids, order):
                key = self._tokens_count_key(ngram)

                counts_log.setdefault(key, 0)
                counts_log[key] += 1

    def train(self, tokens):
        self._train_sentence(tokens)
        self.save()

    def train_many(self, sentences):
        for sentence in sentences:
            self._train_sentence(sentence)
            self._autosave()

        self.save()

    def choose_random_word(self, context, rng=random):
        token_ids = map(self.tokens.get_id, context)

        key = self._tokens_count_key(token_ids)
        items = list(self._prefix_keys(key, skip_prefix=True))

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
        return math.log(self.ngram_count(tokens))

    def ngram_count(self, tokens):
        token_ids = map(self.tokens.get_id, tokens)
        key = self._tokens_count_key(token_ids)

        if len(token_ids) in self.orders:
            # If this ngram is a length we train, get the counts from
            # the database and counts log.
            count = varint.decode_one(self.kv.Get(key, default="\0"))
        else:
            # Otherwise, get this ngram's count by adding up all the
            # other ngrams that have it as a prefix.
            count = 0
            for key, value in self._prefix_items(key):
                count += varint.decode_one(value)

        return count

    def _prefix_items(self, prefix, skip_prefix=False):
        """yield all (key, value) pairs from keys that begin with $prefix"""
        items = self.kv.RangeIter(key_from=prefix, include_value=True)

        start = 0
        if skip_prefix:
            start = len(prefix)

        for key, value in items:
            if not key.startswith(prefix):
                break
            yield key[start:], value

    def _prefix_keys(self, prefix, skip_prefix=False):
        """yield all keys that begin with $prefix"""
        items = self.kv.RangeIter(key_from=prefix, include_value=False)

        start = 0
        if skip_prefix:
            start = len(prefix)

        for key in items:
            if not key.startswith(prefix):
                break
            yield key[start:]
