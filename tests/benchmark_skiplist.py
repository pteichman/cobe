# Copyright (C) 2013 Peter Teichman

import benchmark
import random

from cobe import skiplist


class BenchmarkSkiplist(benchmark.Benchmark):
    def setUp(self):
        self.size = 10000

        self.items = [("item%d" % i, "value%d" % i) for i in xrange(self.size)]
        self.inorder = list(self.items)

        self.randorder = list(self.items)
        random.shuffle(self.randorder)

    def test_insert_inorder(self):
        skip = skiplist.Skiplist(100000)
        for k, v in self.inorder:
            skip.insert(k, v)

    def test_insert_random(self):
        skip = skiplist.Skiplist(100000)
        for k, v in self.randorder:
            skip.insert(k, v)

    def test_insert_toosmall_inorder(self):
        skip = skiplist.Skiplist(100)
        for k, v in self.inorder:
            skip.insert(k, v)

    def test_insert_toosmall_random(self):
        skip = skiplist.Skiplist(100)
        for k, v in self.randorder:
            skip.insert(k, v)


if __name__ == "__main__":
    benchmark.main(format="markdown", numberFormat="%0.4g")
