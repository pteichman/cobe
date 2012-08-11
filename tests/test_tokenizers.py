import unittest

from cobe.tokenizers import (
    CobeStemmer, CobeTokenizer, MegaHALTokenizer, WhitespaceTokenizer)


class TestMegaHALTokenizer(unittest.TestCase):
    def setUp(self):
        self.tokenizer = MegaHALTokenizer()

    def test_split_empty(self):
        self.assertEquals(len(self.tokenizer.split(u"")), 0)

    def test_split_sentence(self):
        words = self.tokenizer.split(u"hi.")
        self.assertEquals(words, ["HI", "."])

    def test_split_comma(self):
        words = self.tokenizer.split(u"hi, cobe")
        self.assertEquals(words, ["HI", ", ", "COBE", "."])

    def test_split_implicit_stop(self):
        words = self.tokenizer.split(u"hi")
        self.assertEquals(words, ["HI", "."])

    def test_split_url(self):
        words = self.tokenizer.split(u"http://www.google.com/")
        self.assertEquals(words, ["HTTP", "://", "WWW", ".", "GOOGLE",
                                  ".", "COM", "/."])

    def test_split_non_unicode(self):
        self.assertRaises(TypeError, self.tokenizer.split, "foo")

    def test_split_apostrophe(self):
        words = self.tokenizer.split(u"hal's brain")
        self.assertEquals(words, ["HAL'S", " ", "BRAIN", "."])

        words = self.tokenizer.split(u"',','")
        self.assertEquals(words, ["'", ",", "'", ",", "'", "."])

    def test_split_alpha_and_numeric(self):
        words = self.tokenizer.split(u"hal9000, test blah 12312")
        self.assertEquals(words, ["HAL", "9000", ", ", "TEST", " ",
                                  "BLAH", " ", "12312", "."])

        words = self.tokenizer.split(u"hal9000's test")
        self.assertEquals(words, ["HAL", "9000", "'S", " ", "TEST", "."])

    def test_capitalize(self):
        words = self.tokenizer.split(u"this is a test")
        self.assertEquals(u"This is a test.", self.tokenizer.join(words))

        words = self.tokenizer.split(u"A.B. Hal test test. will test")
        self.assertEquals(u"A.b. Hal test test. Will test.",
                          self.tokenizer.join(words))

        words = self.tokenizer.split(u"2nd place test")
        self.assertEquals(u"2Nd place test.", self.tokenizer.join(words))


class TestCobeTokenizer(unittest.TestCase):
    def setUp(self):
        self.tokenizer = CobeTokenizer()

    def test_split_empty(self):
        self.assertEquals(len(self.tokenizer.split(u"")), 0)

    def test_split_sentence(self):
        words = self.tokenizer.split(u"hi.")
        self.assertEquals(words, ["hi", "."])

    def test_split_comma(self):
        words = self.tokenizer.split(u"hi, cobe")
        self.assertEquals(words, ["hi", ",", " ", "cobe"])

    def test_split_dash(self):
        words = self.tokenizer.split(u"hi - cobe")
        self.assertEquals(words, ["hi", " ", "-", " ", "cobe"])

    def test_split_multiple_spaces_with_dash(self):
        words = self.tokenizer.split(u"hi  -  cobe")
        self.assertEquals(words, ["hi", " ", "-", " ", "cobe"])

    def test_split_leading_dash(self):
        words = self.tokenizer.split(u"-foo")
        self.assertEquals(words, ["-foo"])

    def test_split_leading_space(self):
        words = self.tokenizer.split(u" foo")
        self.assertEquals(words, ["foo"])

        words = self.tokenizer.split(u"  foo")
        self.assertEquals(words, ["foo"])

    def test_split_trailing_space(self):
        words = self.tokenizer.split(u"foo ")
        self.assertEquals(words, ["foo"])

        words = self.tokenizer.split(u"foo  ")
        self.assertEquals(words, ["foo"])

    def test_split_smiles(self):
        words = self.tokenizer.split(u":)")
        self.assertEquals(words, [":)"])

        words = self.tokenizer.split(u";)")
        self.assertEquals(words, [";)"])

        # not smiles
        words = self.tokenizer.split(u":(")
        self.assertEquals(words, [":("])

        words = self.tokenizer.split(u";(")
        self.assertEquals(words, [";("])

    def test_split_url(self):
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

    def test_split_multiple_spaces(self):
        words = self.tokenizer.split(u"this is  a test")
        self.assertEquals(words, ["this", " ", "is", " ", "a", " ", "test"])

    def test_split_very_sad_frown(self):
        words = self.tokenizer.split(u"testing :    (")
        self.assertEquals(words, ["testing", " ", ":    ("])

        words = self.tokenizer.split(u"testing          :    (")
        self.assertEquals(words, ["testing", " ", ":    ("])

        words = self.tokenizer.split(u"testing          :    (  foo")
        self.assertEquals(words, ["testing", " ", ":    (", " ", "foo"])

    def test_split_hyphenated_word(self):
        words = self.tokenizer.split(u"test-ing")
        self.assertEquals(words, ["test-ing"])

        words = self.tokenizer.split(u":-)")
        self.assertEquals(words, [":-)"])

        words = self.tokenizer.split(u"test-ing :-) 1-2-3")
        self.assertEquals(words, ["test-ing", " ", ":-)", " ", "1-2-3"])

    def test_split_apostrophes(self):
        words = self.tokenizer.split(u"don't :'(")
        self.assertEquals(words, ["don't", " ", ":'("])

    def test_split_non_unicode(self):
        self.assertRaises(TypeError, self.tokenizer.split, "foo")

    def test_join(self):
        self.assertEquals("foo bar baz",
                          self.tokenizer.join(["foo", " ", "bar", " ", "baz"]))


class TestCobeStemmer(unittest.TestCase):
    def setUp(self):
        self.stemmer = CobeStemmer("english")

    def test_stemmer(self):
        self.assertEquals("foo", self.stemmer.stem("foo"))
        self.assertEquals("jump", self.stemmer.stem("jumping"))
        self.assertEquals("run", self.stemmer.stem("running"))

    def test_stemmer_case(self):
        self.assertEquals("foo", self.stemmer.stem("Foo"))
        self.assertEquals("foo", self.stemmer.stem("FOO"))

        self.assertEquals("foo", self.stemmer.stem("FOO'S"))
        self.assertEquals("foo", self.stemmer.stem("FOOING"))
        self.assertEquals("foo", self.stemmer.stem("Fooing"))

    def test_stem_nonword(self):
        self.assertEquals(":)", self.stemmer.stem(":)"))
        self.assertEquals(":)", self.stemmer.stem(": )"))
        self.assertEquals(":)", self.stemmer.stem(":  )"))
        self.assertEquals(":)", self.stemmer.stem(":-)"))

        self.assertEquals(":(", self.stemmer.stem(":("))
        self.assertEquals(":(", self.stemmer.stem(": ("))
        self.assertEquals(":(", self.stemmer.stem(":  ("))
        self.assertEquals(":(", self.stemmer.stem(":-("))


class TestWhitespaceTokenizer(unittest.TestCase):
    def test_split(self):
        tok = WhitespaceTokenizer()

        self.assertEquals([], tok.split(""))

        self.assertEquals(["this", "is", "a", "test"],
                          tok.split("this is a test"))

    def test_join(self):
        tok = WhitespaceTokenizer()

        self.assertEquals("", tok.join([]))

        self.assertEquals("this is a test",
                          tok.join(["this", "is", "a", "test"]))
