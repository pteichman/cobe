# Copyright (C) 2012 Peter Teichman

import os
import unittest

from cobe.corpus import Corpus, CorpusError

TEST_CORPUS_FILE = "test_cobe.corpus"

class testInit(unittest.TestCase):
    def setUp(self):
        if os.path.exists(TEST_CORPUS_FILE):
            os.remove(TEST_CORPUS_FILE)

    def testFailureWithoutInit(self):
        try:
            corpus = Corpus(TEST_CORPUS_FILE)
        except CorpusError:
            return

        self.fail("got no exception for a non-initted corpus")

    def testInit(self):
        Corpus.init(TEST_CORPUS_FILE)
        self.failUnless(os.path.exists(TEST_CORPUS_FILE))

        corpus = Corpus(TEST_CORPUS_FILE)

    def testLogExchange(self):
        Corpus.init(TEST_CORPUS_FILE)
        corpus = Corpus(TEST_CORPUS_FILE)

        corpus.log_exchange("hello", "hello to you")

if __name__ == '__main__':
    unittest.main()
