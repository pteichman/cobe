# Copyright (C) 2012 Peter Teichman

import datetime
import hashlib
import logging
import sqlite3

log = logging.getLogger("cobe.corpus")


class CorpusError(Exception):
    pass


class Corpus(object):
    # A secondary database where we log all replies (along with their
    # inputs) for voting purposes. This is separate from the main
    # graph database for two reasons:
    #
    # 1) It has no connections to the graph data. It contains text
    # data rather than the graph tokens. This is to make vote data
    # future-proof against new tokenizers and reply features.
    #
    # 2) Its life cycle is expected to be longer than the brain graph,
    # and its data is more valuable. A brain can be destroyed and
    # recreated by retraining it, but the vote data requires user
    # input.
    def __init__(self, filename):
        self._conn = sqlite3.connect(filename)
        self._conn.row_factory = sqlite3.Row

        row = self._conn.execute("""
SELECT name FROM sqlite_master WHERE name='voters'""").fetchone()

        if row is None:
            raise CorpusError("Tried to open a non-initted Corpus")

    def add_user(self, email):
        q = "INSERT INTO voters (email) VALUES (?)"
        self._conn.execute(q, (email,))
        self._conn.commit()

    def log_exchange(self, input_, output, when=None):
        if when is None:
            when = datetime.datetime.now()

        # Create a unique hash for this exchange. This is so we can
        # identify an exchange without an easily guessable id, and so
        # voting can be more future-proof across Corpus databases.
        combo = input_ + "\n" + output
        sha1hash = hashlib.sha1(combo.encode("utf-8")).hexdigest()

        c = self._conn.cursor()

        # Try an update first, and if that doesn't work, insert
        q = "UPDATE exchanges SET time=? WHERE hash=?"
        c.execute(q, (when, sha1hash))

        if c.rowcount == 0:
            q = "INSERT INTO exchanges (input, output, time, hash) " \
                " VALUES (?, ?, ?, ?)"
            c.execute(q, (input_, output, when, sha1hash))

        self._conn.commit()

    @staticmethod
    def init(filename):
        log.info("Initializing a cobe corpus: %s" % filename)
        db = sqlite3.connect(filename)

        c = db.cursor()

        c.execute("""
CREATE TABLE IF NOT EXISTS voters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL)""")

        c.execute("""
CREATE UNIQUE INDEX IF NOT EXISTS voters_email ON voters(email)""")

        c.execute("""
CREATE TABLE IF NOT EXISTS exchanges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    input TEXT NOT NULL,
    output TEXT NOT NULL,
    time TIMESTAMP NOT NULL,
    hash TEXT UNIQUE NOT NULL)""")

        c.execute("""
CREATE TABLE IF NOT EXISTS votes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    voter_id INTEGER NOT NULL REFERENCES voters(id),
    log_id INTEGER NOT NULL REFERENCES exchanges(id),
    vote INTEGER NOT NULL,
    star BOOLEAN NOT NULL,
    time TIMESTAMP NOT NULL)""")

        db.commit()
