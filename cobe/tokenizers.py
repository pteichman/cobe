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

        words = re.findall("([A-Z']+|[0-9]+|[^A-Z'0-9]+)", phrase.upper(), re.UNICODE)
        return words

    def join(self, words):
        """Capitalize the first alpha character in the reply and the
        first alpha character that follows one of [.?!] and a
        space."""
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
                if i > 2 and chars[i-1] in ".?!" and char.isspace():
                    start = True

        return u"".join(chars)

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

        # Add hyphen to the list of possible word characters, so hyphenated
        # words become one token (e.g. hy-phen). But don't remove it from
        # the list of non-word characters, so if it's found entirely within
        # punctuation it's a normal non-word (e.g. :-( )
        words = re.findall("(\w+:\S+|[\w'-]+|[^\w]+)", phrase, re.UNICODE)

        # Turn any runs of multiple spaces at the beginning or end of
        # the token into a single space. This discourages extra spaces
        # between words, but preserves whitespace between punctuation
        # characters.
        for i in xrange(len(words)):
            words[i] = re.sub(r"(^  +|  +$)", " ", words[i])

        return words

    def join(self, words):
        return u"".join(words)
