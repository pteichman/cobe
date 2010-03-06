# Copyright (C) 2010 Peter Teichman

import logging
import math
import random
import re
import sqlite3

import tokenizer

log = logging.getLogger("hal")

# use an empty string to denote the start/end of a chain
_END_TOKEN_TEXT = ""
_NEXT_TOKEN_TABLE = "next_token"
_PREV_TOKEN_TABLE = "prev_token"

class Brain:
    def __init__(self, filename):
        self._db = db = Db(sqlite3.connect(filename))

        self.order = int(db.get_info_text("order"))

        self._end_token_id = db.get_token_id(_END_TOKEN_TEXT)

        self.tokenizer = tokenizer.MegaHALTokenizer()

    def learn(self, text, commit=True):
        tokens = self.tokenizer.split(text.decode("utf-8"))

        if len(tokens) < self.order:
            log.debug("Input too short to learn: %s", text)
            return

        self._learn_tokens(tokens, commit)

    def _learn_tokens(self, tokens, commit=True):
        db = self._db
        c = db.cursor()

        token_ids = self._get_or_register_tokens(c, tokens)
        n_exprs = len(token_ids)-self.order

        for i in xrange(n_exprs+1):
            expr = token_ids[i:i+self.order]
            expr_id = self._get_or_register_expr(c, expr)

            # increment the expr count
            db.inc_expr_count(expr_id, c=c)

            if i == 0:
                # add link to boundary on prev_token
                db.add_or_inc_link(_PREV_TOKEN_TABLE, expr_id,
                                   self._end_token_id, c=c)

            if i > 0:
                # link prev token to this expr
                prev_token = token_ids[i-1]
                db.add_or_inc_link(_PREV_TOKEN_TABLE, expr_id, prev_token, c=c)

            if i < n_exprs:
                # link next token to this expr
                next_token = token_ids[i+self.order]
                db.add_or_inc_link(_NEXT_TOKEN_TABLE, expr_id, next_token, c=c)

            if i == n_exprs:
                # add link to boundary on next_token
                db.add_or_inc_link(_NEXT_TOKEN_TABLE, expr_id,
                                   self._end_token_id, c=c)

        if commit:
            db.commit()

    def reply(self, text):
        tokens = self.tokenizer.split(text.decode("utf-8"))

        db = self._db
        c = db.cursor()

        token_ids = self._get_known_tokens(tokens, c)

        best_score = 0.
        best_reply = None

        for i in xrange(100):
            (reply, score) = self._generate_reply(token_ids)

            if score > best_score:
                best_score = score
                best_reply = reply

        if best_reply is None:
            return "I don't know enough to answer you yet!"

        # look up the words for these tokens
        text = []
        for token_id in best_reply:
            text.append(db.get_token_text(token_id))

        return "".join(text)

    def _babble(self):
        return "I don't know enough to reply to that!"

    def _generate_reply(self, token_ids):
        # generate a reply containing one of token_ids

        db = self._db

        if len(token_ids) == 0:
            return self._babble()

        pivot_token_id = random.choice(token_ids)
        pivot_expr_id = db.get_random_expr(pivot_token_id)
        while pivot_expr_id is None:
            pivot_token_id = random.choice(token_ids)
            pivot_expr_id = db.get_random_expr(pivot_token_id)

        next_token_ids = db.follow_chain(_NEXT_TOKEN_TABLE, pivot_expr_id)
        prev_token_ids = db.follow_chain(_PREV_TOKEN_TABLE, pivot_expr_id)
        prev_token_ids.reverse()

        # strip the original expr from the prev reply
        prev_token_ids = prev_token_ids[:-self.order]

        all_tokens = prev_token_ids
        all_tokens.extend(next_token_ids)

        reply = []
        score = 0.

        for token in all_tokens:
            reply.append(token[0])
            score = score - math.log(token[1], 2)

        return reply, score

    def _get_known_tokens(self, tokens, c):
        db = self._db

        token_ids = []

        for token in tokens:
            token_id = db.get_token_id(token, c=c)
            if token_id is not None:
                token_ids.append(token_id)

        return token_ids

    def _get_or_register_tokens(self, c, tokens):
        db = self._db

        token_ids = []
        for token in tokens:
            token_id = db.get_token_id(token, c=c)
            if token_id is None:
                if re.search("\s", token):
                    is_whitespace = True
                else:
                    is_whitespace = False

                token_id = db.insert_token(token, is_whitespace, c=c)

            token_ids.append(token_id)

        return token_ids

    def _get_or_register_expr(self, c, token_ids):
        db = self._db
        expr_id = db.get_expr_by_token_ids(token_ids, c=c)

        if expr_id is None:
            expr_id = db.insert_expr(token_ids, c=c)

        return expr_id

    @staticmethod
    def init(filename, order=5, create_indexes=True):
        """Initialize a brain. This brain's file must not already exist."""

        log.info("Initializing a hal brain.")

        db = Db(sqlite3.connect(filename))
        db.init(order, create_indexes)

class Db:
    """Database functions to support a Hal brain."""
    def __init__(self, conn):
        self._conn = conn

        if self.is_initted():
            self._order = int(self.get_info_text("order"))
            self._end_token_id = self.get_token_id(_END_TOKEN_TEXT)

            self._all_tokens = ",".join(["token%d_id" % i 
                                         for i in xrange(self._order)])
            self._all_token_args = " AND ".join(["token%d_id = ?" % i
                                                 for i in xrange(self._order)])
            self._all_token_q = ",".join(["?" for i in xrange(self._order)])

    def cursor(self):
        return self._conn.cursor()

    def commit(self):
        return self._conn.commit()

    def close(self):
        return self._conn.close()

    def is_initted(self, c=None):
        if c is None:
            c = self.cursor()

        try:
            self.get_info_text("order")
            return True
        except sqlite3.OperationalError:
            return False

    def set_info_text(self, attribute, text, c=None):
        if c is None:
            c = self.cursor()

        # FIXME: needs to UPDATE if the key already exists

        q = "INSERT INTO info (attribute, text) VALUES (?, ?)"
        c.execute(q, (attribute, text))

    def get_info_text(self, attribute, c=None):
        if c is None:
            c = self.cursor()

        q = "SELECT text FROM info WHERE attribute = ?"
        row = c.execute(q, (attribute,)).fetchone()
        if row:
            return row[0]

    def get_token_id(self, token, c=None):
        if c is None:
            c = self.cursor()

        q = "SELECT id FROM tokens WHERE text = ?"
        row = c.execute(q, (token,)).fetchone()
        if row:
            return int(row[0])

    def get_token_text(self, token_id, c=None):
        if c is None:
            c = self.cursor()

        q = "SELECT text FROM tokens WHERE id = ?"
        row = c.execute(q, (token_id,)).fetchone()
        if row:
            return row[0]

    def get_token_texts(self, token_ids, c=None):
        if c is None:
            c = self.cursor()

        return "".join([self.get_token_text(token_id)
                        for token_id in token_ids])

    def _get_expr_token_ids(self, expr_id, c):
        q = "SELECT count,%s FROM expr WHERE id = ?" % self._all_tokens
        return c.execute(q, (expr_id,)).fetchone()

    def insert_token(self, token, is_whitespace, c=None):
        if c is None:
            c = self.cursor()

        q = "INSERT INTO tokens (text, is_whitespace) VALUES (?, ?)"
        c.execute(q, (token, is_whitespace))
        return c.lastrowid

    def insert_expr(self, token_ids, c=None):
        if c is None:
            c = self.cursor()

        q = "INSERT INTO expr (count,%s) VALUES (0,%s)" % (self._all_tokens,
                                                           self._all_token_q)

        c.execute(q, token_ids)
        return c.lastrowid

    def inc_expr_count(self, expr_id, c=None):
        if c is None:
            c = self.cursor()

        q = "UPDATE expr SET count = count + 1 WHERE id = ?"
        c.execute(q, (expr_id,))

    def _count_expr_token_links(self, table, expr_id, token_id, c=None):
        if c is None:
            c = self.cursor()

        q = "SELECT count FROM %s WHERE expr_id = ? AND token_id = ?" % table
        row = c.execute(q, (expr_id, token_id)).fetchone()
        if row:
            return int(row[0])

    def add_or_inc_link(self, table, expr_id, token_id, c=None):
        if c is None:
            c = self.cursor()

        count = self._count_expr_token_links(table, expr_id, token_id, c)

        if count is not None:
            q = "UPDATE %s SET count = count + 1 WHERE expr_id = ? AND token_id = ?" % table
            c.execute(q, (expr_id, token_id))
        else:
            q = "INSERT INTO %s (expr_id, token_id, count) VALUES (?, ?, ?)" % table
            c.execute(q, (expr_id, token_id, 1))

    def get_random_expr(self, token_id, c=None):
        if c is None:
            c = self.cursor()

        q = "SELECT id FROM expr WHERE token0_id = ? ORDER BY RANDOM()"
        row = c.execute(q, (token_id,)).fetchone()
        if row:
            return int(row[0])

    def get_expr_by_token_ids(self, token_ids, c):
        q = "SELECT id FROM expr WHERE %s" % self._all_token_args

        row = c.execute(q, token_ids).fetchone()
        if row:
            return int(row[0])

    def _get_expr_and_count_by_token_ids(self, token_ids, c):
        q = "SELECT id, count FROM expr WHERE %s" % self._all_token_args

        row = c.execute(q, token_ids).fetchone()
        if row:
            return int(row[0]), int(row[1])

    def _get_expr_count(self, expr_id, c):
        q = "SELECT count FROM expr WHERE id = ?"

        row = c.execute(q, expr_id).fetchone()
        if row:
            return int(row[0])

    def follow_chain(self, table, expr_id, c=None):
        if c is None:
            c = self.cursor()

        expr_info = self._get_expr_token_ids(expr_id, c)
        next_expr_count = expr_info[0]
        next_token_ids = expr_info[1:]

        chain = [(token_id, 1.0) for token_id in next_token_ids]

        # pick a random next_token given the things in expr_id
        q = "SELECT token_id, count FROM %s WHERE expr_id = ? ORDER BY RANDOM()" % table

        row = c.execute(q, (expr_id,)).fetchone()
        next_token_id, next_token_count = row

        while next_token_id != self._end_token_id:
            chain.append((next_token_id,
                          float(next_token_count) / float(next_expr_count)))

            if table == _NEXT_TOKEN_TABLE:
                next_token_ids = list(next_token_ids[1:])
                next_token_ids.append(next_token_id)
            else:
                new_next_token_ids = [next_token_id]
                new_next_token_ids.extend(next_token_ids[:-1])
                next_token_ids = new_next_token_ids

            next_expr_id, next_expr_count = self._get_expr_and_count_by_token_ids(next_token_ids, c)

            row = c.execute(q, (next_expr_id,)).fetchone()
            next_token_id, next_token_count = row

        return chain

    def init(self, order, create_indexes):
        c = self.cursor()

        log.debug("Creating table: info")
        c.execute("""
CREATE TABLE info (
    attribute TEXT NOT NULL PRIMARY KEY,
    text TEXT NOT NULL)""")

        log.debug("Creating table: tokens")
        c.execute("""
CREATE TABLE tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT UNIQUE NOT NULL,
    is_whitespace INTEGER NOT NULL)""")

        tokens = []
        for i in xrange(order):
            tokens.append("token%d_id INTEGER NOT NULL REFERENCES token(id)" % i)

        log.debug("Creating table: expr")
        c.execute("""
CREATE TABLE expr (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    count INTEGER NOT NULL,
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

        # create a token for the end of a chain
        self.insert_token(_END_TOKEN_TEXT, 0, c=c)

        # save the order of this brain
        self.set_info_text("order", str(order), c=c)

        if create_indexes:
            c.execute("""
CREATE INDEX tokens_text on tokens (text)""")

            for i in xrange(order):
                c.execute("""
CREATE INDEX expr_token%d_id on expr (token%d_id)""" % (i, i))

            token_ids = ",".join(["token%d_id" % i for i in xrange(order)])
            c.execute("""
CREATE INDEX expr_token_ids on expr (%s)""" % token_ids)

            c.execute("""
CREATE INDEX next_token_expr_id ON next_token (expr_id)""")

            c.execute("""
CREATE INDEX prev_token_expr_id ON prev_token (expr_id)""")

        self.commit()
        c.close()
        self.close()
