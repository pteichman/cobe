# Copyright (C) 2012 Peter Teichman

import abc
import logging

logger = logging.getLogger(__name__)


class KVStore(object):
    """An abstract key-value interface with support for range iteration."""
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def get(self, key, default=None):  # pragma: no cover
        """Get the value associated with a key.

        Returns:
            The specified default if the key is not present in the
            store. This method does not raise KeyError for missing
            keys.
        """
        pass

    @abc.abstractmethod
    def put(self, key, value):  # pragma: no cover
        """Set the value associated with a key.

        Both the key and value can be binary values.
        """
        pass

    @abc.abstractmethod
    def put_many(self, items):  # pragma: no cover
        """Set many key-value pairs.

        This method should take advantage of performance or atomicity
        features of the underlying store.

        Args:
            items: An iterator producing (key, value) tuples.
        """
        pass

    @abc.abstractmethod
    def keys(self, key_from=None, key_to=None):  # pragma: no cover
        """Get a lexically sorted range of keys.

        Args:
            key_from: Lower bound (inclusive), or None for unbounded.
            key_to: Upper bound (inclusive), or None for unbounded.

        Returns:
            An iterator yielding all keys from the store where
            key_from <= key <= key_to.
        """
        pass

    @abc.abstractmethod
    def items(self, key_from=None, key_to=None):  # pragma: no cover
        """Get a lexically sorted range of (key, value) tuples.

        Args:
            key_from: Lower bound (inclusive), or None for unbounded.
            key_to: Upper bound (inclusive), or None for unbounded.

        Returns:
            An iterator yielding all (key, value) pairs from the store
            where key_from <= key <= key_to.
        """
        pass


class LevelDBStore(KVStore):
    def __init__(self, path):
        import leveldb
        self.leveldb = leveldb
        self.kv = leveldb.LevelDB(path)

    def get(self, key, default=None):
        return self.kv.Get(key, default=default)

    def put(self, key, value):
        self.kv.Put(key, value)

    def put_many(self, items):
        batch = self.leveldb.WriteBatch()

        for key, value in items:
            batch.Put(key, value)

        self.kv.Write(batch)

    def items(self, key_from=None, key_to=None):
        return self.kv.RangeIter(key_from=key_from, key_to=key_to)

    def keys(self, key_from=None, key_to=None):
        return self.kv.RangeIter(key_from=key_from, key_to=key_to,
                                 include_value=False)
