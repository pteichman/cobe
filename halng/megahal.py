import bisect
import logging
import re
import struct

log = logging.getLogger("megahal")

class Direction:
    NEXT, PREV = range(2)

class Brain:
    COOKIE = "MegaHALv8"

    order_struct = struct.Struct("=B")
    node_struct = struct.Struct("=HLHH")
    dict_len_struct = struct.Struct("=L")
    word_len_struct = struct.Struct("=B")
    
    def __init__(self, filename):
        self.filename = filename

        fd = open(filename)
        self.cookie = self.__read_cookie(fd)
        fd.close()

    def clone(self, conn):
        fd = open(self.filename)

        c = conn.cursor()

        self.__read_cookie(fd)
        self.__clone_order(fd, c)

        self.__clone_tree(fd, c, Direction.NEXT)
        self.__clone_tree(fd, c, Direction.PREV)

        self.__clone_dictionary(fd, c)
        
        conn.commit()

        fd.close()

    def __read_struct(self, fd, struct):
        data = fd.read(struct.size)
        return struct.unpack(data)

    def __read_cookie(self, fd):
        cookie = fd.read(len(self.COOKIE))
        if cookie != self.COOKIE:
            raise Exception("File is not a MegaHAL brain")
        return cookie

    def __clone_order(self, fd, c):
        log.debug("Reading order: %d bytes" % self.order_struct.size)
        self.order, = self.__read_struct(fd, self.order_struct)
        log.debug("Read order: %s" % str(self.order))

        # FIXME: assert that db order is the same

    def __clone_tree(self, fd, c, direction, context=None):
#        log.debug("Reading node: %d bytes" % self.node_struct.size)
        data = self.__read_struct(fd, self.node_struct)
        if direction != Direction.PREV and context and len(context) == self.order+1:
            log.debug("Read node: %s %s" % (str(data), context))

        if data[3] == 0:
            return

        node = list(data)

        if context is None:
            context = []

        if direction == Direction.NEXT:
            table_name = "next_token"
        elif direction == Direction.PREV:
            table_name = "prev_token"

        statement = "INSERT INTO %s (token0_id, token1_id, token2_id, token3_id) VALUES (?, ?, ?, ?)" % table_name

        context.append(node[0])

        tree = []
        for i in xrange(data[3]):
            subtree = self.__clone_tree(fd, c, direction, context)
            if subtree:
                pass
                # get or insert to get an expr_id
                # insert into table
#                tree.append(subtree)

        context.pop()

#        node.append(tree)
        
        return True

    def __clone_dictionary(self, fd, c):
        data = self.__read_struct(fd, self.dict_len_struct)

        ret = Dictionary()

        for i in xrange(data[0]):
            word = self.__read_word(fd)
            ret.add_word(word)

        return ret

    def __read_word(self, fd):
        data = self.__read_struct(fd, self.word_len_struct)
        word = fd.read(data[0])
        return word

class Dictionary:
    """Stores a WORD -> integer SYMBOL mapping"""
    def __init__(self):
        self.words = []

    def add_word(self, word):
        log.debug("Adding word to dictionary: %s (%d)" % (word, len(self.words)))

        t = (word, len(self.words))
        index = bisect.bisect(self.words, t)

        if index > 0 and self.words[index-1] == t:
            # don't insert, just return the symbol for WORD
            return self.words[index-1][1]

        self.words.insert(index, t)

        # return the symbol for this word
        return t[1]

    def get_symbol(self, word):
        words = self.dictionary
        index = self.__binary_search(words, word, 0, len(words))

        if index >= 0:
            return words[index][1]


class Hal:
    def __init__(self, brain):
        self._brain = brain
    
    def split(self, phrase):
        # add ending punctuation if it is missing
        if phrase[-1] not in ".!?":
            phrase = phrase + "."

        # megahal traditionally considers [a-z0-9] as word characters.
        # Let's see what happens if we add [_']
        words = re.findall("([\w']+|[^\w']+)", phrase.upper())
        return words
