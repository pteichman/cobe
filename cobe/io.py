# Copyright (C) 2013 Peter Teichman

import os


def open_linelog(filename, callback):
    fd = open(filename, "a+b")
    fd.seek(0, os.SEEK_SET)

    for line in fd:
        callback(line[:-1])

    return lambda line: fd.write(line + "\n")
