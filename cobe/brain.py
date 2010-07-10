# Copyright (C) 2010 Peter Teichman

import collections
import logging
import math
import os
import random
import re
import sqlite3
import time
import types

from .instatrace import Instatrace
from . import tokenizers

log = logging.getLogger("cobe")

# use an empty string to denote the start/end of a chain
_END_TOKEN_TEXT = ""
_NEXT_TOKEN_TABLE = "next_token"
_PREV_TOKEN_TABLE = "prev_token"

_trace = Instatrace()

class Brain:
    """The main interface for Cobe."""
    def __init__(self, filename, instatrace=None):
        """Construct a brain for the specified filename. If that file
        doesn't exist, it will be initialized with the default brain
        settings."""
        if not os.path.exists(filename):
            log.info("File does not exist. Assuming defaults.")
            Brain.init(filename)

        if instatrace is not None:
            _trace.init(instatrace)

        _start = _trace.now()
        self._db = db = _Db(sqlite3.connect(filename))
        _trace.trace("Brain.connect_us", _trace.now()-_start)

        self.order = int(db.get_info_text("order"))

        tokenizer_name = db.get_info_text("tokenizer")
        if tokenizer_name == "MegaHAL":
            self.tokenizer = tokenizers.MegaHALTokenizer()
        else:
            self.tokenizer = tokenizers.CobeTokenizer()

        self._end_token_id = db.get_token_id(_END_TOKEN_TEXT)
        self._learning = False

    def start_batch_learning(self):
        """Begin a series of batch learn operations. Data will not be
        committed to the database until stop_batch_learning is
        called. Learn text using the normal learn(text) method."""
        self._learning = True

    def stop_batch_learning(self):
        """Finish a series of batch learn operations."""
        self._learning = False
        self._db.commit()

    def learn(self, text):
        """Learn a string of text. If the input is not already
        Unicode, it will be decoded as utf-8."""
        if type(text) != types.UnicodeType:
            # Assume that non-Unicode text is encoded as utf-8, which
            # should be somewhat safe in the modern world.
            text = text.decode("utf-8", "ignore")

        tokens = self.tokenizer.split(text)
        _trace.trace("Brain.learn_input_token_count", len(tokens))

        if len(tokens) < self.order:
            log.debug("Input too short to learn: %s", text)
            return

        self._learn_tokens(tokens)

    def _learn_tokens(self, tokens):
        db = self._db
        c = db.cursor()

        token_ids = self._get_or_register_tokens(c, tokens)
        n_exprs = len(token_ids)-self.order

        # increment seen count for each token
        db.inc_token_counts(token_ids, c=c)

        links = []

        for i in xrange(n_exprs+1):
            expr = token_ids[i:i+self.order]
            expr_id = self._get_or_register_expr(c, expr)

            # increment the expr count
            db.inc_expr_count(expr_id, c=c)

            if i == 0:
                # add link to boundary on prev_token
                links.append((_PREV_TOKEN_TABLE, expr_id, self._end_token_id))

            if i > 0:
                # link prev token to this expr
                prev_token = token_ids[i-1]
                links.append((_PREV_TOKEN_TABLE, expr_id, prev_token))

            if i < n_exprs:
                # link next token to this expr
                next_token = token_ids[i+self.order]
                links.append((_NEXT_TOKEN_TABLE, expr_id, next_token))

            if i == n_exprs:
                # add link to boundary on next_token
                links.append((_NEXT_TOKEN_TABLE, expr_id, self._end_token_id))

        if len(links) > 0:
            db.add_or_inc_links(links, c=c)

        if not self._learning:
            db.commit()

    def reply(self, text):
        """Reply to a string of text. If the input is not already
        Unicode, it will be decoded as utf-8."""
        if type(text) != types.UnicodeType:
            # Assume that non-Unicode text is encoded as utf-8, which
            # should be somewhat safe in the modern world.
            text = text.decode("utf-8", "ignore")

        tokens = self.tokenizer.split(text)
        _trace.trace("Brain.reply_input_token_count", len(tokens))

        db = self._db
        c = db.cursor()

        token_infos = self._get_token_info(tokens, c)

        # Calculate the probability for using each of these tokens as
        # the pivot. This scores rare words higher, so we'll generate
        # fewer replies from common words.
        token_probs = self._get_pivot_probabilities(token_infos)

        _trace.trace("Brain.known_word_token_count", len(token_probs))

        # If we didn't recognize any word tokens in the input, pick
        # something random from the database and babble.
        if len(token_probs) == 0:
            token_probs = self._babble(c)

        best_score = None
        best_reply = None

        # loop for half a second
        start = time.time()
        end = start + 0.5
        count = 0
        similar_count = 0

        memo = {}

        _start = _trace.now()
        while best_reply is None or time.time() < end:
            _now = _trace.now()
            reply, score = self._generate_reply(token_probs, memo)
            _trace.trace("Brain.generate_reply_us", _trace.now()-_now)
            if reply is None:
                break

            _trace.trace("Brain.reply_output_token_count", len(reply))

            count += 1

            if best_score is not None \
                    and self._too_similar(token_infos, reply):
                similar_count += 1
                continue

            if not best_score or score > best_score:
                best_score = score
                best_reply = reply

        if best_reply is None:
            return "I don't know enough to answer you yet!"

        _time = _trace.now()-_start
        _trace.trace("Brain.reply_us", _time)
        _trace.trace("Brain.reply_count", count, _time)
        _trace.trace("Brain.similar_reply_count", similar_count, _time)
        _trace.trace("Brain.best_reply_score", int(best_score*1000))
        _trace.trace("Brain.best_reply_length", len(best_reply))
        log.debug("made %d replies in %f seconds" % (count, time.time()-start))

        _now = _trace.now()
        # look up the words for these tokens
        text = []
        memo = {}
        for token_id in best_reply:
            try:
                token_text = memo[token_id]
            except KeyError:
                token_text = db.get_token_text(token_id)
                memo[token_id] = token_text
            text.append(token_text)

        _trace.trace("Brain.reply_words_lookup_us", _trace.now()-_now)

        return self.tokenizer.join(text)

    def _too_similar(self, input_tokens, output_tokens):
        for t in zip(input_tokens, output_tokens):
            if t[0] is None or t[0][0] != t[1]:
                return False

        return True

    def _get_pivot_probabilities(self, token_counts):
        # Calculate the probability we wish to pick each token as the pivot.
        # This uses -log2(p) as a method for inverting token probability,
        # ensuring that our rarer tokens are picked more often.

        word_tokens = [token_info for token_info in token_counts
                       if token_info and token_info["is_word"]]

        if len(word_tokens) == 0:
            return []

        if len(word_tokens) == 1:
            return [(word_tokens[0]["id"], 1.0)]

        count_sum = 0
        for token_count in word_tokens:
            if token_count is not None:
                count_sum += token_count["count"]

        # calculate the (non-normalized) probability we want each to occur
        p = []
        p_sum = 0.
        for token in word_tokens:
            count = token["count"]
            token_p = -math.log(float(count) / count_sum, 2)

            p.append(token_p)
            p_sum += token_p

        # normalize the probabilities
        ret = []
        for t in zip(word_tokens, p):
            if t[0]["is_word"]:
                ret.append((t[0]["id"], t[1] / p_sum))

        return ret

    def _babble(self, c):
        # Generate a random input that can be used for reply generation
        token = self._db.get_random_token(c=c)
        if token:
            return [(token[0], 1.0)]
        return []

    def _choose_pivot(self, token_probs):
        r = random.random()

        cur = 0.
        for token in token_probs:
            cur += token[1]
            if r < cur:
                return token[0]

        # this should never happen if token_probs ranges 0..1.0, but
        # provide a fallthrough anyway
        return random.choice(token_probs)[0]

    def _generate_reply(self, token_probs, memo):
        if len(token_probs) == 0:
            return None, None

        # generate a reply containing one of token_ids
        db = self._db
        c = db.cursor()
        c.arraysize = 200

        token_ids = [token_prob[0] for token_prob in token_probs]
        pivot_token_id = self._choose_pivot(token_probs)
        pivot_expr_id = db.get_random_expr(pivot_token_id, c=c)

        next_token_ids = db.follow_chain(_NEXT_TOKEN_TABLE, pivot_expr_id,
                                         memo, c=c)
        prev_token_ids = db.follow_chain(_PREV_TOKEN_TABLE, pivot_expr_id,
                                         memo, c=c)

        # strip the original expr from the prev reply
        for i in xrange(self.order):
            prev_token_ids.pop()

        reply = prev_token_ids
        reply.extend(next_token_ids)

        _now = _trace.now()
        score = self._evaluate_reply(token_ids, list(reply), memo, c)

        _trace.trace("Brain.evaluate_reply_us", _trace.now()-_now)

        if log.isEnabledFor(logging.DEBUG) and score == 0:
            text = self._get_marked_text(reply, pivot_token_id)
            log.debug(text.encode("utf-8"))

        return reply, score

    def _evaluate_reply(self, input_tokens, output_tokens, memo, c):
        if len(output_tokens) == 0:
            return 0.

        # If input_tokens is empty (i.e. we didn't know any words in
        # the input), use output == input to make sure we still check
        # scoring
        if len(input_tokens) == 0:
            input_tokens = output_tokens

        db = self._db

        score = 0.

        next_memo = memo.setdefault(_NEXT_TOKEN_TABLE, {})
        prev_memo = memo.setdefault(_PREV_TOKEN_TABLE, {})

        # evaluate forward probabilities
        for output_idx in xrange(len(output_tokens)-self.order):
            output_token = output_tokens[output_idx+self.order]
            if output_token in input_tokens:
                expr = output_tokens[output_idx:output_idx+self.order]

                try:
                    key = (tuple(expr), output_token)
                    p = next_memo[key]
                except KeyError:
                    p = db.get_expr_token_probability(_NEXT_TOKEN_TABLE, expr,
                                                      output_token, c)
                    next_memo[key] = p

                if p > 0:
                    score -= math.log(p, 2)

        # evaluate reverse probabilities
        for output_idx in xrange(len(output_tokens)-self.order):
            output_token = output_tokens[output_idx]
            if output_token in input_tokens:
                expr = output_tokens[output_idx+1:output_idx+self.order+1]

                try:
                    key = (tuple(expr), output_token)
                    p = prev_memo[key]
                except KeyError:
                    p = db.get_expr_token_probability(_PREV_TOKEN_TABLE, expr,
                                                      output_token, c)
                    prev_memo[key] = p

                if p > 0:
                    score -= math.log(p, 2)

        raw_score = score

        # Prefer smaller replies. This behavior is present but not
        # documented in recent MegaHAL.
        score_divider = 1
        n_tokens = len(output_tokens)
        if n_tokens >= 8:
            score_divider = math.sqrt(n_tokens-1)
        elif n_tokens >= 16:
            score_divider = n_tokens

        score = score / score_divider
        _trace.trace("Brain.reply_score_divider", math.floor(score_divider))

        _trace.trace("Brain.reply_score", int(raw_score*1000))

        if score != raw_score:
            _trace.trace("Brain.adjusted_reply_score", int(score*1000),
                         raw_score/score)

        return score

    def _get_token_info(self, tokens, c):
        db = self._db

        token_infos = []
        memo = {}

        for token in tokens:
            try:
                token_info = memo[token]
            except KeyError:
                token_info = db.get_token_info(token, c=c)
                memo[token] = token_info

            token_infos.append(token_info)

        return token_infos

    def _get_or_register_tokens(self, c, tokens):
        db = self._db

        token_ids = []
        memo = {}
        for token in tokens:
            try:
                token_id = memo[token]
            except KeyError:
                token_id = db.get_token_id(token, c=c)
                memo[token] = token_id

            if token_id is None:
                if re.search("\w", token, re.UNICODE):
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

    def _get_marked_text(self, token_ids, pivot_token_id):
        db = self._db

        # look up the words for these tokens
        text = []
        memo = {}
        for token_id in token_ids:
            try:
                token = memo[token_id]
            except KeyError:
                token = db.get_token_text(token_id)
                memo[token_id] = token

            if token_id == pivot_token_id:
                token = "[%s]" % token
            text.append(token)

        return self.tokenizer.join(text)

    @staticmethod
    def init(filename, order=5, tokenizer=None):
        """Initialize a brain. This brain's file must not already exist.

Keyword arguments:
order -- Order of the forward/reverse Markov chains (integer)
tokenizer -- One of Cobe, MegaHAL (default Cobe). See documentation
             for cobe.tokenizers for details. (string)"""
        log.info("Initializing a cobe brain: %s" % filename)

        if tokenizer is None:
            tokenizer = "Cobe"

        if tokenizer not in ("Cobe", "MegaHAL"):
            log.info("Unknown tokenizer: %s. Using CobeTokenizer", tokenizer)
            tokenizer = "Cobe"

        db = _Db(sqlite3.connect(filename))

        _now = _trace.now()
        db.init(order, tokenizer)
        _trace.trace("Brain.init_time_us", _trace.now()-_now)

class _Db:
    """Database functions to support a Cobe brain. This is not meant
    to be used from outside."""
    def __init__(self, conn, run_migrations=True):
        self._conn = conn
        conn.row_factory = sqlite3.Row

        if self.is_initted():
            if run_migrations:
                self._run_migrations()

            self._order = int(self.get_info_text("order"))
            self._end_token_id = self.get_token_id(_END_TOKEN_TEXT)

            self._all_tokens = ",".join(["token%d_id" % i
                                         for i in xrange(self._order)])
            self._all_token_args = " AND ".join(["token%d_id = ?" % i
                                                 for i in xrange(self._order)])
            self._all_token_q = ",".join(["?" for i in xrange(self._order)])

            # construct partial subqueries for use when following chains
            next_parts = []
            prev_parts = []
            for i in xrange(self._order-1):
                next_parts.append("next_expr.token%d_id = expr.token%d_id" %
                                  (i, i+1))
                prev_parts.append("prev_expr.token%d_id = expr.token%d_id" %
                                  (i+1, i))
            next_query = " AND ".join(next_parts)
            prev_query = " AND ".join(prev_parts)

            self._next_chain_q = "SELECT next_expr.token%(last_token)d_id, next_expr.id FROM expr, expr AS next_expr WHERE expr.id = :expr_id AND next_expr.token%(last_token)d_id = (SELECT token_id FROM %(table)s WHERE expr_id = :expr_id LIMIT 1 OFFSET ifnull(random()%%(SELECT count(*) FROM %(table)s WHERE expr_id = :expr_id), 0)) AND %(subquery)s" \
                % { "last_token" : self._order-1,
                    "subquery" : next_query,
                    "table" : _NEXT_TOKEN_TABLE }

            self._prev_chain_q = "SELECT prev_expr.token0_id, prev_expr.id FROM expr, expr AS prev_expr WHERE expr.id = :expr_id AND prev_expr.token0_id = (SELECT token_id FROM %(table)s WHERE expr_id = :expr_id LIMIT 1 OFFSET ifnull(random()%%(SELECT count(*) FROM %(table)s WHERE expr_id = :expr_id), 0)) AND %(subquery)s" \
                % { "subquery" : prev_query,
                    "table" : _PREV_TOKEN_TABLE }

    def cursor(self):
        return self._conn.cursor()

    def commit(self):
        _start = _trace.now()
        ret = self._conn.commit()
        _trace.trace("Brain.db_commit_us", _trace.now()-_start)
        return ret

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
            q = "UPDATE info SET text = ? WHERE attribute = ?"
            c.execute(q, (text, attribute))

            if c.rowcount == 0:
                q = "INSERT INTO info (attribute, text) VALUES (?, ?)"
                c.execute(q, (attribute, text))

    def get_info_text(self, attribute, default=None, text_factory=None, c=None):
        if c is None:
            c = self.cursor()

        if text_factory is not None:
            old_text_factory = self._conn.text_factory
            self._conn.text_factory = text_factory

        q = "SELECT text FROM info WHERE attribute = ?"
        row = c.execute(q, (attribute,)).fetchone()

        if text_factory is not None:
            self._conn.text_factory = old_text_factory

        if row:
            return row[0]

        return default

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

        # select a random row from tokens
        q = "SELECT id, count FROM tokens WHERE id != ? AND id >= abs(random()) % (SELECT MAX(id) FROM tokens)"
        row = c.execute(q, (self._end_token_id,)).fetchone()

        if row:
            return row[0], row[1]

    def get_token_info(self, token, c=None):
        if c is None:
            c = self.cursor()

        q = "SELECT id, is_word, count FROM tokens WHERE text = ?"
        row = c.execute(q, (token,)).fetchone()
        if row:
            return row

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

        q = "INSERT INTO tokens (text, is_word, count) VALUES (?, ?, 0)"
        c.execute(q, (token, is_word))
        return c.lastrowid

    def insert_expr(self, token_ids, c=None):
        if c is None:
            c = self.cursor()

        q = "INSERT INTO expr (count,%s) VALUES (0,%s)" % (self._all_tokens,
                                                           self._all_token_q)

        c.execute(q, token_ids)
        return c.lastrowid

    def inc_token_counts(self, token_ids, c=None):
        if c is None:
            c = self.cursor()

        q = "UPDATE tokens SET count = count + 1 WHERE id = ?"
        for token_id in token_ids:
            c.execute(q, (token_id,))

    def inc_expr_count(self, expr_id, c=None):
        if c is None:
            c = self.cursor()

        q = "UPDATE expr SET count = count + 1 WHERE id = ?"
        c.execute(q, (expr_id,))

    def add_or_inc_links(self, links, c=None):
        if c is None:
            c = self.cursor()

        for (table, expr_id, token_id) in links:
            update_q = "UPDATE %s SET count = count + 1 WHERE expr_id = ? AND token_id = ?" % table
            c.execute(update_q, (expr_id, token_id))

            if c.rowcount == 0:
                insert_q = "INSERT INTO %s (expr_id, token_id, count) VALUES (?, ?, ?)" % table
                c.execute(insert_q, (expr_id, token_id, 1))

    def get_random_expr(self, token_id, c=None):
        if c is None:
            c = self.cursor()

        # try looking for the token in a random spot in the exprs
        positions = range(self._order)
        random.shuffle(positions)

        for pos in positions:
            q = "SELECT id FROM expr WHERE token%d_id = ? LIMIT 1 OFFSET ifnull(abs(random())%%(SELECT count(*) from expr WHERE token%d_id = ?), 0)" \
                % (pos, pos)

            row = c.execute(q, (token_id, token_id)).fetchone()
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

    def _get_random_next_token(self, table, expr_id, c):
        q = "SELECT token_id FROM %s WHERE expr_id = ? LIMIT 1 OFFSET ifnull(abs(random())%%(SELECT count(*) FROM %s WHERE expr_id = ?), 0)" % (table, table)

        c.execute(q, (expr_id, expr_id))

        row = c.fetchone()
        if row:
            return row[0]

    def follow_chain(self, table, expr_id, memo, c=None):
        if c is None:
            c = self.cursor()

        try:
            expr = memo[expr_id]
        except KeyError:
            expr = self._get_expr_token_ids(expr_id, c)
            memo[expr_id] = expr

        # initialize the chain with the current expr's tokens
        chain = collections.deque(expr)

        if table == _NEXT_TOKEN_TABLE:
            append = chain.append
            query = self._next_chain_q
        else:
            append = chain.appendleft
            query = self._prev_chain_q

        while True:
            # get the token
            c.execute(query, {"expr_id" : expr_id})

            row = c.fetchone()
            if not row or row[0] == self._end_token_id:
                break

            next_token_id, expr_id = row
            append(next_token_id)

        return chain

    def init(self, order, tokenizer, run_migrations=True):
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

        if run_migrations:
            self._run_migrations()

        # create a token for the end of a chain
        self.insert_token(_END_TOKEN_TEXT, 0, c=c)

        # save the order of this brain
        self.set_info_text("order", str(order), c=c)

        # save the tokenizer
        self.set_info_text("tokenizer", tokenizer)

        # save the brain/schema version
        self.set_info_text("version", "1")

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

    def _run_migrations(self):
        _start = _trace.now()
        self._maybe_add_token_counts()
        _trace.trace("Db.run_migrations_us", _trace.now()-_start)

    def _maybe_add_token_counts(self):
        c = self.cursor()

        try:
            c.execute("""
SELECT count FROM tokens LIMIT 1""")
        except sqlite3.OperationalError: # no such column: count
            self._add_token_counts(c)

        c.close()

    def _add_token_counts(self, c):
        log.info("SCHEMA UPDATE: adding token counts")
        _start = _trace.now_ms()

        c.execute("""
ALTER TABLE tokens ADD COLUMN count INTEGER""")

        read_c = self.cursor()

        log.info("extracting next token counts")

        q = read_c.execute("""
SELECT count(*) AS count, token_id AS id FROM next_token GROUP BY id""")

        for row in q:
            c.execute("""
UPDATE tokens SET count = ? WHERE id = ?""", (row[0], row[1]))

        self.commit()

        log.info("extracting prev token counts")

        # add counts for tokens that were never in next_token
        q = read_c.execute("""
SELECT count(*) AS count, token_id AS id FROM prev_token,tokens WHERE tokens.count IS NULL AND tokens.id = prev_token.token_id GROUP BY id""")

        for row in q:
            c.execute("""
UPDATE tokens SET count = ? WHERE id = ?""", tuple(row))

        # Some tokens can still have NULL counts, if they have only been
        # found in training input shorter than the current Markov order.
        # Set their counts to 1 to have valid data.
        c.execute("""
UPDATE tokens SET count = 1 WHERE count IS NULL""")

        self.commit()
        _trace.trace("Db.add_token_counts_us", _trace.now_ms()-_start)
