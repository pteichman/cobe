# Copyright (C) 2012 Peter Teichman

import os
import random
import shutil
import unittest

from cobe.model import Model, TokenRegistry


TEST_MODEL = "test_model.cobe"


class TestTokenRegistry(unittest.TestCase):
    def test_get_new_tokens(self):
        tokens = TokenRegistry()

        # First, register four new tokens and make sure they get the
        # expected ids.
        for token_id, token in enumerate("this is a test".split()):
            self.assertEquals(chr(token_id), tokens.get_id(token))

        # Then, repeat the same check to make sure they aren't
        # re-registered.
        for token_id, token in enumerate("this is a test".split()):
            self.assertEquals(chr(token_id), tokens.get_id(token))


class TestModel(unittest.TestCase):
    def setUp(self):
        if os.path.exists(TEST_MODEL):
            shutil.rmtree(TEST_MODEL)

    def test_init(self):
        self.assertFalse(os.path.exists(TEST_MODEL))

        # Don't specify any ngram orders, which should get trigrams,
        # bigrams, and unigrams stored.
        model = Model(TEST_MODEL)

        self.assertTrue(os.path.exists(TEST_MODEL))
        self.assertEquals((3, 2, 1), model.orders)

    def test_load_tokens(self):
        # Ensure that model.tokens is properly reloaded from the
        # database when an old Model is loaded
        model = Model(TEST_MODEL)

        strs = ("foo", "bar", "baz", "quux", "quuux")
        ids1 = map(model.tokens.get_id, strs)

        model.save()

        model = Model(TEST_MODEL)

        # TokenRegistry should come back with the above ids (+ the id
        # from the empty string)
        self.assertEquals(len(ids1), len(model.tokens.token_ids))

        ids2 = map(model.tokens.get_id, strs)
        self.assertEquals(ids1, ids2)

        # And verify the reverse mapping
        for token_id, token in zip(ids2, strs):
            self.assertEquals(token, model.tokens.get_token(token_id))

    def test_ngrams(self):
        model = Model(TEST_MODEL)
        tokens = "this is a test string for n-grams".split()

        # Test n=3
        ngrams = list(model._ngrams(tokens, 3))
        expected = [["this", "is", "a"],
                    ["is", "a", "test"],
                    ["a", "test", "string"],
                    ["test", "string", "for"],
                    ["string", "for", "n-grams"]]

        # Test n=2
        ngrams = list(model._ngrams(tokens, 2))
        expected = [["this", "is"],
                    ["is", "a"],
                    ["a", "test"],
                    ["test", "string"],
                    ["string", "for"],
                    ["for", "n-grams"]]

        # Test unigrams
        ngrams = list(model._ngrams(tokens, 1))
        expected = [["this"], ["is"], ["a"], ["test"], ["string"],
                    ["for"], ["n-grams"]]

        self.assertEquals(expected, ngrams)

    def test_ngrams_short(self):
        model = Model(TEST_MODEL)
        tokens = "this is".split()

        # Test n=3 with a string that doesn't have any 3-grams
        ngrams = list(model._ngrams(tokens, 3))
        expected = []

        self.assertEquals(expected, ngrams)

    def test_train(self):
        model = Model(TEST_MODEL)

        tokens = "this is a test string".split()
        model.train(tokens)

        counts = [(1, ("<S>", "this", "is")),
                  (1, ("test", "string", "</S>")),
                  (1, ("this", "is", "a")),
                  (1, ("is", "a", "test")),
                  (1, ("a", "test", "string")),
                  (0, ("will", "not", "find"))]

        # Make sure the model was saved
        self.assertEquals(0, len(model.counts_log))

        for count, ngram in counts:
            self.assertEquals(count, model.ngram_count(ngram))

        # Now train the phrase again and make sure the new counts were
        # merged.
        model.train(tokens)

        for count, ngram in counts:
            if count != 0:
                count += 1

            self.assertEquals(count, model.ngram_count(ngram))

    def test_train_many(self):
        model = Model(TEST_MODEL)

        sentences = ["this is a test",
                     "this is another test",
                     "this is a third test"]

        def tokens_gen(items):
            for sentence in items:
                yield sentence.split()

        model.train_many(tokens_gen(sentences))

        # Make sure the model was saved
        self.assertEquals(0, len(model.counts_log))

        self.assertEquals(2, model.ngram_count("this is a".split()))
        self.assertEquals(1, model.ngram_count("is a test".split()))
        self.assertEquals(1, model.ngram_count("this is another".split()))
        self.assertEquals(1, model.ngram_count("is a third".split()))

    def test_add_count(self):
        # Since _add_count adds to a LevelDB WriteBatch directly, and
        # the bindings for WriteBatch don't make it easy to figure out
        # what has been queued, test _add_count via its side effects
        # in the database.
        model = Model(TEST_MODEL)

        ngram = "one two three".split()
        self.assertEquals(0, model.ngram_count(ngram))

        model.train(ngram)
        self.assertEquals(1, model.ngram_count(ngram))

        # Ensure new counts are added to existing database counts
        model.train(ngram)
        self.assertEquals(2, model.ngram_count(ngram))

    def test_logprob_with_counts(self):
        # Make a couple of logprob checks with a model that tracks the
        # default trigrams, bigrams, and unigrams
        model = Model(TEST_MODEL)

        # Test before and after a save
        model.train("one two three".split())
        model.train("one two four".split())

        ngram = "one two three".split()
        token, context = ngram[-1], ngram[:-1]
        self.assertAlmostEqual(0.69314718, model.logprob(token, context))

    def test_logprob_without_counts(self):
        # Make logprob checks with a model that only tracks trigrams,
        # so it has to calculate the bigram counts necessary for
        # 3-gram logprobs.
        model = Model(TEST_MODEL, (3,))

        model.train("one two three".split())
        model.train("one two four".split())

        ngram = "one two three".split()
        token, context = ngram[-1], ngram[:-1]
        self.assertAlmostEqual(0.69314718, model.logprob(token, context))

    def test_prob_with_counts(self):
        # Make a couple of probability checks with a model that tracks
        # the default trigrams, bigrams, and unigrams
        model = Model(TEST_MODEL)

        # Test before and after a save
        model.train("one two three".split())
        model.train("one two four".split())

        ngram = "one two three".split()
        token, context = ngram[-1], ngram[:-1]
        self.assertAlmostEqual(0.5, model.prob(token, context))

    def test_prob_without_counts(self):
        # Make a couple of probability checks with a model that tracks
        # the default trigrams, bigrams, and unigrams
        model = Model(TEST_MODEL, (3,))

        # Test before and after a save
        model.train("one two three".split())
        model.train("one two four".split())

        ngram = "one two three".split()
        token, context = ngram[-1], ngram[:-1]
        self.assertAlmostEqual(0.5, model.prob(token, context))

    def test_autosave(self):
        model = Model(TEST_MODEL, (3,))
        self.assertEqual(0, len(model.counts_log))

        # force the autosave threshold down and make sure it fires
        # once enough counts have been logged
        model.SAVE_THRESHOLD = 5

        for num in xrange(model.SAVE_THRESHOLD):
            trigram = [str(num)] * 3

            model._train_sentence(trigram)
            model._autosave()

            self.assert_(len(model.counts_log) <= model.SAVE_THRESHOLD)

    def test_choose_random_word(self):
        model = Model(TEST_MODEL, (3,))

        # First, train one sentence and make sure we randomly pick the
        # only possible option.
        model.train("one two three".split())
        context = ["one", "two"]

        self.assertEqual("three", model.choose_random_word(context))

        # Train another sentence and make sure we pick both options
        # with carefully chosen seeding. Explicitly use Python's (old)
        # WichmannHill PRNG to ensure reproducability, since the
        # default PRNG generator could conceivably change in a future
        # release.
        model.train("one two four".split())

        rng = random.WichmannHill()

        rng.seed(0)
        self.assertEqual("three", model.choose_random_word(context, rng=rng))
        self.assertEqual("four", model.choose_random_word(context, rng=rng))


if __name__ == '__main__':
    unittest.main()
