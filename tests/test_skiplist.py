# Copyright (C) 2013 Peter Teichman

import unittest2 as unittest

from cobe import skiplist


class TestSkiplist(unittest.TestCase):
    def test_insert(self):
        items = [
            ("foo", "bar"),
            ("bar", "baz"),
            ("quux", "quuux")
        ]

        skip = skiplist.Skiplist(maxsize=10, use_finger=True)
        for key, value in items:
            skip.insert(key, value)

        self.assertEqual(sorted(items), list(skip.items()))

    def test_delete_one(self):
        skip = skiplist.Skiplist(maxsize=10)
        skip.insert("foo", "bar")

        skip.delete("foo")
        self.assertEqual([], list(skip.items()))

    def test_delete_two(self):
        skip = skiplist.Skiplist(maxsize=10)
        skip.insert("foo", "bar")
        skip.insert("quux", "quuux")

        skip.delete("foo")
        self.assertEqual([("quux", "quuux")], list(skip.items()))

        skip.insert("foo", "bar")
        skip.delete("quux")
        self.assertEqual([("foo", "bar")], list(skip.items()))

    def test_delete(self):
        items = [
            ("foo", "bar"),
            ("bar", "baz"),
            ("quux", "quuux")
        ]

        for to_delete in ("foo", "bar", "quux"):
            skip = skiplist.Skiplist(maxsize=10)
            for key, value in items:
                skip.insert(key, value)

            skip.delete(to_delete)
            self.assertEqual(sorted([i for i in items if i[0] != to_delete]),
                             list(skip.items()))

    def test_delete_from_empty(self):
        skip = skiplist.Skiplist(maxsize=10)
        skip.delete("foo")

        self.assertEqual([], list(skip.items()))

    def test_too_many_items(self):
        items = [
            ("item%d" % d, "value%d" % d) for d in xrange(1000)
        ]

        # Test 1000 items in a skiplist with 10 items expected
        skip = skiplist.Skiplist(maxsize=10)
        for key, value in items:
            skip.insert(key, value)

        self.assertEqual(sorted(items), list(skip.items()))

    def test_count_low_set_bits(self):
        skip = skiplist.Skiplist()

        self.assertEqual(0, skip._count_low_set_bits(0b0))
        self.assertEqual(3, skip._count_low_set_bits(0b111))
        self.assertEqual(1, skip._count_low_set_bits(0b101))
