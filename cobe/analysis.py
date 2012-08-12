# Copyright (C) 2012 Peter Teichman

import abc
import logging
import re
import Stemmer
import types
import unicodedata

from . import search
from . import tokenizers

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
    """Normalize tokens by ignoring upper/lower case.

    This allows a search for a token to return results containing any
    mixture of case of its characters.

    """
    def normalize(self, token):
        yield token.lower()


class AccentNormalizer(TokenNormalizer):
    """Normalize tokens by ignoring upper/lower case and accents.

    This normalizer uses the Python Unicode database to convert each
    token to the NFKD normal form, then discards combining
    characters. This normalizes Unicode characters with multiple forms
    and discards accents.

    """
    def normalize(self, token):
        nkfd = unicodedata.normalize("NFKD", token.lower())
        yield u"".join([c for c in nkfd if not unicodedata.combining(c)])


class StemNormalizer(TokenNormalizer):
    """Normalize tokens by reducing them to their lexical stems.

    This normalizer uses PyStemmer, an implementation of the Snowball
    stemming algorithms, to reduce tokens to their stems.

    """
    def __init__(self, language):
        """Initialize a StemNormalizer.

        Args:
            language: a PyStemmer language. These can be seen by
                listing Stemmer.algorithms(), but current options are:
                danish, dutch, english, finnish, french, german,
                hungarian, italian, norwegian, portuguese, romanian,
                russian, spanish, swedish, turkish.

                You can also specify "porter" to get the classic
                Porter stemmer for English.

        """
        super(StemNormalizer, self).__init__()

        self.stemmer = Stemmer.Stemmer(language.lower())

    def normalize(self, token):
        yield self.stemmer.stemWord(token.lower())


class Analyzer(object):
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer
        self.token_normalizers = []

    def tokens(self, input):
        """Split the input into a sequence of learnable tokens."""
        if not isinstance(input, types.UnicodeType):
            raise TypeError("token must be Unicode")

        return self.tokenizer.split(input)

    def join(self, tokens):
        """Join a tokens list into a response string."""
        return self.tokenizer.join(tokens)

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
        if not isinstance(token, types.UnicodeType):
            raise TypeError("token must be Unicode")

        ret = []
        for normalizer in self.token_normalizers:
            for new_token in normalizer.normalize(token):
                ret.append((normalizer.prefix, new_token))

        return ret

    def query(self, text, model=None):
        tokens = self.tokens(text)

        terms = []
        for index, token in enumerate(tokens):
            terms.append(dict(term=token, pos=index))

            # Conflate this term to any terms that normalize to the
            # same things.
            if model is None:
                continue

            seen_tokens = set([token])

            for prefix, norm in self.normalize_token(token):
                for norm_token in model.get_norm_tokens(prefix, norm):
                    if norm_token not in seen_tokens:
                        terms.append(dict(term=norm_token, pos=index))
                        seen_tokens.add(norm_token)

        return search.Query(terms)


class WhitespaceAnalyzer(Analyzer):
    """An analyzer that splits tokens on whitespace.

    This can be used for simple circumstances where you don't care
    about words with leading or trailing punctuation being considered
    different from the same word without punctuation.

    """
    def __init__(self):
        super(WhitespaceAnalyzer, self).__init__(
            tokenizers.WhitespaceTokenizer())


class MegaHALAnalyzer(Analyzer):
    """A traditional MegaHAL style analyzer.

    This considers any of these to be a token:
    * one or more consecutive alpha characters (plus apostrophe)
    * one or more consecutive numeric characters
    * one or more consecutive punctuation/space characters (not apostrophe)

    This tokenizer ignores differences in capitalization.

    """
    def __init__(self):
        super(MegaHALAnalyzer, self).__init__(tokenizers.MegaHALTokenizer())

    def query(self, text, model=None):
        """Create a MegaHAL query.

        This skips any non-word tokens in the input when building the query.

        """
        tokens = self.tokens(text)

        terms = []
        for index, token in enumerate(tokens):
            if not re.match(r"[A-Z0-9']", token):
                # Skip any non-word tokens when building the query.
                continue

            terms.append(dict(term=token, pos=index))

        return search.Query(terms)
