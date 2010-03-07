import unittest

from cobe.tokenizer import MegaHALTokenizer

class testMegaHALTokenizer(unittest.TestCase):
    def setUp(self):
        self.tokenizer = MegaHALTokenizer()

    def testSplitEmpty(self):
        self.assertEquals(len(self.tokenizer.split("")), 0)

    def testSplitSentence(self):
        words = self.tokenizer.split("hi.")
        self.assertEquals(len(words), 2)
        self.assertEquals(words[0], "HI")
        self.assertEquals(words[1], ".")

    def testSplitComma(self):
        words = self.tokenizer.split("hi, cobe")
        self.assertEquals(len(words), 4)
        self.assertEquals(words[0], "HI")
        self.assertEquals(words[1], ", ")
        self.assertEquals(words[2], "COBE")
        self.assertEquals(words[3], ".")

    def testSplitImplicitStop(self):
        words = self.tokenizer.split("hi")
        self.assertEquals(len(words), 2)
        self.assertEquals(words[0], "HI")
        self.assertEquals(words[1], ".")

    def testSplitUrl(self):
        words = self.tokenizer.split("http://www.google.com/")
        self.assertEquals(len(words), 8)
        self.assertEquals(words[0], "HTTP")
        self.assertEquals(words[1], "://")
        self.assertEquals(words[2], "WWW")
        self.assertEquals(words[3], ".")
        self.assertEquals(words[4], "GOOGLE")
        self.assertEquals(words[5], ".")
        self.assertEquals(words[6], "COM")
        self.assertEquals(words[7], "/.")

if __name__ == '__main__':
    unittest.main()
