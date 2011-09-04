from cobe.brain import Brain
from cobe.tokenizers import MegaHALTokenizer
import cPickle as pickle
import os
import unittest

TEST_BRAIN_FILE = "test_cobe.brain"

class testInit(unittest.TestCase):
    def setUp(self):
        if os.path.exists(TEST_BRAIN_FILE):
            os.remove(TEST_BRAIN_FILE)

    def testInit(self):
        Brain.init(TEST_BRAIN_FILE)
        self.failUnless(os.path.exists(TEST_BRAIN_FILE),
                        "missing brain file after init")

        brain = Brain(TEST_BRAIN_FILE)
        self.failUnless(brain.order, "missing brain order after init")
        self.failUnless(brain._end_token_id,
                        "missing brain _end_token_id after init")

    def testInitWithOrder(self):
        order = 2
        Brain.init(TEST_BRAIN_FILE, order=order)

        brain = Brain(TEST_BRAIN_FILE)
        self.assertEqual(order, brain.order)

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
        obj = self

        db.set_info_text(key, pickle.dumps(obj))

        # pickle cannot load from a unicode object
        get_info_text = lambda: pickle.loads(db.get_info_text(key))
        self.assertRaises(TypeError, get_info_text)

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
        self.assertEquals(list(brain._to_edges(tokens)),
                          [((1, 1), False),
                           ((1, "this"), False),
                           (("this", "is"), True),
                           (("is", "a"), True),
                           (("a", "test"), True),
                           (("test", 1), False),
                           ((1, 1), False)])

        tokens = ["this", "is", "a", "test"]
        self.assertEquals(list(brain._to_edges(tokens)),
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

        self.assertEquals(list(brain._to_graph(brain._to_edges(tokens))),
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
