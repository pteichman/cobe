# Copyright (C) 2013 Peter Teichman
# coding=utf-8

import os
import park
import random
import shutil
import tempfile
import unittest2 as unittest

from cobe.analysis import LowercaseNormalizer, WhitespaceAnalyzer
from cobe.model import Model, TokenRegistry


class TestTokenRegistry(unittest.TestCase):
    def setUp(self):
        tf = tempfile.NamedTemporaryFile(delete=False)
        tf.close()

        self.filename = tf.name

    def tearDown(self):
        os.remove(self.filename)

    def test_get_new_tokens(self):
        tokens = TokenRegistry(self.filename)

        # First, register four new tokens and make sure they get the
        # expected ids.
        for token_id, token in enumerate(u"this is a test".split()):
            self.assertEquals(token_id, tokens.get_id(token))

        # Then, repeat the same check to make sure they aren't
        # re-registered.
        for token_id, token in enumerate(u"this is a test".split()):
            self.assertEquals(token_id, tokens.get_id(token))

    def test_non_unicode(self):
        # Test the Unicode-checking entry points in TokenRegistry
        tokens = TokenRegistry(self.filename)

        with self.assertRaises(TypeError):
            tokens.get_id("non-unicode string")

    def test_unicode(self):
        tokens = TokenRegistry(self.filename)
        self.assertEquals(0, tokens.get_id(u"<∅>"))

        # Reopen the file and ensure the token is loaded from disk
        tokens = TokenRegistry(self.filename)
        self.assertIn(u"<∅>", tokens.token_ids)
        self.assertEquals(0, tokens.get_id(u"<∅>"))

        # And make sure it's not re-registered on subsequent gets
        self.assertEquals(0, tokens.get_id(u"<∅>"))

    def test_del(self):
        tokens = TokenRegistry(self.filename)

        # Ensure that a token with a DEL character (0x7f) is saved and
        # loaded correctly. This is not likely in practice, but
        # codecs.open() considers a DEL an end of line character.

        token = u"foo\x7fbar"
        self.assertEquals(0, tokens.get_id(token))

        # Reopen the file and ensure the token is loaded from disk
        tokens = TokenRegistry(self.filename)
        self.assertIn(token, tokens.token_ids)
        self.assertEquals(0, tokens.get_id(token))


class SharedModelTests(object):
    # subclasses must set self.order to an integer ngram order
    def setUp(self):
        self.model = Model(self.__class__.__name__, self.order)

        training = [
            u"this is a test",
            u"this is another test"
            ]

        for text in training:
            self.model.train(text)

    def tearDown(self):
        shutil.rmtree(self.model.path)
        del self.model

    def test_limits(self):
        with self.assertRaises(ValueError):
            self.model.get_ngram_count(tuple())

        with self.assertRaises(ValueError):
            ng = ("foo",) * (self.order + 1)
            self.model.get_ngram_count(ng)

    def assertNgramCounts(self, model, expected):
        for each in expected:
            ngram, count = tuple(each[:-1]), each[-1]
            self.assertEquals(count, model.get_ngram_count(ngram), str(ngram))

    def do_test_unigram_counts(self):
        # At this point the model has 7 known tokens:
        # <∅> </∅> a another is test this
        #
        # With these counts:
        expected = [
            (u"<∅>", 2),
            (u"</∅>", 2),
            (u"a", 1),
            (u"another", 1),
            (u"is", 2),
            (u"test", 2),
            (u"this", 2)
            ]

        self.assertNgramCounts(self.model, expected)

    def do_test_bigram_counts(self):
        expected = [
            (u"<∅>", u"this", 2),
            (u"this", u"is", 2),
            (u"is", u"a", 1),
            (u"a", u"test", 1),
            (u"test", u"</∅>", 2),
            (u"is", u"another", 1),
            (u"another", u"test", 1),
            ]

        self.assertNgramCounts(self.model, expected)

    def do_test_trigram_counts(self):
        expected = [
            (u"<∅>", u"this", u"is", 2),
            (u"this", u"is", u"a", 1),
            (u"is", u"a", u"test", 1),
            (u"a", u"test", u"</∅>", 1),
            (u"this", u"is", u"another", 1),
            (u"is", u"another", u"test", 1),
            (u"another", u"test", u"</∅>", 1),
            ]

        self.assertNgramCounts(self.model, expected)

    def do_test_entropy(self):
        e1 = self.model.entropy(u"this is a test")
        e2 = self.model.entropy(u"this is another test")

        self.assertAlmostEquals(e1, e2)

        self.assertAlmostEquals(0.0, self.model.entropy("never trained"))
        self.assertAlmostEquals(
            0.0, self.model.entropy("this is another test too"))


class TestUnigramModel(SharedModelTests, unittest.TestCase):
    order = 1

    def test_counts(self):
        self.do_test_unigram_counts()


class TestBigramModel(SharedModelTests, unittest.TestCase):
    order = 2

    def test_counts(self):
        self.do_test_unigram_counts()
        self.do_test_bigram_counts()

    def test_entropy(self):
        self.do_test_entropy()

    def test_prob(self):
        self.assertAlmostEquals(1.0, self.model.prob(u"is", [u"this"]))
        self.assertAlmostEquals(0.5, self.model.prob(u"a", [u"is"]))

    def test_logprob(self):
        self.assertAlmostEquals(0.0, self.model.logprob(u"is", [u"this"]))
        self.assertAlmostEquals(1.0, self.model.logprob(u"a", [u"is"]))


class TestTrigramModel(SharedModelTests, unittest.TestCase):
    order = 3

    def test_counts(self):
        self.do_test_unigram_counts()
        self.do_test_bigram_counts()
        self.do_test_trigram_counts()

    def test_entropy(self):
        self.do_test_entropy()

    def test_prob(self):
        # context, token, expected
        tests = [
            ([u"this"], u"is", 1.0),
            ([u"is"], u"a", 0.5),
            ([u"<∅>", u"this"], u"is", 1.0),
            ([u"this", u"is"], u"a", 0.5),
            ]

        for test in tests:
            context, token, expected = test
            self.assertAlmostEquals(expected, self.model.prob(token, context),
                                    msg=test)

    def test_logprob(self):
        # context, token, expected
        tests = [
            ([u"this"], u"is", 0.0),
            ([u"is"], u"a", 1.0),
            ([u"<∅>", u"this"], u"is", 0.0),
            ([u"this", u"is"], u"a", 1.0),
            ]

        for test in tests:
            context, token, expected = test
            self.assertAlmostEquals(expected,
                                    self.model.logprob(token, context),
                                    msg=test)


@unittest.skip("skip old model tests")
class TestModel(unittest.TestCase):
    def setUp(self):
        self.analyzer = WhitespaceAnalyzer()
        self.store = park.SQLiteStore(":memory:")
        self.model = Model(self.analyzer, self.store)

    def test_init(self):
        # Don't specify any ngram orders, which should get trigrams
        # and bigrams stored.
        model = self.model
        self.assertEquals((3, 2, 1), model.orders)

        # And make sure n=5 yields 5-grams and 4-grams
        model = Model(self.analyzer, self.store, n=5)
        self.assertEquals((5, 4, 3, 2, 1), model.orders)

    def test_load_tokens(self):
        # Ensure that model.tokens is properly reloaded from the
        # database when an old Model is loaded
        model = self.model

        model.train(u"this is a test")
        model.train(u"this is another test")

        # We save on train(), so make sure the new tokens log is empty.
        self.assertEqual(0, len(model.tokens.token_log))

        save_token_ids = dict(model.tokens.token_ids)
        save_tokens = dict(model.tokens.tokens)

        model = Model(self.analyzer, self.store)

        self.assertEqual(save_token_ids, model.tokens.token_ids)
        self.assertEqual(save_tokens, model.tokens.tokens)

    def test_non_unicode(self):
        # Test the Unicode-checking entry points in Model
        model = self.model

        with self.assertRaises(TypeError):
            model.train("non-unicode")

        with self.assertRaises(TypeError):
            model.train_many(["non-unicode"])

        with self.assertRaises(TypeError):
            model.choose_random_context("non-unicode")

        with self.assertRaises(TypeError):
            model.choose_random_word("non-unicode")

        with self.assertRaises(TypeError):
            model.entropy("a longer non-unicode string")

        with self.assertRaises(TypeError):
            # search_bfs is a generator, so call next() to run the check
            model.search_bfs(["context"], "non-unicode").next()

        with self.assertRaises(TypeError):
            model.search_bfs_reverse(["context"], "non-unicode").next()

    def test_train(self):
        model = self.model

        text = u"<S> this is a test string </S>"
        model.train(text)

        counts = [
            (1, (model.TRAIN_START, model.TRAIN_START, model.TRAIN_START)),
            (1, (model.TRAIN_START, model.TRAIN_START, u"<S>")),
            (1, (model.TRAIN_START, u"<S>", u"this")),
            (1, (u"<S>", u"this", u"is")),
            (1, (u"test", u"string", u"</S>")),
            (1, (u"string", u"</S>", model.TRAIN_END)),
            (1, (u"</S>", model.TRAIN_END, model.TRAIN_END)),
            (1, (u"this", u"is", u"a")),
            (1, (u"is", u"a", u"test")),
            (1, (u"a", u"test", u"string")),
            (0, (u"will", u"not", u"find"))
        ]

        for count, ngram in counts:
            self.assertEquals(count, model.ngram_count(ngram))

        # Make sure the right number of reverse tokens have been trained
        self.assertEqual(len(list(model.store.prefix_items("3"))),
                         len(list(model.store.prefix_items("r"))))

        # Now train the phrase again and make sure the new counts were
        # merged.
        model.train(text)

        for count, ngram in counts:
            # Make sure we have twice as many counts as before.
            self.assertEquals(2 * count, model.ngram_count(ngram))

        # Make sure the n-grams that only contain TRAIN_START and TRAIN_END
        # have a count that is:
        # 1) equal to the number of trained items and
        # 2) equal to each other
        self.assertEqual(2, model.ngram_count([model.TRAIN_START] * 3))
        self.assertEqual(2, model.ngram_count([model.TRAIN_START] * 2))
        self.assertEqual(2, model.ngram_count([model.TRAIN_START] * 1))

        self.assertEqual(2, model.ngram_count([model.TRAIN_END] * 3))
        self.assertEqual(2, model.ngram_count([model.TRAIN_END] * 2))
        self.assertEqual(2, model.ngram_count([model.TRAIN_END] * 1))

    def test_train_start_end_counts(self):
        model = self.model

        text = u"foo bar baz"
        model.train(text)

        # Ensure we've only trained one start & end count
        self.assertEqual(1, model.ngram_count([model.TRAIN_START]))
        self.assertEqual(1, model.ngram_count([model.TRAIN_END]))

        self.assertEqual(1, model.ngram_count([model.TRAIN_START,
                                               model.TRAIN_START]))

        self.assertEqual(1, model.ngram_count([model.TRAIN_END,
                                               model.TRAIN_END]))

        model.train(text)
        self.assertEqual(2, model.ngram_count([model.TRAIN_START]))
        self.assertEqual(2, model.ngram_count([model.TRAIN_END]))

    def test_train_short(self):
        model = self.model
        store = self.model.store

        # Make sure the short-text check in training ensures that no
        # n-grams are counted for text with fewer than three tokens
        model.train(u"")

        self.assertEqual([], list(store.prefix_keys("1")))
        self.assertEqual([], list(store.prefix_keys("2")))
        self.assertEqual([], list(store.prefix_keys("3")))

        model.train(u"one")

        self.assertEqual([], list(store.prefix_keys("1")))
        self.assertEqual([], list(store.prefix_keys("2")))
        self.assertEqual([], list(store.prefix_keys("3")))

        model.train(u"one two")

        self.assertEqual([], list(store.prefix_keys("1")))
        self.assertEqual([], list(store.prefix_keys("2")))
        self.assertEqual([], list(store.prefix_keys("3")))

        model.train(u"one two three")

        # TRAIN_START / one / two / three / TRAIN_END
        self.assertEqual(5, len(list(store.prefix_keys("1"))))

        # TRAIN_START TRAIN_START / TRAIN_START one / one two / two three /
        # three TRAIN_END / TRAIN_END TRAIN_END
        self.assertEqual(6, len(list(store.prefix_keys("2"))))

        # TRAIN_START TRAIN_START TRAIN_START / TRAIN_START TRAIN_START one /
        # TRAIN_START one two / one two three / two three TRAIN_END /
        # three TRAIN_END TRAIN_END / TRAIN_END TRAIN_END TRAIN_END
        self.assertEqual(7, len(list(store.prefix_keys("3"))))

    def test_train_many(self):
        model = self.model

        sentences = [u"this is a test",
                     u"this is another test",
                     u"this is a third test"]

        model.train_many(sentences)

        self.assertEquals(2, model.ngram_count(u"this is a".split()))
        self.assertEquals(1, model.ngram_count(u"is a test".split()))
        self.assertEquals(1, model.ngram_count(u"this is another".split()))
        self.assertEquals(1, model.ngram_count(u"is a third".split()))

    def test_add_count(self):
        # Since _add_count adds to a LevelDB WriteBatch directly, and
        # the bindings for WriteBatch don't make it easy to figure out
        # what has been queued, test _add_count via its side effects
        # in the database.
        model = self.model

        text = u"one two three"
        ngram = text.split()
        self.assertEquals(0, model.ngram_count(ngram))

        model.train(text)
        self.assertEquals(1, model.ngram_count(ngram))

        # Ensure new counts are added to existing database counts
        model.train(text)
        self.assertEquals(2, model.ngram_count(ngram))

    def test_logprob_with_counts(self):
        # Make a couple of logprob checks with a model that tracks the
        # default trigrams, bigrams, and unigrams
        model = self.model

        model.train(u"one two three")
        model.train(u"one two four")

        ngram = u"one two three".split()
        token, context = ngram[-1], ngram[:-1]
        self.assertAlmostEqual(1.0, model.logprob(token, context))

    def test_prob_with_counts(self):
        # Make a couple of probability checks with a model that tracks
        # the default trigrams, bigrams, and unigrams
        model = self.model

        model.train(u"one two three")
        model.train(u"one two four")

        ngram = u"one two three".split()
        token, context = ngram[-1], ngram[:-1]
        self.assertAlmostEqual(0.5, model.prob(token, context))

    def test_entropy(self):
        model = self.model

        model.train(u"one two three")
        self.assertAlmostEqual(0.0, model.entropy(u"one two three"))

        model.train(u"one two four")
        self.assertAlmostEqual(1.0, model.entropy(u"one two three"))

    def test_choose_random_word(self):
        model = self.model

        # First, train one sentence and make sure we randomly pick the
        # only possible option.
        model.train(u"one two three")
        context = [u"one", u"two"]

        self.assertEqual(u"three", model.choose_random_word(context))

        # Make sure a context that hasn't been trained comes back None
        self.assertIsNone(model.choose_random_word([u"missing", u"context"]))

        # Train another sentence and make sure we pick both options
        # with carefully chosen seeding. Explicitly use Python's (old)
        # WichmannHill PRNG to ensure reproducability, since the
        # default PRNG generator could conceivably change in a future
        # release.
        model.train(u"one two four")

        rng = random.WichmannHill()

        rng.seed(0)
        self.assertEqual(u"three", model.choose_random_word(context, rng=rng))
        self.assertEqual(u"four", model.choose_random_word(context, rng=rng))

    def test_choose_random_context(self):
        model = self.model

        # First, train one sentence and make sure we randomly pick the
        # only possible option.
        model.train(u"one two three")

        self.assertEqual([u"one", u"two", u"three"],
                         model.choose_random_context(u"one"))

        # Make sure a context that hasn't been trained comes back None
        self.assert_(model.choose_random_context(u"missing") is None)

        # Train another sentence and make sure we pick both options
        # with carefully chosen seeding.
        model.train(u"one two four")

        rng = random.WichmannHill()

        rng.seed(0)
        self.assertEqual([u"one", u"two", u"three"],
                         model.choose_random_context(u"one", rng=rng))
        self.assertEqual([u"one", u"two", u"four"],
                         model.choose_random_context(u"one", rng=rng))

    def test_search_bfs(self):
        model = self.model

        model.train(u"<S> this is a test sentence </S>")
        model.train(u"<S> this is a test sentence that continues </S>")
        model.train(u"<S> this is another test sentence </S>")

        results = list(model.search_bfs(u"<S> this is".split(), u"</S>"))

        # There should be four results, the three explicitly trained
        # sentence and one combination of 2 & 3.
        self.assertEquals(4, len(results))

        expected = [
            u"<S> this is a test sentence </S>".split(),
            u"<S> this is a test sentence that continues </S>".split(),
            u"<S> this is another test sentence </S>".split(),
            u"<S> this is another test sentence that continues </S>".split()]

        self.assertEqual(sorted(results), sorted(expected))

    def test_search_bfs_context_has_end(self):
        # Test for correct results when the search context contains
        # the end token.
        model = self.model

        model.train(u"foo bar baz quux")

        context = [u"baz", u"quux", u""]
        results = model.search_bfs(context, u"")
        self.assertEqual([u"baz", u"quux", u""], results.next())

        context = [u"quux", u"", u""]
        results = model.search_bfs(context, u"")
        self.assertEqual([u"quux", u"", u""], results.next())

    def test_search_bfs_reverse(self):
        model = self.model

        model.train(u"<S> this is a test sentence </S>")
        model.train(u"<S> this is a test sentence that continues </S>")
        model.train(u"<S> this is another test sentence </S>")

        results = list(
            model.search_bfs_reverse(u"test sentence </S>".split(), u"<S>"))

        # There should be two results
        self.assertEquals(2, len(results))

        expected = [
            u"<S> this is a test sentence </S>".split(),
            u"<S> this is another test sentence </S>".split()
        ]

        self.assertEqual(sorted(results), sorted(expected))

    def test_search_bfs_reverse_context_has_end(self):
        # Test for correct results when the search context contains
        # the end token.
        model = self.model

        model.train(u"foo bar baz quux")

        context = [u"", u"foo", u"bar"]
        results = model.search_bfs_reverse(context, u"")
        self.assertEqual([u"", u"foo", u"bar"], results.next())

        context = [u"", u"", u"foo"]
        results = model.search_bfs_reverse(context, u"")
        self.assertEqual([u"", u"", u"foo"], results.next())

    def test_normalizer(self):
        model = self.model
        analyzer = self.analyzer

        analyzer.add_token_normalizer(LowercaseNormalizer())

        model.train(u"This is a test")
