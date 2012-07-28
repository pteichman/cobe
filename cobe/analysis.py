# Copyright (C) 2012 Peter Teichman

import logging

from . import search

logger = logging.getLogger(__name__)


class WhitespaceAnalyzer(object):
    def tokens(self, input):
        return input.split()

    def join(self, tokens):
        return " ".join(tokens)

    def query(self, tokens):
        return search.Query(tokens)
