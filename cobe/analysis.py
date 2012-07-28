# Copyright (C) 2012 Peter Teichman

import abc
import logging

from . import search

logger = logging.getLogger(__name__)


class TokenNormalizer(object):
    """Apply a normalization step to learned tokens.

    This allows many different tokens to be considered equivalent for
    querying purposes.
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, prefix=None):
        """A key prefix for namespacing items in the data store.

        Args:
            prefix: a namespace for storing the result of this
                normalization step in the data store.
        """
        self.prefix = prefix or self.__class__.__name__

    @abc.abstractmethod
    def normalize(self, token):  # pragma: no cover
        """Normalize a single token."""
        pass


class LowercaseNormalizer(TokenNormalizer):
    """Normalize tokens by lowercasing their text."""
    def normalize(self, token):
        return token.lower()


class Analyzer(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        self.token_normalizers = []

    @abc.abstractmethod
    def tokens(self, input):  # pragma: no cover
        """Split the input into a sequence of learnable tokens."""
        pass

    @abc.abstractmethod
    def join(self, tokens):  # pragma: no cover
        """Join a tokens list into a response string."""
        return " ".join(tokens)

    def add_token_normalizer(self, token_normalizer):
        """Append a token normalizer to this analyzer's list."""
        self.token_normalizers.append(token_normalizer)
        return self

    def normalize_token(self, token):
        """Apply all token normalizers to a token.

        Args:
            token: a string token

        Returns:
            A list of (prefix, normalized_token) tuples, where prefix
            is the namespace prefix defined by the normalizer. If a
            normalizer returns None for the token, it will not be
            included.
        """
        ret = []
        for normalizer in self.token_normalizers:
            new_token = normalizer.normalize(token)

            if new_token is not None:
                ret.append((normalizer.prefix, new_token))

        return ret


class WhitespaceAnalyzer(Analyzer):
    """An analyzer that splits tokens on whitespace.

    This can be used for simple circumstances where you don't care
    about words with leading or trailing punctuation being considered
    different from the same word without punctuation.
    """
    def tokens(self, input):
        return input.split()

    def join(self, tokens):
        return " ".join(tokens)

    def query(self, tokens):
        return search.Query(tokens)
