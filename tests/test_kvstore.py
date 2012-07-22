# Copyright (C) 2012 Peter Teichman

import operator
import os
import shutil
import unittest2 as unittest

import cobe.kvstore

class KVStoreBase(object):
    """Base tests for KV Stores"""

    def test_put_get(self):
        key, value = "test_key", "test_value"

        self.assertIsNone(self.store.get(key, None))
        self.store.put(key, value)
        self.assertEqual(value, self.store.get(key))

    def test_put_many(self):
        items = [
            ("one", "value1"),
            ("two", "value2"),
            ("three", "value3"),
            ("four", "value4"),
            ("five", "value5"),
            ("six", "value6"),
            ("seven", "value7"),
            ("eight", "value8"),
            ("nine", "value9")
            ]

        self.store.put_many(items)

        for key, value in items:
            self.assertEqual(value, self.store.get(key))

    def test_keys(self):
        items = [
            ("one", "value1"),
            ("two", "value2"),
            ("three", "value3"),
            ("four", "value4"),
            ("five", "value5"),
            ("six", "value6"),
            ("seven", "value7"),
            ("eight", "value8"),
            ("nine", "value9")
            ]

        for key, value in items:
            self.store.put(key, value)

        # Sorted order is: eight five four nine one seven six three two
        keys = list(self.store.keys())
        expected = "eight five four nine one seven six three two".split()
        self.assertEqual(expected, keys)

        # Test key_from on keys that are present and missing in the db
        keys = list(self.store.keys(key_from="four"))
        expected = "four nine one seven six three two".split()
        self.assertEqual(expected, keys)

        keys = list(self.store.keys(key_from="fo"))
        expected = "four nine one seven six three two".split()
        self.assertEqual(expected, keys)

        # Test key_to
        keys = list(self.store.keys(key_to="six"))
        expected = "eight five four nine one seven six".split()
        self.assertEqual(expected, keys)

        keys = list(self.store.keys(key_to="si"))
        expected = "eight five four nine one seven".split()
        self.assertEqual(expected, keys)

        # And test them both together
        keys = list(self.store.keys(key_from="five", key_to="three"))
        expected = "five four nine one seven six three".split()
        self.assertEqual(expected, keys)

    def test_items(self):
        put_items = dict([
            ("one", "value1"),
            ("two", "value2"),
            ("three", "value3"),
            ("four", "value4"),
            ("five", "value5"),
            ("six", "value6"),
            ("seven", "value7"),
            ("eight", "value8"),
            ("nine", "value9")
            ])

        for key, value in put_items.items():
            self.store.put(key, value)

        # Sorted order is: eight five four nine one seven six three two
        keys = list(self.store.items())
        expected = sorted(put_items.items(), key=operator.itemgetter(0))
        self.assertEqual(expected, keys)

        # Test key_from on keys that are present and missing in the db
        keys = list(self.store.items(key_from="four"))
        self.assertEqual(expected[2:], keys)

        keys = list(self.store.items(key_from="fo"))
        self.assertEqual(expected[2:], keys)

        # Test key_to
        keys = list(self.store.items(key_to="six"))
        self.assertEqual(expected[:7], keys)

        keys = list(self.store.items(key_to="si"))
        self.assertEqual(expected[:6], keys)

        # And test them both together
        keys = list(self.store.items(key_from="five", key_to="three"))
        self.assertEqual(expected[1:8], keys)

class TestLevelDBStore(unittest.TestCase, KVStoreBase):
    DBDIR = "tests.test_store"

    @classmethod
    def setUpClass(cls):
        try:
            import leveldb
        except ImportError:
            raise unittest.SkipTest("py-leveldb not installed")

    def setUp(self):
        self.store = cobe.kvstore.LevelDBStore(self.DBDIR)

        def cleanup():
            if os.path.exists(self.DBDIR):
                shutil.rmtree(self.DBDIR)

        self.addCleanup(cleanup)


if __name__ == '__main__':
    unittest.main()
