# Copyright (C) 2012 Peter Teichman

import tempfile
import types
import unittest

import cobe.counter
import cobe.varint


class TestMergeCounter(unittest.TestCase):
    def setUp(self):
        # Use a few n-grams from cobe's README as test data
        self.items = {
            "an": 1,
            "an on-disk": 1,
            "an on-disk data": 1,
            "can": 3,
            "can read": 2,
            "can read about": 1,
            "can read about its": 1
        }

    def test_file_counts(self):
        counter = cobe.counter.MergeCounter()

        tmpfile = tempfile.TemporaryFile()

        def file_item(item, count):
            return cobe.varint.encode((count, len(item))) + item

        for item, count in sorted(self.items.iteritems()):
            tmpfile.write(file_item(item, count))

        expected = [
            ("an", 1),
            ("an on-disk", 1),
            ("an on-disk data", 1),
            ("can", 3),
            ("can read", 2),
            ("can read about", 1),
            ("can read about its", 1)
        ]

        counts = list(counter.file_counts(tmpfile))

        self.assertEqual(expected, counts)

    def test_overflow(self):
        # Overflow some counts into a temporary file. Make sure it
        # looks correct.
        counter = cobe.counter.MergeCounter()

        fds = []
        counter._overflow(self.items, fds)

        self.assertEqual(1, len(fds))
        fd = fds[0]

        def file_item(item, count):
            return cobe.varint.encode((count, len(item))) + item

        expected = [
            file_item("an", 1),
            file_item("an on-disk", 1),
            file_item("an on-disk data", 1),
            file_item("can", 3),
            file_item("can read", 2),
            file_item("can read about", 1),
            file_item("can read about its", 1)
        ]

        fd.seek(0)

        self.assertEqual("".join(expected), fd.read())

    def test_count(self):
        # A basic test of counts
        counter = cobe.counter.MergeCounter()

        def repeat(items):
            # Repeat each key of items as many times as its value
            for item, count in items.iteritems():
                for i in xrange(count):
                    yield item, 1

        counts = counter.count(repeat(self.items))
        self.assert_(isinstance(counts, types.GeneratorType))

        for item, count in counts:
            self.assertEqual(self.items[item], count)

    def test_count_overflow(self):
        # Test counts, with restricted max_len. This forces an
        # overflow file to be written for every count logged.
        counter = cobe.counter.MergeCounter(max_len=1)

        def repeat(items):
            # Repeat each key of items as many times as its value
            for item, count in items.iteritems():
                for i in xrange(count):
                    yield item, 1

        counts = counter.count(repeat(self.items))
        self.assert_(isinstance(counts, types.GeneratorType))

        for item, count in counts:
            self.assertEqual(self.items[item], count)

    def test_count_overflow_merge(self):
        # Test counts, with restricted max_len and max_fds. This
        # forces overflow files to be merged together on every logged
        # count.
        counter = cobe.counter.MergeCounter(max_fds=1, max_len=1)

        def repeat(items):
            # Repeat each key of items as many times as its value
            for item, count in items.iteritems():
                for i in xrange(count):
                    yield item, 1

        counts = counter.count(repeat(self.items))
        self.assert_(isinstance(counts, types.GeneratorType))

        for item, count in counts:
            self.assertEqual(self.items[item], count)


class TestNgramCounter(unittest.TestCase):
    def setUp(self):
        class TestTokenizer(object):
            def split(self, text):
                return text.split()

        self.tokenizer = TestTokenizer()

    def test_count(self):
        ext = cobe.counter.NgramCounter(self.tokenizer)

        items = [
            "foo bar",
            "foo bar baz",
            "foo bar baz",
            "foo bar baz",
            "foo bar baz",
            "foo bar baz2",
            "foo bar baz2"
        ]

        expected = [
            ("bar", 7),
            ("bar\tbaz", 4),
            ("bar\tbaz2", 2),
            ("baz", 4),
            ("baz2", 2),
            ("foo", 7),
            ("foo\tbar", 7),
            ("foo\tbar\tbaz", 4),
            ("foo\tbar\tbaz2", 2)
        ]

        self.assertEqual(expected, list(ext.count(items, orders=(3, 2, 1))))

        # There are no 4-grams in the above
        self.assertEqual([], list(ext.count(items, orders=(4,))))
