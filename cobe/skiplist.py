# Copyright (C) 2013 Peter Teichman

import math
import random


class Skiplist(object):
    """A dict-like data structure storing its data in a skiplist"""
    def __init__(self, maxsize=65535):
        self.max_level = max(1, int(math.floor(math.log(maxsize, 2))))
        self.level = 1

        self.head = self._make_node(self.max_level, None, None)
        self.finger = self._make_update()

        self._find_prev = self._find_prev_from_head

    def _make_node(self, level, key, value):
        # each node is a list with this layout:
        # [ key, value, level1_next, level2_next, ... ]
        node = [None] * (2 + level)
        node[0] = key
        node[1] = value

        return node

    def _make_update(self):
        return [None] * self.max_level

    def _random_level(self):
        # assume p=0.5; use each successive bit of r as a uniformly
        # distributed random number
        r = random.getrandbits(self.max_level)

        return max(1, self._count_low_set_bits(r))

    def _count_low_set_bits(self, num):
        ret = 0
        while num & 1:
            ret += 1
            num >>= 1

        return ret

    def _find_prev_from_head(self, key, update):
        node = self.head
        for i in reversed(xrange(self.level)):
            while node[2 + i] is not None and node[2 + i][0] < key:
                node = node[2 + i]
            update[i] = node

        return node

    def get(self, key, default=None):
        update = self._make_update()

        node = self._find_prev(key, update)[2]
        if node is not None and node[0] == key:
            return node[1]

        return default

    def insert(self, key, value):
        update = self._make_update()

        node = self._find_prev(key, update)[2]
        if node is not None and node[0] == key:
            node[1] = value
            return

        level = self._random_level()
        assert level <= self.max_level

        if level > self.level:
            for i in reversed(xrange(level, self.level + 1)):
                update[i] = self.head
            self.level = level

        x = self._make_node(level, key, value)
        for i in xrange(level):
            if update[i] is not None:
                x[2 + i] = update[i][2 + i]
                update[i][2 + i] = x

    def delete(self, key):
        update = self._make_update()

        node = self._find_prev(key, update)[2]
        if node is None or node[0] != key:
            return

        # Remove node from any item in update where it's next
        for i in xrange(self.level):
            if update[i][2] != node:
                break
            update[i][2] = node[2]

        while self.level > 1 and self.head[1 + self.level] is None:
            self.level -= 1

    def items(self):
        node = self.head
        while node[2] is not None:
            node = node[2]
            yield node[0], node[1]
