from halng.brain import Brain
from halng.tokenizer import MegaHALTokenizer
import os
import unittest

TEST_BRAIN_FILE = "hal.test_halng.brain"

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

    def testInitWithOrder(self):
        order = 2
        Brain.init(TEST_BRAIN_FILE, order=order)

        brain = Brain(TEST_BRAIN_FILE)
        self.assertEqual(order, brain.order)

class testLearn(unittest.TestCase):
    def setUp(self):
        if os.path.exists(TEST_BRAIN_FILE):
            os.remove(TEST_BRAIN_FILE)

    def test2ndOrderContexts(self):
        Brain.init(TEST_BRAIN_FILE, order=2)
        brain = Brain(TEST_BRAIN_FILE)

        tokenizer = MegaHALTokenizer()

        words = tokenizer.split(".")
        contexts = brain.get_learn_contexts(words)
        self.assertEqual(0, len(contexts))

        words = tokenizer.split("Hi.")
        contexts = brain.get_learn_contexts(words)
        self.assertEqual(1, len(contexts))
        self.assertEqual(["HI", "."], contexts[0])

        words = tokenizer.split("Hi Hal.")
        contexts = brain.get_learn_contexts(words)
        self.assertEqual(3, len(contexts))
        self.assertEqual(["HI", " "], contexts[0])
        self.assertEqual([" ", "HAL"], contexts[1])
        self.assertEqual(["HAL", "."], contexts[2])

        words = tokenizer.split("Hi, Hal.")
        contexts = brain.get_learn_contexts(words)
        self.assertEqual(3, len(contexts))
        self.assertEqual(["HI", ", "], contexts[0])
        self.assertEqual([", ", "HAL"], contexts[1])
        self.assertEqual(["HAL", "."], contexts[2])

if __name__ == '__main__':
    unittest.main()
