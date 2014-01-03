# Copyright (C) 2010 Peter Teichman

import datetime
import os
import time

from contextlib import contextmanager

_instatrace = None


def init_trace(filename):
    global _instatrace
    if _instatrace is not None:
        _instatrace.close()

    _instatrace = Instatrace(filename)


class Instatrace:
    def __init__(self, filename):
        # rotate logs if present
        if os.path.exists(filename):
            now = datetime.datetime.now()
            stamp = now.strftime("%Y-%m-%d.%H%M%S")
            os.rename(filename, "%s.%s" % (filename, stamp))

        self._fd = open(filename, "w")

    def now(self):
        """Microsecond resolution, integer now"""
        return int(time.time() * 100000)

    def now_ms(self):
        """Millisecond resolution, integer now"""
        return int(time.time() * 1000)

    def trace(self, stat, value, data=None):
        extra = ""
        if data is not None:
            extra = " " + repr(data)

        self._fd.write("%s %d%s\n" % (stat, value, extra))


def trace(stat, value, user_data=None):
    if _instatrace is not None:
        _instatrace.trace(stat, value, user_data)


@contextmanager
def trace_us(statName):
    if _instatrace is None:
        yield
        return

    # Microsecond resolution, integer now
    now = _instatrace.now()
    yield
    _instatrace.trace(statName, _instatrace.now() - now)


@contextmanager
def trace_ms(statName):
    if _instatrace is None:
        yield
        return

    # Millisecond resolution, integer now
    now = _instatrace.now_ms()
    yield
    _instatrace.trace(statName, _instatrace.now_ms() - now)
