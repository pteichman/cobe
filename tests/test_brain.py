from cobe.brain import Brain, CobeError
from cobe.tokenizers import MegaHALTokenizer
import pickle as pickle
import os
import unittest

TEST_BRAIN_FILE = "test_cobe.brain"

class testInit(unittest.TestCase):
    def setUp(self):
        if os.path.exists(TEST_BRAIN_FILE):
            os.remove(TEST_BRAIN_FILE)

    def testInit(self):
        Brain.init(TEST_BRAIN_FILE)
        self.assertTrue(os.path.exists(TEST_BRAIN_FILE),
                        "missing brain file after init")

        brain = Brain(TEST_BRAIN_FILE)
        self.assertTrue(brain.order, "missing brain order after init")
        self.assertTrue(brain._end_token_id,
                        "missing brain _end_token_id after init")

    def testInitWithOrder(self):
        order = 2
        Brain.init(TEST_BRAIN_FILE, order=order)

        brain = Brain(TEST_BRAIN_FILE)
        self.assertEqual(order, brain.order)

    def testVersion(self):
        Brain.init(TEST_BRAIN_FILE)

        brain = Brain(TEST_BRAIN_FILE)
        self.assertEqual("2", brain.graph.get_info_text("version"))

    def testEmptyReply(self):
        Brain.init(TEST_BRAIN_FILE)

        brain = Brain(TEST_BRAIN_FILE)
        self.assertTrue(brain.reply("") is not "")

    def testWrongVersion(self):
        Brain.init(TEST_BRAIN_FILE)

        # manually change the brain version to 1
        brain = Brain(TEST_BRAIN_FILE)
        brain.graph.set_info_text("version", "1")
        brain.graph.commit()
        brain.graph.close()

        try:
            Brain(TEST_BRAIN_FILE)
        except CobeError as e:
            self.assertTrue("cannot read a version" in str(e))
        else:
            self.fail("opened a wrong version brain file")

    def testInitWithTokenizer(self):
        tokenizer = "MegaHAL"
        Brain.init(TEST_BRAIN_FILE, order=2, tokenizer=tokenizer)

        brain = Brain(TEST_BRAIN_FILE)
        self.assertTrue(isinstance(brain.tokenizer, MegaHALTokenizer))

    def testInfoText(self):
        order = 2
        Brain.init(TEST_BRAIN_FILE, order=order)

        brain = Brain(TEST_BRAIN_FILE)

        db = brain.graph
        key = "test_text"

        self.assertEqual(None, db.get_info_text(key))

        db.set_info_text(key, "test_value")
        self.assertEqual("test_value", db.get_info_text(key))

        db.set_info_text(key, "test_value2")
        self.assertEqual("test_value2", db.get_info_text(key))

        db.set_info_text(key, None)
        self.assertEqual(None, db.get_info_text(key))

    def testInfoPickle(self):
        order = 2
        Brain.init(TEST_BRAIN_FILE, order=order)

        brain = Brain(TEST_BRAIN_FILE)

        db = brain.graph
        key = "pickle_test"
        obj = {"dummy": "object", "to": "pickle"}

        db.set_info_text(key, pickle.dumps(obj))

        get_info_text = lambda: pickle.loads(
            db.get_info_text(key, text_factory=str))

class testLearn(unittest.TestCase):
    def setUp(self):
        if os.path.exists(TEST_BRAIN_FILE):
            os.remove(TEST_BRAIN_FILE)

    def testExpandContexts(self):
        Brain.init(TEST_BRAIN_FILE, order=2)
        brain = Brain(TEST_BRAIN_FILE)

        tokens = ["this", Brain.SPACE_TOKEN_ID, "is", Brain.SPACE_TOKEN_ID,
                  "a", Brain.SPACE_TOKEN_ID, "test"]
        self.assertEqual(list(brain._to_edges(tokens)),
                          [((1, 1), False),
                           ((1, "this"), False),
                           (("this", "is"), True),
                           (("is", "a"), True),
                           (("a", "test"), True),
                           (("test", 1), False),
                           ((1, 1), False)])

        tokens = ["this", "is", "a", "test"]
        self.assertEqual(list(brain._to_edges(tokens)),
                          [((1, 1), False),
                           ((1, "this"), False),
                           (("this", "is"), False),
                           (("is", "a"), False),
                           (("a", "test"), False),
                           (("test", 1), False),
                           ((1, 1), False)])

    def testExpandGraph(self):
        Brain.init(TEST_BRAIN_FILE, order=2)
        brain = Brain(TEST_BRAIN_FILE)

        tokens = ["this", Brain.SPACE_TOKEN_ID, "is", Brain.SPACE_TOKEN_ID,
                  "a", Brain.SPACE_TOKEN_ID, "test"]

        self.assertEqual(list(brain._to_graph(brain._to_edges(tokens))),
                          [((1, 1), False, (1, "this")),
                           ((1, "this"), True, ("this", "is")),
                           (("this", "is"), True, ("is", "a")),
                           (("is", "a"), True, ("a", "test")),
                           (("a", "test"), False, ("test", 1)),
                           (("test", 1), False, (1, 1))])

    def testLearn(self):
        Brain.init(TEST_BRAIN_FILE, order=2)
        brain = Brain(TEST_BRAIN_FILE)

        brain.learn("this is a test")
        brain.learn("this is also a test")

    def testLearnStems(self):
        Brain.init(TEST_BRAIN_FILE, order=2)

        brain = Brain(TEST_BRAIN_FILE)
        brain.set_stemmer("english")
        stem = brain.stemmer.stem

        brain.learn("this is testing")

        c = brain.graph.cursor()
        stem_count = c.execute("SELECT count(*) FROM token_stems").fetchone()

        self.assertEqual(3, stem_count[0])
        self.assertEqual(brain.graph.get_token_stem_id(stem("test")),
                          brain.graph.get_token_stem_id(stem("testing")))


class testReply(unittest.TestCase):
    def setUp(self):
        if os.path.exists(TEST_BRAIN_FILE):
            os.remove(TEST_BRAIN_FILE)

        Brain.init(TEST_BRAIN_FILE, order=2)
        self._brain = Brain(TEST_BRAIN_FILE)

    def testReply(self):
        brain = self._brain

        brain.learn("this is a test")
        brain.reply("this is a test")

if __name__ == '__main__':
    unittest.main()
