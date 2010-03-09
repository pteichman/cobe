# Copyright (C) 2010 Peter Teichman

import re

class MegaHALTokenizer:
    def split(self, phrase):
        if len(phrase) == 0:
            return []

        # add ending punctuation if it is missing
        if phrase[-1] not in ".!?":
            phrase = phrase + "."

        # megahal traditionally considers [a-z0-9] as word characters.
        # Let's see what happens if we add [_']
        words = re.findall("([\w']+|[^\w']+)", phrase.upper(), re.UNICODE)
        return words

    def join(self, words):
        return "".join(words).capitalize()

class CobeTokenizer:
    def split(self, phrase):
        if len(phrase) == 0:
            return []

        words = re.findall("(http:\S+|[\w']+|[^\w']+)", phrase, re.UNICODE)
        return words
