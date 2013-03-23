# Copyright (C) 2013 Peter Teichman
# coding=utf-8

import abc
import array
import bisect
import codecs
import collections
import itertools
import logging
import math
import os
import random
import struct
import types
import varint

from cobe import ng

logger = logging.getLogger(__name__)


class TokenRegistry(object):
    """Token registry for mapping tokens to integer ids.

    TokenRegistry assigns each unique token it sees an integer token
    id. These are allocated in the order the tokens are registered.

    New tokens are immediately logged to the registry file.

    """

    def __init__(self, filename):
        self.filename = filename

        # Two-way maps: token text to token id and back.
        self.token_ids = {}
        self.tokens = []

        # Replay the token log and leave it ready for appending new tokens
        self.token_log = self._replay_token_log(filename)

    def _replay_token_log(self, filename):
        if os.path.exists(filename):
            with open(filename, "r") as fd:
                for i, text in enumerate(fd):
                    assert text[-1] == "\n"
                    token = unicode(text[:-1], "utf-8")

                    assert token not in self.token_ids

                    token_id = self._append(token)
                    assert token_id == i

                    logger.debug("%s: replayed %d tokens", filename,
                                 len(self.tokens))

        return open(filename, "a")

    def _append(self, token):
        # Register the token, assigning the next available integer
        # as its id.
        assert token not in self.token_ids

        token_id = len(self.tokens)
        self.token_ids[token] = token_id
        self.tokens.append(token)

        return token_id

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
            self._append(token)
            self.token_log.write(token.encode("utf-8") + "\n")
            self.token_log.flush()

        return self.token_ids[token]

    def get_token(self, token_id):
        """Get the token associated with an id.

        Raises: KeyError if the token_id doesn't correspond to a
            registered token.

        """
        return self.tokens[token_id]


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

        self.counts = [collections.defaultdict(int) for _ in xrange(order)]

        # next / previous ngram adjacency lists
        self.next = []
        self.prev = []

        if not os.path.exists(path):
            os.makedirs(path)

        self.tokens = TokenRegistry(os.path.join(path, "tokens.log"))

        self.ngram_log = self._replay_ngram_log()

    def _replay_ngram_log(self):
        # replay the ngram log file and leave it open for appending
        filename = os.path.join(self.path, "ngram.log")

        def split(line):
            assert line[-1] == "\n"
            return line.split("\t")

        if os.path.exists(filename):
            with open(filename, "r") as fd:
                for ngrams in ng.transactions(itertools.imap(split, fd)):
                    map(self._train_ngrams, ngrams)

                self.next.sort()
                self.prev.sort()

        return codecs.open(filename, "a", "utf-8")

    def _seen_ngram(self, ngram):
        # counts object for this ngram's length
        counts = self.counts[len(ngram) - 1]

        t = tuple(ngram)
        if t not in counts:
            # train the next/prev adjacency lists
            self.next.append(t)
            self.prev.append(t[::-1])

        counts[t] += 1

    def _train_ngrams(self, grams):
        # Train the language model
        for ngram in ng.many_ngrams(grams, range(1, self.order + 1)):
            self._seen_ngram(ngram)

    def logprob(self, token, context):
        """The negative log probability of this token in this context."""
        def logcount(tokens):
            return math.log(self.get_ngram_count(tokens), 2)

        return logcount(context) - logcount(context + [token])

    def prob(self, token, context):
        """The negative log probability of this token in this context."""
        def count(tokens):
            return self.get_ngram_count(tokens)

        c1, c2 = count(context + [token]), count(context)
        if c2 == 0:
            return 0.0

        return float(c1) / c2

    def _wrap_split(self, text):
        # add beginning & end tokens and extract ngrams from text
        return [ng.START_TOKEN] + self.tokenizer.split(text) + [ng.END_TOKEN]

    def entropy(self, text):
        tokens = self._wrap_split(text)

        order = self.order
        context_len = order - 1

        entropy = 0.
        for index in xrange(len(tokens) - order):
            token = tokens[index + context_len]
            context = tokens[index:index + context_len]

            try:
                entropy += self.logprob(token, context)
            except ValueError:
                return 0.0

        return entropy

    def get_ngram_count(self, ngram):
        order = len(ngram)
        if not 0 < order <= self.order:
            raise ValueError("count for untracked ngram length: %d" % order)

        return self.counts[order - 1][tuple(ngram)]

    def train(self, text):
        if type(text) is not types.UnicodeType:
            raise TypeError("can only train Unicode text")

        tokens = self._wrap_split(text)

        for token in tokens:
            # Make sure all tokens are in the token registry
            self.tokens.get_id(token)

        # Write the highest order ngrams to the log. The rest can be
        # recovered from those.
        for ngram in ng.ngrams(tokens, self.order):
            # If we want to make the log robust to arbitrarily removed
            # lines, add an ngram sequence number to each line.
            self.ngram_log.write(u"\t".join(ngram) + "\n")

        self._train_ngrams(tokens)

    def train_counts(self, ngram_counts):
        """Train from ngrams directly"""
        pass

    def counts(self):
        return heapq.merge(self.mem_counts(), self.disk_counts())

    def disk_counts(self):
        return iter([])

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


class LanguageModel(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def prob(self, token, context):
        """Calculate the conditional probability P(token|context)."""
        pass

    @abc.abstractmethod
    def logprob(self, token, context):
        """The negative log probability of this token in this context."""
        pass

    @abc.abstractmethod
    def entropy(self, text):
        """Evaluate the total entropy of a text with respect to the model.

        This is the sum of the log probability of each token in the text.

        """
        pass


class OldModel(object):
    """An n-gram language model for online learning and text generation.

    cobe's Model is an unsmoothed n-gram language model.

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
    TRAIN_START = u"<∅>"
    TRAIN_END = u"</∅>"

    def __init__(self, analyzer, path, n=3):
        self.analyzer = analyzer
        self.path = path

        # Count n-grams, (n-1)-grams, ..., bigrams, unigrams
        # P(wordN|word1,word2,...,wordN-1)
        self.orders = tuple(range(n, 0, -1))

        if not os.path.exists(path):
            os.makedirs(path)

        self.tokens = TokenRegistry("tokens.log")

        # FIXME: create a memory model that includes an ngram log

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
