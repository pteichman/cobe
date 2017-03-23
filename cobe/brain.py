# Copyright (C) 2013 Peter Teichman

import collections
import itertools
import logging
import math
import operator
import os
import random
import re
import sqlite3
import time
import types

from .instatrace import trace, trace_ms, trace_us
from . import scoring
from . import tokenizers

log = logging.getLogger("cobe")


class CobeError(Exception):
    pass


class Brain:
    """The main interface for Cobe."""

    # use an empty string to denote the start/end of a chain
    END_TOKEN = ""

    # use a magic token id for (single) whitespace, so space is never
    # in the tokens table
    SPACE_TOKEN_ID = -1

    def __init__(self, filename):
        """Construct a brain for the specified filename. If that file
        doesn't exist, it will be initialized with the default brain
        settings."""
        if not os.path.exists(filename):
            log.info("File does not exist. Assuming defaults.")
            Brain.init(filename)

        with trace_us("Brain.connect_us"):
            self.graph = graph = Graph(sqlite3.connect(filename))

        version = graph.get_info_text("version")
        if version != "2":
            raise CobeError("cannot read a version %s brain" % version)

        self.order = int(graph.get_info_text("order"))

        self.scorer = scoring.ScorerGroup()
        self.scorer.add_scorer(1.0, scoring.CobeScorer())

        tokenizer_name = graph.get_info_text("tokenizer")
        if tokenizer_name == "MegaHAL":
            self.tokenizer = tokenizers.MegaHALTokenizer()
        else:
            self.tokenizer = tokenizers.CobeTokenizer()

        self.stemmer = None
        stemmer_name = graph.get_info_text("stemmer")

        if stemmer_name is not None:
            try:
                self.stemmer = tokenizers.CobeStemmer(stemmer_name)
                log.debug("Initialized a stemmer: %s" % stemmer_name)
            except Exception as e:
                log.error("Error creating stemmer: %s", str(e))

        self._end_token_id = \
            graph.get_token_by_text(self.END_TOKEN, create=True)

        self._end_context = [self._end_token_id] * self.order
        self._end_context_id = graph.get_node_by_tokens(self._end_context)

        self._learning = False

    def start_batch_learning(self):
        """Begin a series of batch learn operations. Data will not be
        committed to the database until stop_batch_learning is
        called. Learn text using the normal learn(text) method."""
        self._learning = True

        self.graph.cursor().execute("PRAGMA journal_mode=memory")
        self.graph.drop_reply_indexes()

    def stop_batch_learning(self):
        """Finish a series of batch learn operations."""
        self._learning = False

        self.graph.commit()
        self.graph.cursor().execute("PRAGMA journal_mode=truncate")
        self.graph.ensure_indexes()

    def del_stemmer(self):
        self.stemmer = None

        self.graph.delete_token_stems()

        self.graph.set_info_text("stemmer", None)
        self.graph.commit()

    def set_stemmer(self, language):
        self.stemmer = tokenizers.CobeStemmer(language)

        self.graph.delete_token_stems()
        self.graph.update_token_stems(self.stemmer)

        self.graph.set_info_text("stemmer", language)
        self.graph.commit()

    def learn(self, text):
        """Learn a string of text. If the input is not already
        Unicode, it will be decoded as utf-8."""
        if type(text) != types.UnicodeType:
            # Assume that non-Unicode text is encoded as utf-8, which
            # should be somewhat safe in the modern world.
            text = text.decode("utf-8", "ignore")

        tokens = self.tokenizer.split(text)
        trace("Brain.learn_input_token_count", len(tokens))

        self._learn_tokens(tokens)

    def _to_edges(self, tokens):
        """This is an iterator that returns the nodes of our graph:
"This is a test" -> "None This" "This is" "is a" "a test" "test None"

Each is annotated with a boolean that tracks whether whitespace was
found between the two tokens."""
        # prepend self.order Nones
        chain = self._end_context + tokens + self._end_context

        has_space = False

        context = []

        for i in xrange(len(chain)):
            context.append(chain[i])

            if len(context) == self.order:
                if chain[i] == self.SPACE_TOKEN_ID:
                    context.pop()
                    has_space = True
                    continue

                yield tuple(context), has_space

                context.pop(0)
                has_space = False

    def _to_graph(self, contexts):
        """This is an iterator that returns each edge of our graph
with its two nodes"""
        prev = None

        for context in contexts:
            if prev is None:
                prev = context
                continue

            yield prev[0], context[1], context[0]
            prev = context

    def _learn_tokens(self, tokens):
        token_count = len([token for token in tokens if token != " "])
        if token_count < 3:
            return

        # create each of the non-whitespace tokens
        token_ids = []
        for text in tokens:
            if text == " ":
                token_ids.append(self.SPACE_TOKEN_ID)
                continue

            token_id = self.graph.get_token_by_text(text, create=True,
                                                    stemmer=self.stemmer)
            token_ids.append(token_id)

        edges = list(self._to_edges(token_ids))

        prev_id = None
        for prev, has_space, next in self._to_graph(edges):
            if prev_id is None:
                prev_id = self.graph.get_node_by_tokens(prev)
            next_id = self.graph.get_node_by_tokens(next)

            self.graph.add_edge(prev_id, next_id, has_space)
            prev_id = next_id

        if not self._learning:
            self.graph.commit()

    def reply(self, text, loop_ms=500, max_len=None):
        """Reply to a string of text. If the input is not already
        Unicode, it will be decoded as utf-8."""
        if type(text) != types.UnicodeType:
            # Assume that non-Unicode text is encoded as utf-8, which
            # should be somewhat safe in the modern world.
            text = text.decode("utf-8", "ignore")

        tokens = self.tokenizer.split(text)
        input_ids = map(self.graph.get_token_by_text, tokens)

        # filter out unknown words and non-words from the potential pivots
        pivot_set = self._filter_pivots(input_ids)

        # Conflate the known ids with the stems of their words
        if self.stemmer is not None:
            self._conflate_stems(pivot_set, tokens)

        # If we didn't recognize any word tokens in the input, pick
        # something random from the database and babble.
        if len(pivot_set) == 0:
            pivot_set = self._babble()

        score_cache = {}

        best_score = -1.0
        best_reply = None

        # Loop for approximately loop_ms milliseconds. This can either
        # take more (if the first reply takes a long time to generate)
        # or less (if the _generate_replies search ends early) time,
        # but it should stay roughly accurate.
        start = time.time()
        end = start + loop_ms * 0.001
        count = 0

        all_replies = []

        _start = time.time()
        for edges, pivot_node in self._generate_replies(pivot_set):
            reply = Reply(self.graph, tokens, input_ids, pivot_node, edges)

            if max_len and self._too_long(max_len, reply):
                continue

            key = reply.edge_ids
            if key not in score_cache:
                with trace_us("Brain.evaluate_reply_us"):
                    score = self.scorer.score(reply)
                    score_cache[key] = score
            else:
                # skip scoring, we've already seen this reply
                score = -1

            if score > best_score:
                best_reply = reply
                best_score = score

            # dump all replies to the console if debugging is enabled
            if log.isEnabledFor(logging.DEBUG):
                all_replies.append((score, reply))

            count += 1
            if time.time() > end:
                break

        if best_reply is None:
            # we couldn't find any pivot words in _babble(), so we're
            # working with an essentially empty brain. Use the classic
            # MegaHAL reply:
            return "I don't know enough to answer you yet!"

        _time = time.time() - _start

        self.scorer.end(best_reply)

        if log.isEnabledFor(logging.DEBUG):
            replies = [(score, reply.to_text())
                       for score, reply in all_replies]
            replies.sort()

            for score, text in replies:
                log.debug("%f %s", score, text)

        trace("Brain.reply_input_token_count", len(tokens))
        trace("Brain.known_word_token_count", len(pivot_set))

        trace("Brain.reply_us", _time)
        trace("Brain.reply_count", count, _time)
        trace("Brain.best_reply_score", int(best_score * 1000))
        trace("Brain.best_reply_length", len(best_reply.edge_ids))

        log.debug("made %d replies (%d unique) in %f seconds"
                  % (count, len(score_cache), _time))

        if len(text) > 60:
            msg = text[0:60] + "..."
        else:
            msg = text

        log.info("[%s] %d %f", msg, count, best_score)

        # look up the words for these tokens
        with trace_us("Brain.reply_words_lookup_us"):
            text = best_reply.to_text()

        return text

    def _too_long(self, max_len, reply):
        text = reply.to_text()
        if len(text) > max_len:
            log.debug("over max_len [%d]: %s", len(text), text)
            return True

    def _conflate_stems(self, pivot_set, tokens):
        for token in tokens:
            stem_ids = self.graph.get_token_stem_id(self.stemmer.stem(token))
            if not stem_ids:
                continue

            # add the tuple of stems to the pivot set, and then
            # remove the individual token_ids
            pivot_set.add(tuple(stem_ids))
            pivot_set.difference_update(stem_ids)

    def _babble(self):
        token_ids = []
        for i in xrange(5):
            # Generate a few random tokens that can be used as pivots
            token_id = self.graph.get_random_token()

            if token_id is not None:
                token_ids.append(token_id)

        return set(token_ids)

    def _filter_pivots(self, pivots):
        # remove pivots that might not give good results
        tokens = set(filter(None, pivots))

        filtered = self.graph.get_word_tokens(tokens)
        if not filtered:
            filtered = self.graph.get_tokens(tokens) or []

        return set(filtered)

    def _pick_pivot(self, pivot_ids):
        pivot = random.choice(tuple(pivot_ids))

        if type(pivot) is types.TupleType:
            # the input word was stemmed to several things
            pivot = random.choice(pivot)

        return pivot

    def _generate_replies(self, pivot_ids):
        if not pivot_ids:
            return

        end = self._end_context_id
        graph = self.graph
        search = graph.search_random_walk

        # Cache all the trailing and beginning sentences we find from
        # each random node we search. Since the node is a full n-tuple
        # context, we can combine any pair of next_cache[node] and
        # prev_cache[node] and get a new reply.
        next_cache = collections.defaultdict(set)
        prev_cache = collections.defaultdict(set)

        while pivot_ids:
            # generate a reply containing one of token_ids
            pivot_id = self._pick_pivot(pivot_ids)
            node = graph.get_random_node_with_token(pivot_id)

            parts = itertools.izip_longest(search(node, end, 1),
                                           search(node, end, 0),
                                           fillvalue=None)

            for next, prev in parts:
                if next:
                    next_cache[node].add(next)
                    for p in prev_cache[node]:
                        yield p + next, node

                if prev:
                    prev = tuple(reversed(prev))
                    prev_cache[node].add(prev)
                    for n in next_cache[node]:
                        yield prev + n, node

    @staticmethod
    def init(filename, order=3, tokenizer=None):
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

        graph = Graph(sqlite3.connect(filename))

        with trace_us("Brain.init_time_us"):
            graph.init(order, tokenizer)


class Reply:
    """Provide useful support for scoring functions"""
    def __init__(self, graph, tokens, token_ids, pivot_node, edge_ids):
        self.graph = graph
        self.tokens = tokens
        self.token_ids = token_ids
        self.pivot_node = pivot_node
        self.edge_ids = edge_ids
        self.text = None

    def to_text(self):
        if self.text is None:
            parts = []
            for word, has_space in map(self.graph.get_text_by_edge,
                                       self.edge_ids):
                parts.append(word)
                if has_space:
                    parts.append(" ")

            self.text = "".join(parts)

        return self.text


class Graph:
    """A special-purpose graph class, stored in a sqlite3 database"""
    def __init__(self, conn, run_migrations=True):
        self._conn = conn
        conn.row_factory = sqlite3.Row

        if self.is_initted():
            if run_migrations:
                self._run_migrations()

            self.order = int(self.get_info_text("order"))

            self._all_tokens = ",".join(["token%d_id" % i
                                         for i in xrange(self.order)])
            self._all_tokens_args = " AND ".join(
                ["token%d_id = ?" % i for i in xrange(self.order)])
            self._all_tokens_q = ",".join(["?" for i in xrange(self.order)])
            self._last_token = "token%d_id" % (self.order - 1)

            # Disable the SQLite cache. Its pages tend to get swapped
            # out, even if the database file is in buffer cache.
            c = self.cursor()
            c.execute("PRAGMA cache_size=0")
            c.execute("PRAGMA page_size=4096")

            # Each of these speed-for-reliability tradeoffs is useful for
            # bulk learning.
            c.execute("PRAGMA journal_mode=truncate")
            c.execute("PRAGMA temp_store=memory")
            c.execute("PRAGMA synchronous=OFF")

    def cursor(self):
        return self._conn.cursor()

    def commit(self):
        with trace_us("Brain.db_commit_us"):
            self._conn.commit()

    def close(self):
        return self._conn.close()

    def is_initted(self):
        try:
            self.get_info_text("order")
            return True
        except sqlite3.OperationalError:
            return False

    def set_info_text(self, attribute, text):
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

    def get_info_text(self, attribute, default=None, text_factory=None):
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

    def get_seq_expr(self, seq):
        # Format the sequence seq as (item1, item2, item2) as appropriate
        # for an IN () clause in SQL
        if len(seq) == 1:
            # Grab the first item from seq. Use an iterator so this works
            # with sets as well as lists.
            return "(%s)" % iter(seq).next()

        return str(tuple(seq))

    def get_token_by_text(self, text, create=False, stemmer=None):
        c = self.cursor()

        q = "SELECT id FROM tokens WHERE text = ?"

        row = c.execute(q, (text,)).fetchone()
        if row:
            return row[0]
        elif create:
            q = "INSERT INTO tokens (text, is_word) VALUES (?, ?)"

            is_word = bool(re.search("\w", text, re.UNICODE))
            c.execute(q, (text, is_word))

            token_id = c.lastrowid
            if stemmer is not None:
                stem = stemmer.stem(text)
                if stem is not None:
                    self.insert_stem(token_id, stem)

            return token_id

    def insert_stem(self, token_id, stem):
        q = "INSERT INTO token_stems (token_id, stem) VALUES (?, ?)"
        self._conn.execute(q, (token_id, stem))

    def get_token_stem_id(self, stem):
        q = "SELECT token_id FROM token_stems WHERE token_stems.stem = ?"
        rows = self._conn.execute(q, (stem,))
        if rows:
            return map(operator.itemgetter(0), rows)

    def get_word_tokens(self, token_ids):
        q = "SELECT id FROM tokens WHERE id IN %s AND is_word = 1" % \
            self.get_seq_expr(token_ids)

        rows = self._conn.execute(q)
        if rows:
            return map(operator.itemgetter(0), rows)

    def get_tokens(self, token_ids):
        q = "SELECT id FROM tokens WHERE id IN %s" % \
            self.get_seq_expr(token_ids)

        rows = self._conn.execute(q)
        if rows:
            return map(operator.itemgetter(0), rows)

    def get_node_by_tokens(self, tokens):
        c = self.cursor()

        q = "SELECT id FROM nodes WHERE %s" % self._all_tokens_args

        row = c.execute(q, tokens).fetchone()
        if row:
            return int(row[0])

        # if not found, create the node
        q = "INSERT INTO nodes (count, %s) " \
            "VALUES (0, %s)" % (self._all_tokens, self._all_tokens_q)
        c.execute(q, tokens)
        return c.lastrowid

    def get_text_by_edge(self, edge_id):
        q = "SELECT tokens.text, edges.has_space FROM nodes, edges, tokens " \
            "WHERE edges.id = ? AND edges.prev_node = nodes.id " \
            "AND nodes.%s = tokens.id" % self._last_token

        return self._conn.execute(q, (edge_id,)).fetchone()

    def get_random_token(self):
        # token 1 is the end_token_id, so we want to generate a random token
        # id from 2..max(id) inclusive.
        q = "SELECT (abs(random()) % (MAX(id)-1)) + 2 FROM tokens"
        row = self._conn.execute(q).fetchone()
        if row:
            return row[0]

    def get_random_node_with_token(self, token_id):
        c = self.cursor()

        q = "SELECT id FROM nodes WHERE token0_id = ? " \
            "LIMIT 1 OFFSET abs(random())%(SELECT count(*) FROM nodes " \
            "                              WHERE token0_id = ?)"

        row = c.execute(q, (token_id, token_id)).fetchone()
        if row:
            return int(row[0])

    def get_edge_logprob(self, edge_id):
        # Each edge goes from an n-gram node (word1, word2, word3) to
        # another (word2, word3, word4). Calculate the probability:
        # P(word4|word1,word2,word3) = count(edge_id) / count(prev_node_id)

        c = self.cursor()
        q = "SELECT edges.count, nodes.count FROM edges, nodes " \
            "WHERE edges.id = ? AND edges.prev_node = nodes.id"

        edge_count, node_count = c.execute(q, (edge_id,)).fetchone()
        return math.log(edge_count, 2) - math.log(node_count, 2)

    def has_space(self, edge_id):
        c = self.cursor()

        q = "SELECT has_space FROM edges WHERE id = ?"

        row = c.execute(q, (edge_id,)).fetchone()
        if row:
            return bool(row[0])

    def add_edge(self, prev_node, next_node, has_space):
        c = self.cursor()

        assert type(has_space) == types.BooleanType

        update_q = "UPDATE edges SET count = count + 1 " \
            "WHERE prev_node = ? AND next_node = ? AND has_space = ?"

        q = "INSERT INTO edges (prev_node, next_node, has_space, count) " \
            "VALUES (?, ?, ?, 1)"

        args = (prev_node, next_node, has_space)

        c.execute(update_q, args)
        if c.rowcount == 0:
            c.execute(q, args)

        # The count on the next_node in the nodes table must be
        # incremented here, to register that the node has been seen an
        # additional time. This is now handled by database triggers.

    def search_bfs(self, start_id, end_id, direction):
        if direction:
            q = "SELECT id, next_node FROM edges WHERE prev_node = ?"
        else:
            q = "SELECT id, prev_node FROM edges WHERE next_node = ?"

        c = self.cursor()

        left = collections.deque([(start_id, tuple())])
        while left:
            cur, path = left.popleft()
            rows = c.execute(q, (cur,))

            for rowid, next in rows:
                newpath = path + (rowid,)

                if next == end_id:
                    yield newpath
                else:
                    left.append((next, newpath))

    def search_random_walk(self, start_id, end_id, direction):
        """Walk once randomly from start_id to end_id."""
        if direction:
            q = "SELECT id, next_node " \
                "FROM edges WHERE prev_node = :last " \
                "LIMIT 1 OFFSET abs(random())%(SELECT count(*) from edges " \
                "                              WHERE prev_node = :last)"
        else:
            q = "SELECT id, prev_node " \
                "FROM edges WHERE next_node = :last " \
                "LIMIT 1 OFFSET abs(random())%(SELECT count(*) from edges " \
                "                              WHERE next_node = :last)"

        c = self.cursor()

        left = collections.deque([(start_id, tuple())])
        while left:
            cur, path = left.popleft()
            rows = c.execute(q, dict(last=cur))

            # Note: the LIMIT 1 above means this list only contains
            # one row. Using a list here so this matches the bfs()
            # code, so the two functions can be more easily combined
            # later.
            for rowid, next in rows:
                newpath = path + (rowid,)

                if next == end_id:
                    yield newpath
                else:
                    left.append((next, newpath))

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
            tokens.append("token%d_id INTEGER REFERENCES token(id)" % i)

        log.debug("Creating table: token_stems")
        c.execute("""
CREATE TABLE token_stems (
    token_id INTEGER,
    stem TEXT NOT NULL)""")

        log.debug("Creating table: nodes")
        c.execute("""
CREATE TABLE nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    count INTEGER NOT NULL,
    %s)""" % ',\n    '.join(tokens))

        log.debug("Creating table: edges")
        c.execute("""
CREATE TABLE edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prev_node INTEGER NOT NULL REFERENCES nodes(id),
    next_node INTEGER NOT NULL REFERENCES nodes(id),
    count INTEGER NOT NULL,
    has_space INTEGER NOT NULL)""")

        if run_migrations:
            self._run_migrations()

        # save the order of this brain
        self.set_info_text("order", str(order))
        self.order = order

        # save the tokenizer
        self.set_info_text("tokenizer", tokenizer)

        # save the brain/schema version
        self.set_info_text("version", "2")

        self.commit()
        self.ensure_indexes()

        self.close()

    def drop_reply_indexes(self):
        self._conn.execute("DROP INDEX IF EXISTS edges_all_next")
        self._conn.execute("DROP INDEX IF EXISTS edges_all_prev")

        self._conn.execute("""
CREATE INDEX IF NOT EXISTS learn_index ON edges
    (prev_node, next_node)""")

    def ensure_indexes(self):
        c = self.cursor()

        # remove the temporary learning index if it exists
        c.execute("DROP INDEX IF EXISTS learn_index")

        token_ids = ",".join(["token%d_id" % i for i in xrange(self.order)])
        c.execute("""
CREATE UNIQUE INDEX IF NOT EXISTS nodes_token_ids on nodes
    (%s)""" % token_ids)

        c.execute("""
CREATE UNIQUE INDEX IF NOT EXISTS edges_all_next ON edges
    (next_node, prev_node, has_space, count)""")

        c.execute("""
CREATE UNIQUE INDEX IF NOT EXISTS edges_all_prev ON edges
    (prev_node, next_node, has_space, count)""")

    def delete_token_stems(self):
        c = self.cursor()

        # drop the two stem indexes
        c.execute("DROP INDEX IF EXISTS token_stems_stem")
        c.execute("DROP INDEX IF EXISTS token_stems_id")

        # delete all the existing stems from the table
        c.execute("DELETE FROM token_stems")

        self.commit()

    def update_token_stems(self, stemmer):
        # stemmer is a CobeStemmer
        with trace_ms("Db.update_token_stems_ms"):
            c = self.cursor()

            insert_c = self.cursor()
            insert_q = "INSERT INTO token_stems (token_id, stem) VALUES (?, ?)"

            q = c.execute("""
SELECT id, text FROM tokens""")

            for row in q:
                stem = stemmer.stem(row[1])
                if stem is not None:
                    insert_c.execute(insert_q, (row[0], stem))

            self.commit()

        with trace_ms("Db.index_token_stems_ms"):
            c.execute("""
CREATE INDEX token_stems_id on token_stems (token_id)""")
            c.execute("""
CREATE INDEX token_stems_stem on token_stems (stem)""")

    def _run_migrations(self):
        with trace_us("Db.run_migrations_us"):
            self._maybe_drop_tokens_text_index()
            self._maybe_create_node_count_triggers()

    def _maybe_drop_tokens_text_index(self):
        # tokens_text was an index on tokens.text, deemed redundant since
        # tokens.text is declared UNIQUE, and sqlite automatically creates
        # indexes for UNIQUE columns
        self._conn.execute("DROP INDEX IF EXISTS tokens_text")

    def _maybe_create_node_count_triggers(self):
        # Create triggers on the edges table to update nodes counts.
        # In previous versions, the node counts were updated with a
        # separate query. Moving them into triggers improves
        # performance.
        c = self.cursor()

        c.execute("""
CREATE TRIGGER IF NOT EXISTS edges_insert_trigger AFTER INSERT ON edges
    BEGIN UPDATE nodes SET count = count + NEW.count
        WHERE nodes.id = NEW.next_node; END;""")

        c.execute("""
CREATE TRIGGER IF NOT EXISTS edges_update_trigger AFTER UPDATE ON edges
    BEGIN UPDATE nodes SET count = count + (NEW.count - OLD.count)
        WHERE nodes.id = NEW.next_node; END;""")

        c.execute("""
CREATE TRIGGER IF NOT EXISTS edges_delete_trigger AFTER DELETE ON edges
    BEGIN UPDATE nodes SET count = count - old.count
        WHERE nodes.id = OLD.next_node; END;""")
