# Copyright (C) 2012 Peter Teichman

import abc
import itertools
import logging
import os
import sqlite3

logger = logging.getLogger(__name__)


def batchiter(iterable, size):
    """yield a series of batches from iterable, each size elements long"""
    source = iter(iterable)
    while True:
        batch = itertools.islice(source, size)
        yield itertools.chain([batch.next()], batch)


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


class BsddbStore(KVStore):
    def __init__(self, path):
        import bsddb
        self.bsddb = bsddb
        self.db = bsddb.btopen(path)

    def get(self, key, default=None):
        if not key in self.db:
            return default

        return self.db[key]

    def put(self, key, value):
        self.db[key] = value

    def put_many(self, items):
        for key, value in items:
            self.put(key, value)

    def _iter(self, key_from=None, key_to=None):
        db = self.db

        def is_done(key):
            return key_to is not None and key > key_to

        # This is pretty messy, as bsddb throws different exceptions
        # for first() and set_location() on empty databases.
        try:
            if key_from is None:
                key, value = db.first()
            else:
                key, value = db.set_location(key_from)
        except (KeyError, self.bsddb.error):
            return

        while not is_done(key):
            yield key, value
            try:
                key, value = db.next()
            except self.bsddb.error:
                return

    def keys(self, key_from=None, key_to=None):
        for key, value in self._iter(key_from=key_from, key_to=key_to):
            yield key

    def items(self, key_from=None, key_to=None):
        for key, value in self._iter(key_from=key_from, key_to=key_to):
            yield key, value


class SqliteStore(KVStore):
    def __init__(self, path):
        need_schema = not os.path.exists(path)

        self.conn = sqlite3.connect(path)

        # Don't create unicode objects for retrieved values
        self.conn.text_factory = buffer

        # Disable the SQLite cache. Its pages tend to get swapped
        # out, even if the database file is in buffer cache.
        c = self.conn.cursor()
        c.execute("PRAGMA cache_size=0")
        c.execute("PRAGMA page_size=4096")

        # Use write-ahead logging if it's available, otherwise truncate
        journal_mode, = c.execute("PRAGMA journal_mode=WAL").fetchone()
        if journal_mode != "wal":
            c.execute("PRAGMA journal_mode=truncate")

        # Speed-for-reliability tradeoffs
        c.execute("PRAGMA temp_store=memory")
        c.execute("PRAGMA synchronous=OFF")

        if need_schema:
            self._create_db(self.conn)

    def _create_db(self, conn):
        logger.debug("Creating SqliteStore schema")
        c = conn.cursor()

        c.execute("""
CREATE TABLE kv (
    key BLOB NOT NULL PRIMARY KEY,
    value BLOB NOT NULL)""")

        conn.commit()

    def get(self, key, default=None):
        q = "SELECT value FROM kv WHERE key = ?"
        c = self.conn.cursor()

        row = c.execute(q, (sqlite3.Binary(key),)).fetchone()
        if not row:
            return default

        return str(row[0])

    def _put_one(self, c, key, value):
        q = "INSERT OR REPLACE INTO kv (key, value) VALUES (?, ?)"
        c.execute(q, (sqlite3.Binary(key), sqlite3.Binary(value)))

    def put(self, key, value):
        c = self.conn.cursor()
        self._put_one(c, key, value)
        self.conn.commit()

    def put_many(self, items):
        for item_batch in batchiter(items, 30000):
            c = self.conn.cursor()

            for key, value in item_batch:
                self._put_one(c, key, value)

            self.conn.commit()

    def _range_where(self, key_from=None, key_to=None):
        if key_from is not None and key_to is None:
            return "WHERE key >= :key_from"

        if key_from is None and key_to is not None:
            return "WHERE key <= :key_to"

        if key_from is not None and key_to is not None:
            return "WHERE key BETWEEN :key_from AND :key_to"

        return ""

    def items(self, key_from=None, key_to=None):
        q = "SELECT key, value FROM kv %s ORDER BY key " \
            % self._range_where(key_from, key_to)

        if key_from is not None:
            key_from = sqlite3.Binary(key_from)

        if key_to is not None:
            key_to = sqlite3.Binary(key_to)

        c = self.conn.cursor()
        for key, value in c.execute(q, dict(key_from=key_from, key_to=key_to)):
            yield str(key), str(value)

    def keys(self, key_from=None, key_to=None):
        q = "SELECT key FROM kv %s ORDER BY key " \
            % self._range_where(key_from, key_to)

        if key_from is not None:
            key_from = sqlite3.Binary(key_from)

        if key_to is not None:
            key_to = sqlite3.Binary(key_to)

        c = self.conn.cursor()
        for key, in c.execute(q, dict(key_from=key_from, key_to=key_to)):
            yield str(key)


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
        for item_batch in batchiter(items, 30000):
            batch = self.leveldb.WriteBatch()

            for key, value in item_batch:
                batch.Put(key, value)

            self.kv.Write(batch)

    def items(self, key_from=None, key_to=None):
        return self.kv.RangeIter(key_from=key_from, key_to=key_to)

    def keys(self, key_from=None, key_to=None):
        return self.kv.RangeIter(key_from=key_from, key_to=key_to,
                                 include_value=False)
