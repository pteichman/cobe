# Copyright (C) 2012 Peter Teichman
# coding=utf8

import unittest2 as unittest

from cobe.brain import Brain


class BrainTest(unittest.TestCase):
    def setUp(self):
        self.brain = Brain(":memory:")

    def test_train(self):
        # It's hard to test training from here; make sure the model
        # gets expected probabilities.
        model = self.brain.model

        self.brain.train(u"this is a test")
        self.assertAlmostEqual(1.0, model.prob(u"a", u"this is".split()))

        self.brain.train(u"this is another test")
        self.assertAlmostEqual(0.5, model.prob(u"a", u"this is".split()))

    def test_train_many(self):
        self.brain.train_many([u"this is a test"])

        model = self.brain.model
        self.assertAlmostEqual(1.0, model.prob(u"a", u"this is".split()))

    def test_reply(self):
        training = [u"this is a test", u"this is another test"]

        for train in training:
            self.brain.train(train)

        self.assert_(self.brain.reply(u"testing") in set(training))
