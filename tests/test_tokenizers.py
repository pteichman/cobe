import unittest

from cobe.tokenizers import CobeStemmer, CobeTokenizer, MegaHALTokenizer

class testMegaHALTokenizer(unittest.TestCase):
    def setUp(self):
        self.tokenizer = MegaHALTokenizer()

    def testSplitEmpty(self):
        self.assertEqual(len(self.tokenizer.split("")), 0)

    def testSplitSentence(self):
        words = self.tokenizer.split("hi.")
        self.assertEqual(words, ["HI", "."])

    def testSplitComma(self):
        words = self.tokenizer.split("hi, cobe")
        self.assertEqual(words, ["HI", ", ", "COBE", "."])

    def testSplitImplicitStop(self):
        words = self.tokenizer.split("hi")
        self.assertEqual(words, ["HI", "."])

    def testSplitUrl(self):
        words = self.tokenizer.split("http://www.google.com/")
        self.assertEqual(words, ["HTTP", "://", "WWW", ".", "GOOGLE", ".", "COM", "/."])

    def testSplitNonUnicode(self):
        self.assertRaises(TypeError, self.tokenizer.split, "foo")

    def testSplitApostrophe(self):
        words = self.tokenizer.split("hal's brain")
        self.assertEqual(words, ["HAL'S", " ", "BRAIN", "."])

        words = self.tokenizer.split("',','")
        self.assertEqual(words, ["'", ",", "'", ",", "'", "."])

    def testSplitAlphaAndNumeric(self):
        words = self.tokenizer.split("hal9000, test blah 12312")
        self.assertEqual(words, ["HAL", "9000", ", ", "TEST", " ", "BLAH", " ", "12312", "."])

        words = self.tokenizer.split("hal9000's test")
        self.assertEqual(words, ["HAL", "9000", "'S", " ", "TEST", "."])

    def testCapitalize(self):
        words = self.tokenizer.split("this is a test")
        self.assertEqual("This is a test.", self.tokenizer.join(words))

        words = self.tokenizer.split("A.B. Hal test test. will test")
        self.assertEqual("A.b. Hal test test. Will test.",
                          self.tokenizer.join(words))

        words = self.tokenizer.split("2nd place test")
        self.assertEqual("2Nd place test.", self.tokenizer.join(words))

class testCobeTokenizer(unittest.TestCase):
    def setUp(self):
        self.tokenizer = CobeTokenizer()

    def testSplitEmpty(self):
        self.assertEqual(len(self.tokenizer.split("")), 0)

    def testSplitSentence(self):
        words = self.tokenizer.split("hi.")
        self.assertEqual(words, ["hi", "."])

    def testSplitComma(self):
        words = self.tokenizer.split("hi, cobe")
        self.assertEqual(words, ["hi", ",", " ", "cobe"])

    def testSplitDash(self):
        words = self.tokenizer.split("hi - cobe")
        self.assertEqual(words, ["hi", " ", "-", " ", "cobe"])

    def testSplitMultipleSpacesWithDash(self):
        words = self.tokenizer.split("hi  -  cobe")
        self.assertEqual(words, ["hi", " ", "-", " ", "cobe"])

    def testSplitLeadingDash(self):
        words = self.tokenizer.split("-foo")
        self.assertEqual(words, ["-foo"])

    def testSplitLeadingSpace(self):
        words = self.tokenizer.split(" foo")
        self.assertEqual(words, ["foo"])

        words = self.tokenizer.split("  foo")
        self.assertEqual(words, ["foo"])

    def testSplitTrailingSpace(self):
        words = self.tokenizer.split("foo ")
        self.assertEqual(words, ["foo"])

        words = self.tokenizer.split("foo  ")
        self.assertEqual(words, ["foo"])

    def testSplitSmiles(self):
        words = self.tokenizer.split(":)")
        self.assertEqual(words, [":)"])

        words = self.tokenizer.split(";)")
        self.assertEqual(words, [";)"])

        # not smiles
        words = self.tokenizer.split(":(")
        self.assertEqual(words, [":("])

        words = self.tokenizer.split(";(")
        self.assertEqual(words, [";("])

    def testSplitUrl(self):
        words = self.tokenizer.split("http://www.google.com/")
        self.assertEqual(words, ["http://www.google.com/"])

        words = self.tokenizer.split("https://www.google.com/")
        self.assertEqual(words, ["https://www.google.com/"])

        # odd protocols
        words = self.tokenizer.split("cobe://www.google.com/")
        self.assertEqual(words, ["cobe://www.google.com/"])

        words = self.tokenizer.split("cobe:www.google.com/")
        self.assertEqual(words, ["cobe:www.google.com/"])

        words = self.tokenizer.split(":foo")
        self.assertEqual(words, [":", "foo"])

    def testSplitMultipleSpaces(self):
        words = self.tokenizer.split("this is  a test")
        self.assertEqual(words, ["this", " ", "is", " ", "a", " ", "test"])

    def testSplitVerySadFrown(self):
        words = self.tokenizer.split("testing :    (")
        self.assertEqual(words, ["testing", " ", ":    ("])

        words = self.tokenizer.split("testing          :    (")
        self.assertEqual(words, ["testing", " ", ":    ("])

        words = self.tokenizer.split("testing          :    (  foo")
        self.assertEqual(words, ["testing", " ", ":    (", " ", "foo"])

    def testSplitHyphenatedWord(self):
        words = self.tokenizer.split("test-ing")
        self.assertEqual(words, ["test-ing"])

        words = self.tokenizer.split(":-)")
        self.assertEqual(words, [":-)"])

        words = self.tokenizer.split("test-ing :-) 1-2-3")
        self.assertEqual(words, ["test-ing", " ", ":-)", " ", "1-2-3"])

    def testSplitApostrophes(self):
        words = self.tokenizer.split("don't :'(")
        self.assertEqual(words, ["don't", " ", ":'("])

    def testSplitNonUnicode(self):
        self.assertRaises(TypeError, self.tokenizer.split, "foo")

    def testJoin(self):
        self.assertEqual("foo bar baz",
                          self.tokenizer.join(["foo", " ", "bar", " ", "baz"]))


class testCobeStemmer(unittest.TestCase):
    def setUp(self):
        self.stemmer = CobeStemmer("english")

    def testStemmer(self):
        self.assertEqual("foo", self.stemmer.stem("foo"))
        self.assertEqual("jump", self.stemmer.stem("jumping"))
        self.assertEqual("run", self.stemmer.stem("running"))

    def testStemmerCase(self):
        self.assertEqual("foo", self.stemmer.stem("Foo"))
        self.assertEqual("foo", self.stemmer.stem("FOO"))

        self.assertEqual("foo", self.stemmer.stem("FOO'S"))
        self.assertEqual("foo", self.stemmer.stem("FOOING"))
        self.assertEqual("foo", self.stemmer.stem("Fooing"))

if __name__ == '__main__':
    unittest.main()
