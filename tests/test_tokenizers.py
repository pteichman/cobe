import unittest

from cobe.tokenizers import CobeStemmer, CobeTokenizer, MegaHALTokenizer

class testMegaHALTokenizer(unittest.TestCase):
    def setUp(self):
        self.tokenizer = MegaHALTokenizer()

    def testSplitEmpty(self):
        self.assertEquals(len(self.tokenizer.split(u"")), 0)

    def testSplitSentence(self):
        words = self.tokenizer.split(u"hi.")
        self.assertEquals(words, ["HI", "."])

    def testSplitComma(self):
        words = self.tokenizer.split(u"hi, cobe")
        self.assertEquals(words, ["HI", ", ", "COBE", "."])

    def testSplitImplicitStop(self):
        words = self.tokenizer.split(u"hi")
        self.assertEquals(words, ["HI", "."])

    def testSplitUrl(self):
        words = self.tokenizer.split(u"http://www.google.com/")
        self.assertEquals(words, ["HTTP", "://", "WWW", ".", "GOOGLE", ".", "COM", "/."])

    def testSplitNonUnicode(self):
        self.assertRaises(TypeError, self.tokenizer.split, "foo")

    def testSplitApostrophe(self):
        words = self.tokenizer.split(u"hal's brain")
        self.assertEquals(words, ["HAL'S", " ", "BRAIN", "."])

        words = self.tokenizer.split(u"',','")
        self.assertEquals(words, ["'", ",", "'", ",", "'", "."])

    def testSplitAlphaAndNumeric(self):
        words = self.tokenizer.split(u"hal9000, test blah 12312")
        self.assertEquals(words, ["HAL", "9000", ", ", "TEST", " ", "BLAH", " ", "12312", "."])

        words = self.tokenizer.split(u"hal9000's test")
        self.assertEquals(words, ["HAL", "9000", "'S", " ", "TEST", "."])

    def testCapitalize(self):
        words = self.tokenizer.split(u"this is a test")
        self.assertEquals(u"This is a test.", self.tokenizer.join(words))

        words = self.tokenizer.split(u"A.B. Hal test test. will test")
        self.assertEquals(u"A.b. Hal test test. Will test.",
                          self.tokenizer.join(words))

        words = self.tokenizer.split(u"2nd place test")
        self.assertEquals(u"2Nd place test.", self.tokenizer.join(words))

class testCobeTokenizer(unittest.TestCase):
    def setUp(self):
        self.tokenizer = CobeTokenizer()

    def testSplitEmpty(self):
        self.assertEquals(len(self.tokenizer.split(u"")), 0)

    def testSplitSentence(self):
        words = self.tokenizer.split(u"hi.")
        self.assertEquals(words, ["hi", "."])

    def testSplitComma(self):
        words = self.tokenizer.split(u"hi, cobe")
        self.assertEquals(words, ["hi", ",", " ", "cobe"])

    def testSplitDash(self):
        words = self.tokenizer.split(u"hi - cobe")
        self.assertEquals(words, ["hi", " ", "-", " ", "cobe"])

    def testSplitMultipleSpacesWithDash(self):
        words = self.tokenizer.split(u"hi  -  cobe")
        self.assertEquals(words, ["hi", " ", "-", " ", "cobe"])

    def testSplitLeadingDash(self):
        words = self.tokenizer.split(u"-foo")
        self.assertEquals(words, ["-foo"])

    def testSplitLeadingSpace(self):
        words = self.tokenizer.split(u" foo")
        self.assertEquals(words, ["foo"])

        words = self.tokenizer.split(u"  foo")
        self.assertEquals(words, ["foo"])

    def testSplitTrailingSpace(self):
        words = self.tokenizer.split(u"foo ")
        self.assertEquals(words, ["foo"])

        words = self.tokenizer.split(u"foo  ")
        self.assertEquals(words, ["foo"])

    def testSplitSmiles(self):
        words = self.tokenizer.split(u":)")
        self.assertEquals(words, [":)"])

        words = self.tokenizer.split(u";)")
        self.assertEquals(words, [";)"])

        # not smiles
        words = self.tokenizer.split(u":(")
        self.assertEquals(words, [":("])

        words = self.tokenizer.split(u";(")
        self.assertEquals(words, [";("])

    def testSplitUrl(self):
        words = self.tokenizer.split(u"http://www.google.com/")
        self.assertEquals(words, ["http://www.google.com/"])

        words = self.tokenizer.split(u"https://www.google.com/")
        self.assertEquals(words, ["https://www.google.com/"])

        # odd protocols
        words = self.tokenizer.split(u"cobe://www.google.com/")
        self.assertEquals(words, ["cobe://www.google.com/"])

        words = self.tokenizer.split(u"cobe:www.google.com/")
        self.assertEquals(words, ["cobe:www.google.com/"])

        words = self.tokenizer.split(u":foo")
        self.assertEquals(words, [":", "foo"])

    def testSplitMultipleSpaces(self):
        words = self.tokenizer.split(u"this is  a test")
        self.assertEquals(words, ["this", " ", "is", " ", "a", " ", "test"])

    def testSplitVerySadFrown(self):
        words = self.tokenizer.split(u"testing :    (")
        self.assertEquals(words, ["testing", " ", ":    ("])

        words = self.tokenizer.split(u"testing          :    (")
        self.assertEquals(words, ["testing", " ", ":    ("])

        words = self.tokenizer.split(u"testing          :    (  foo")
        self.assertEquals(words, ["testing", " ", ":    (", " ", "foo"])

    def testSplitHyphenatedWord(self):
        words = self.tokenizer.split(u"test-ing")
        self.assertEquals(words, ["test-ing"])

        words = self.tokenizer.split(u":-)")
        self.assertEquals(words, [":-)"])

        words = self.tokenizer.split(u"test-ing :-) 1-2-3")
        self.assertEquals(words, ["test-ing", " ", ":-)", " ", "1-2-3"])

    def testSplitApostrophes(self):
        words = self.tokenizer.split(u"don't :'(")
        self.assertEquals(words, ["don't", " ", ":'("])

    def testSplitNonUnicode(self):
        self.assertRaises(TypeError, self.tokenizer.split, "foo")

    def testJoin(self):
        self.assertEquals("foo bar baz",
                          self.tokenizer.join(["foo", " ", "bar", " ", "baz"]))


class testCobeStemmer(unittest.TestCase):
    def setUp(self):
        self.stemmer = CobeStemmer("english")

    def testStemmer(self):
        self.assertEquals("foo", self.stemmer.stem("foo"))
        self.assertEquals("jump", self.stemmer.stem("jumping"))
        self.assertEquals("run", self.stemmer.stem("running"))

    def testStemmerCase(self):
        self.assertEquals("foo", self.stemmer.stem("Foo"))
        self.assertEquals("foo", self.stemmer.stem("FOO"))

        self.assertEquals("foo", self.stemmer.stem("FOO'S"))
        self.assertEquals("foo", self.stemmer.stem("FOOING"))
        self.assertEquals("foo", self.stemmer.stem("Fooing"))

if __name__ == '__main__':
    unittest.main()
