import unittest

from cobe.tokenizer import CobeTokenizer, MegaHALTokenizer

class testMegaHALTokenizer(unittest.TestCase):
    def setUp(self):
        self.tokenizer = MegaHALTokenizer()

    def testSplitEmpty(self):
        self.assertEquals(len(self.tokenizer.split("")), 0)

    def testSplitSentence(self):
        words = self.tokenizer.split("hi.")
        self.assertEquals(words, ["HI", "."])

    def testSplitComma(self):
        words = self.tokenizer.split("hi, cobe")
        self.assertEquals(words, ["HI", ", ", "COBE", "."])

    def testSplitImplicitStop(self):
        words = self.tokenizer.split("hi")
        self.assertEquals(words, ["HI", "."])

    def testSplitUrl(self):
        words = self.tokenizer.split("http://www.google.com/")
        self.assertEquals(words, ["HTTP", "://", "WWW", ".", "GOOGLE", ".", "COM", "/."])

class testCobeTokenizer(unittest.TestCase):
    def setUp(self):
        self.tokenizer = CobeTokenizer()

    def testSplitEmpty(self):
        self.assertEquals(len(self.tokenizer.split("")), 0)

    def testSplitSentence(self):
        words = self.tokenizer.split("hi.")
        self.assertEquals(words, ["hi", "."])

    def testSplitComma(self):
        words = self.tokenizer.split("hi, cobe")
        self.assertEquals(words, ["hi", ", ", "cobe"])

    def testSplitUrl(self):
        words = self.tokenizer.split("http://www.google.com/")
        self.assertEquals(words, ["http://www.google.com/"])

    def testSplitMultipleSpaces(self):
        words = self.tokenizer.split("this is  a test")
        self.assertEquals(words, ["this", " ", "is", " ", "a", " ", "test"])

    def testSplitVerySadFrown(self):
        words = self.tokenizer.split("testing :    (")
        self.assertEquals(words, ["testing", " :    ("])

if __name__ == '__main__':
    unittest.main()
