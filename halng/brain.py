import logging
import re
import sqlite3

import megahal
import tokenizer

log = logging.getLogger("hal")

class Brain:
    def __init__(self, filename):
        self._conn = sqlite3.connect(filename)

        c = self._conn.cursor()
        row = c.execute("SELECT text FROM info WHERE attribute = 'order'").fetchone()
        self.order = int(row[0])
        self.tokenizer = tokenizer.MegaHALTokenizer()

    def learn(self, text):
        words = self._split(text)

        print words

        pass

    @staticmethod
    def init(filename, order=5):
        """Initialize a brain. This brain's file must not already exist."""

        log.info("Initializing a hal brain.")

        conn = sqlite3.connect(filename)
        c = conn.cursor()

        log.debug("Creating table: info")
        c.execute("""
CREATE TABLE info (
    attribute TEXT NOT NULL PRIMARY KEY,
    text TEXT NOT NULL)""")

        log.debug("Creating table: tokens")
        c.execute("""
CREATE TABLE tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL)""")

        tokens = []
        for i in xrange(order):
            if i < order-1:
                tokens.append("token%d_id INTEGER NOT NULL REFERENCES token(id)" % i)
            else:
                tokens.append("token%d_id INTEGER NOT NULL" % i)

        log.debug("Creating table: expr")
        c.execute("""
CREATE TABLE expr (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    %s)""" % ',\n    '.join(tokens))

        log.debug("Creating table: next_token")
        c.execute("""
CREATE TABLE next_token (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    expr_id INTEGER NOT NULL REFERENCES expr (id),
    token_id INTEGER NOT NULL REFERENCES token (id),
    count INTEGER NOT NULL)""")

        log.debug("Creating table: prev_token")
        c.execute("""
CREATE TABLE prev_token (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    expr_id INTEGER NOT NULL REFERENCES expr (id),
    token_id INTEGER NOT NULL REFERENCES token (id),
    count INTEGER NOT NULL)""")

        c.execute("INSERT INTO info (attribute, text) VALUES ('order', ?)",
                  str(order))

        conn.commit()
        c.close()
        conn.close()

    def clone(self, megahal_brain):
        log.info("Cloning a MegaHAL brain: %s", megahal_brain)

        conn = sqlite3.connect(self.filename)

        b = megahal.Brain(megahal_brain)
        b.clone(conn)

        conn.close()
