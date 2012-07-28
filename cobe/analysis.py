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

    def prefix(self):
        """A key prefix for namespacing items in the data store.

        This is used to namespace the results of different normalizers
        in the data store.
        """
        return self.__class__.__name__

    @abc.abstractmethod
    def normalize(self, token):  # pragma: no cover
        """Normalize a single token."""
        pass


class LowercaseNormalizer(TokenNormalizer):
    """Normalize tokens by lowercasing their text."""
    def normalize(self, token):
        return token.lower()


class WhitespaceAnalyzer(object):
    def tokens(self, input):
        return input.split()

    def join(self, tokens):
        return " ".join(tokens)

    def query(self, tokens):
        return search.Query(tokens)
