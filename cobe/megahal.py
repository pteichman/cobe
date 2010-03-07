import bisect
import logging
import struct

log = logging.getLogger("cobe")
log.addHandler(logging.StreamHandler())

class Brain:
    COOKIE = "MegaHALv8"

    order_struct = struct.Struct("=B")
    node_struct = struct.Struct("=HLHH")
    dict_len_struct = struct.Struct("=L")
    word_len_struct = struct.Struct("=B")

    def __init__(self, filename):
        fd = open(filename)

        self.cookie = self.__read_cookie(fd)
        self.order = self.__read_order(fd)

        self.forward = self.__read_tree(fd)
        self.backward = self.__read_tree(fd)

        self.dictionary = self.__read_dictionary(fd)

        fd.close()

    def __read_struct(self, fd, struct):
        data = fd.read(struct.size)
        return struct.unpack(data)

    def __read_cookie(self, fd):
        cookie = fd.read(len(self.COOKIE))
        if cookie != self.COOKIE:
            raise Exception("File is not a MegaHAL brain")
        return cookie

    def __read_order(self, fd):
        log.debug("Reading order: %d bytes" % self.order_struct.size)
        order = self.__read_struct(fd, self.order_struct)
        log.debug("Read order: %s" % str(order))
        return order[0]

    def __read_tree(self, fd):
        log.debug("Reading node: %d bytes" % self.node_struct.size)
        data = self.__read_struct(fd, self.node_struct)
        log.debug("Read node: %s" % str(data))

        if data[3] == 0:
            return

        node = list(data)

        tree = []
        for i in xrange(data[3]):
            subtree = self.__read_tree(fd)
            if subtree:
                tree.append(subtree)

        node.append(tree)

        return node

    def __read_dictionary(self, fd):
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
