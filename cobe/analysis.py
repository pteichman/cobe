# Copyright (C) 2012 Peter Teichman

import abc
import logging
import re
import types

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

    def query(self, tokens, model=None):
        terms = []
        for index, token in enumerate(tokens):
            terms.append(dict(term=token, pos=index))

            # Conflate this term to any terms that normalize to the
            # same things.
            if model is None:
                continue

            for prefix, norm in self.normalize_token(token):
                for norm_token in model.get_norm_tokens(prefix, norm):
                    if norm_token != token:
                        terms.append(dict(term=norm_token, pos=index))

        return search.Query(terms)


class WhitespaceAnalyzer(Analyzer):
    """An analyzer that splits tokens on whitespace.

    This can be used for simple circumstances where you don't care
    about words with leading or trailing punctuation being considered
    different from the same word without punctuation.

    """
    def tokens(self, text):
        return text.split()

    def join(self, tokens):
        return unicode(" ".join(tokens), "utf-8")


class MegaHALAnalyzer(Analyzer):
    """A traditional MegaHAL style analyzer.

    This considers any of these to be a token:
    * one or more consecutive alpha characters (plus apostrophe)
    * one or more consecutive numeric characters
    * one or more consecutive punctuation/space characters (not apostrophe)

    This tokenizer ignores differences in capitalization.

    """
    def tokens(self, text):
        if not isinstance(text, types.UnicodeType):
            raise TypeError("Input must be Unicode")

        if len(text) == 0:
            return []

        # add ending punctuation if it is missing
        if text[-1] not in ".!?":
            text = text + "."

        words = re.findall("([A-Z']+|[0-9]+|[^A-Z'0-9]+)", text.upper(),
                           re.UNICODE)

        return words

    def join(self, words):
        """Re-join a MegaHAL style response.

        Capitalizes the first alpha character in the reply and any
        alpha character that follows [.?!] and a space.

        """
        chars = list(u"".join(words))
        start = True

        for i in xrange(len(chars)):
            char = chars[i]
            if char.isalpha():
                if start:
                    chars[i] = char.upper()
                else:
                    chars[i] = char.lower()

                start = False
            else:
                if i > 2 and chars[i - 1] in ".?!" and char.isspace():
                    start = True

        return u"".join(chars)

    def query(self, tokens, model=None):
        """Create a MegaHAL query.

        This skips any non-word tokens in the input when building the query.

        """
        terms = []
        for index, token in enumerate(tokens):
            if not re.match(r"[A-Z0-9']", token):
                # Skip any non-word tokens when building the query.
                continue

            terms.append(dict(term=token, pos=index))

        return search.Query(terms)
