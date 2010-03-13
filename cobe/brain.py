# Copyright (C) 2010 Peter Teichman

import logging
import math
import random
import re
import sqlite3
import time

import tokenizer

log = logging.getLogger("cobe")

# use an empty string to denote the start/end of a chain
_END_TOKEN_TEXT = ""
_NEXT_TOKEN_TABLE = "next_token"
_PREV_TOKEN_TABLE = "prev_token"

class Brain:
    def __init__(self, filename):
        self._db = db = Db(sqlite3.connect(filename))

        self.order = int(db.get_info_text("order"))

        self._end_token_id = db.get_token_id(_END_TOKEN_TEXT)
        self._learning = False

        self.tokenizer = tokenizer.CobeTokenizer()

    def start_batch_learning(self):
        self._learning = True

    def stop_batch_learning(self):
        self._learning = False
        self._db.commit()

    def learn(self, text):
        tokens = self.tokenizer.split(text.decode("utf-8"))

        if len(tokens) < self.order:
            log.debug("Input too short to learn: %s", text)
            return

        self._learn_tokens(tokens)

    def _learn_tokens(self, tokens):
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

        if not self._learning:
            db.commit()

    def reply(self, text):
        tokens = self.tokenizer.split(text.decode("utf-8"))

        db = self._db
        c = db.cursor()

        token_ids = self._get_known_word_tokens(tokens, c)

        best_score = None
        best_reply = None

        # loop for one second
        end = time.time() + 1

        while best_reply is None or time.time() < end:
            reply, score = self._generate_reply(token_ids)
            if reply is None:
                break

            if not best_score or score > best_score:
                best_score = score
                best_reply = reply

        if best_reply is None:
            return "I don't know enough to answer you yet!"

        # look up the words for these tokens
        text = []
        memo = {}
        for token_id in best_reply:
            text.append(memo.setdefault(token_id, db.get_token_text(token_id)))

        return self.tokenizer.join(text)

    def _babble(self, c):
        db = self._db

        token_id = None
        expr_id = None

        while expr_id is None:
            token_id = db.get_random_token(c=c)
            if token_id is None:
                return None, None

            expr_id = db.get_random_expr(token_id, c=c)

        return token_id, expr_id

    def _generate_reply(self, token_ids):
        # generate a reply containing one of token_ids
        db = self._db
        c = db.cursor()

        if len(token_ids) > 0:
            pivot_token_id = random.choice(token_ids)
            pivot_expr_id = db.get_random_expr(pivot_token_id, c=c)
        else:
            pivot_token_id, pivot_expr_id = self._babble(c)
            if pivot_token_id is None:
                return None, 0.

        next_token_ids = db.follow_chain(_NEXT_TOKEN_TABLE, pivot_expr_id, c=c)
        prev_token_ids = db.follow_chain(_PREV_TOKEN_TABLE, pivot_expr_id, c=c)
        prev_token_ids.reverse()

        # strip the original expr from the prev reply
        prev_token_ids = prev_token_ids[:-self.order]

        reply = prev_token_ids
        reply.extend(next_token_ids)

        score = self._evaluate_reply(token_ids, reply, c)

        return reply, score

    def _evaluate_reply(self, input_tokens, output_tokens, c):
        if len(output_tokens) == 0:
            return 0.

        db = self._db

        score = 0.

        # evaluate forward probabilities
        for output_idx in xrange(len(output_tokens)-self.order):
            output_token = output_tokens[output_idx+self.order]
            if output_token in input_tokens:
                expr = output_tokens[output_idx:output_idx+self.order]

                p = db.get_expr_token_probability(_NEXT_TOKEN_TABLE, expr,
                                                  output_token, c)
                if p > 0:
                    score = score - math.log(p, 2)

        # evaluate reverse probabilities
        for output_idx in xrange(len(output_tokens)-self.order):
            output_token = output_tokens[output_idx]
            if output_token in input_tokens:
                expr = output_tokens[output_idx+1:output_idx+self.order+1]

                p = db.get_expr_token_probability(_PREV_TOKEN_TABLE, expr,
                                                  output_token, c)
                if p > 0:
                    score = score - math.log(p, 2)

        # prefer smaller replies
        n_tokens = len(output_tokens)
        if n_tokens >= 8:
            score = score / math.sqrt(n_tokens-1)
        elif n_tokens >= 16:
            score = score / n_tokens

        return score

    def _get_known_word_tokens(self, tokens, c):
        db = self._db

        token_ids = []
        memo = {}

        for token in tokens:
            token_id = memo.setdefault(token, db.get_word_token_id(token, c=c))
            if token_id is not None:
                token_ids.append(token_id)

        return token_ids

    def _get_or_register_tokens(self, c, tokens):
        db = self._db

        token_ids = []
        memo = {}
        for token in tokens:
            token_id = memo.setdefault(token, db.get_token_id(token, c=c))
            if token_id is None:
                if re.search("\w", token):
                    is_word = True
                else:
                    is_word = False

                token_id = db.insert_token(token, is_word, c=c)
                memo[token] = token_id

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

        log.info("Initializing a cobe brain: %s" % filename)

        db = Db(sqlite3.connect(filename))
        db.init(order, create_indexes)

class Db:
    """Database functions to support a Cobe brain."""
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

        if text is None:
            q = "DELETE FROM info WHERE attribute = ?"
            c.execute(q, (attribute,))
        else:
            q = "SELECT count(*) FROM info WHERE attribute = ?"
            row = c.execute(q, (attribute,)).fetchone()

            if row and row[0] > 0:
                q = "UPDATE info SET text = ? WHERE attribute = ?"
                c.execute(q, (text, attribute))
            else:
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

    def get_random_token(self, c=None):
        if c is None:
            c = self.cursor()

        # get the count of tokens
        q = "SELECT MAX(id) from tokens"
        row = c.execute(q).fetchone()
        if not row:
            return None

        count = int(row[0])

        if count == 1:
            return None

        # assume end_token was the first token inserted
        return random.randint(self._end_token_id+1, count-1)

    def get_word_token_id(self, token, c=None):
        if c is None:
            c = self.cursor()

        q = "SELECT id FROM tokens WHERE text = ? AND is_word = 1"
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

    def _get_expr_token_ids(self, expr_id, c):
        q = "SELECT %s FROM expr WHERE id = ?" % self._all_tokens
        return c.execute(q, (expr_id,)).fetchone()

    def insert_token(self, token, is_word, c=None):
        if c is None:
            c = self.cursor()

        q = "INSERT INTO tokens (text, is_word) VALUES (?, ?)"
        c.execute(q, (token, is_word))
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

        # try looking for the token in a random spot in the exprs
        positions = range(self._order)
        random.shuffle(positions)

        for pos in positions:
            q = "SELECT count(id) FROM expr WHERE token%d_id = ?" % pos
            row = c.execute(q, (token_id,)).fetchone()
            count = row[0]

            if count == 0:
                continue
            elif count == 1:
                offset = 0
            else:
                offset = random.randint(0, count-1)

            q = "SELECT id FROM expr WHERE token%d_id = ? LIMIT 1 OFFSET ?" \
                % pos

            row = c.execute(q, (token_id, offset)).fetchone()
            if row:
                return int(row[0])

    def get_expr_by_token_ids(self, token_ids, c):
        q = "SELECT id FROM expr WHERE %s" % self._all_token_args

        row = c.execute(q, token_ids).fetchone()
        if row:
            return int(row[0])

    def _get_expr_token_count(self, table, expr_id, token_id, c):
        q = "SELECT count FROM %s WHERE expr_id = ? AND token_id = ?" % table

        row = c.execute(q, (expr_id, token_id)).fetchone()
        if row:
            return int(row[0])

    def get_expr_token_probability(self, table, expr, token_id, c=None):
        if c is None:
            c = self.cursor()

        expr_id, expr_count = self._get_expr_and_count_by_token_ids(expr, c)
        token_count = self._get_expr_token_count(table, expr_id, token_id, c)

        if token_count is None:
            return 0.

        return float(token_count) / float(expr_count)

    def _get_expr_and_count_by_token_ids(self, token_ids, c):
        q = "SELECT id, count FROM expr WHERE %s" % self._all_token_args

        row = c.execute(q, token_ids).fetchone()
        if row:
            return int(row[0]), int(row[1])

    def _get_expr_count(self, expr_id, c):
        q = "SELECT count FROM expr WHERE id = ?"

        row = c.execute(q, (expr_id,)).fetchone()
        if row:
            return int(row[0])

    def _get_random_next_token(self, table, expr_id, c):
        # try to limit the table sort to 1/10 the available data
        q = "SELECT token_id FROM %s WHERE expr_id = ? AND RANDOM()>0.9 ORDER BY RANDOM()" % table
        row = c.execute(q, (expr_id,)).fetchone()
        if row is None:
            q = "SELECT token_id FROM %s WHERE expr_id = ? ORDER BY RANDOM()" % table
            row = c.execute(q, (expr_id,)).fetchone()

        return row[0]

    def follow_chain(self, table, expr_id, c=None):
        if c is None:
            c = self.cursor()

        # initialize the chain with the current expr's tokens
        chain = list(self._get_expr_token_ids(expr_id, c))
        expr_token_ids = chain[:]

        # pick a random next_token that can follow expr_id
        next_token_id = self._get_random_next_token(table, expr_id, c)
        while next_token_id != self._end_token_id:
            chain.append(next_token_id)

            if table == _NEXT_TOKEN_TABLE:
                expr_token_ids = expr_token_ids[1:] + [next_token_id]
            else:
                expr_token_ids = [next_token_id] + expr_token_ids[:-1]

            expr_id = self.get_expr_by_token_ids(expr_token_ids, c)
            next_token_id = self._get_random_next_token(table, expr_id, c)

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
    is_word INTEGER NOT NULL)""")

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
CREATE INDEX next_token_expr_id ON next_token (expr_id, token_id)""")

            c.execute("""
CREATE INDEX prev_token_expr_id ON prev_token (expr_id, token_id)""")

        self.commit()
        c.close()
        self.close()
