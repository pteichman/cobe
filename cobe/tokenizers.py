# Copyright (C) 2010 Peter Teichman

import re
import types

class MegaHALTokenizer:
    """A traditional MegaHAL style tokenizer. This considers any of these
to be a token:
  * one or more consecutive alpha characters (plus apostrophe)
  * one or more consecutive numeric characters
  * one or more consecutive punctuation/space characters (not apostrophe)

This tokenizer ignores differences in capitalization."""
    def split(self, phrase):
        if type(phrase) != types.UnicodeType:
            raise TypeError("Input must be Unicode")

        if len(phrase) == 0:
            return []

        # add ending punctuation if it is missing
        if phrase[-1] not in ".!?":
            phrase = phrase + "."

        # megahal traditionally considers [a-z0-9] as word characters.
        # Let's see what happens if we add [_']
        words = re.findall("([A-Z']+|[0-9]+|[^A-Z'0-9]+)", phrase.upper(), re.UNICODE)
        return words

    def join(self, words):
        return u"".join(words).capitalize()

class CobeTokenizer:
    """A tokenizer that is somewhat improved from MegaHAL. These are
considered tokens:
  * one or more consecutive Unicode word characters (plus apostrophe)
  * one or more consecutive Unicode non-word characters
  * an HTTP url, http: followed by any run of non-space characters.

This tokenizer minimizes whitespace at the beginning or end of a token.

It preserves differences in case. foo, Foo, and FOO are different
tokens."""
    def split(self, phrase):
        if type(phrase) != types.UnicodeType:
            raise TypeError("Input must be Unicode")

        if len(phrase) == 0:
            return []

        words = re.findall("(http:\S+|[\w']+|[^\w']+)", phrase, re.UNICODE)

        # Turn any runs of multiple spaces at the beginning or end of
        # the token into a single space. This discourages extra spaces
        # between words, but preserves whitespace between punctuation
        # characters.
        for i in xrange(len(words)):
            words[i] = re.sub(r"(^  +|  +$)", " ", words[i])

        return words

    def join(self, words):
        return u"".join(words)
