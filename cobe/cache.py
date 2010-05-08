# Copyright (C) 2010 Peter Teichman

class LRUCache:
    def __init__(self, num_items=100):
        self._num_items = num_items

        self._cache = {}
        self._order = []

    def _touch(self, key):
        try:
            self._order.remove(key)
        except ValueError:
            # ignore the error, the key didn't exist
            pass

        self._order.insert(0, key)
        while len(self._order) > self._num_items:
            oldest_key = self._order[-1]
            del self._cache[oldest_key]
            self._order.pop()

    def __getitem__(self, key):
        value = self._cache[key]
        self._touch(key)
        return value

    def __setitem__(self, key, value):
        self._cache[key] = value
        self._touch(key)

    def __len__(self):
        return len(self._cache)
