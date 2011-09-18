# Copyright (C) 2011 Peter Teichman

from cobe.bayes import Bayes

import unittest

class TestBayes(unittest.TestCase):
    def test_bayes_train(self):
        b = Bayes()

        tokens = "this is a test".split()
        b.train(tokens, "test")

        counts = b.classes["test"].token_counts

        assert counts["this"] == 1
        assert counts["is"] == 1
        assert counts["a"] == 1
        assert counts["test"] == 1

    def tokens(self, text):
        return text.strip().decode("utf-8").lower().split()

    def test_twss_train(self):
        b = Bayes()

        with open("gutenberg-fairy-tales.txt") as fd:
            for line in fd.xreadlines():
                b.train(self.tokens(line), "non-twss")

        with open("twss-stories-parsed.txt") as fd:
            for line in fd.xreadlines():
                b.train(self.tokens(line), "twss")

        ret = b.classify(self.tokens("wet"))
        assert ret["twss"] > ret["non-twss"]
