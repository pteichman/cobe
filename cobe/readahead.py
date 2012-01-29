# Copyright (C) 2012 Peter Teichman

# Utilities to force a file into the kernel cache on various operating
# systems.

import logging
import os
import platform

_readahead_impl = None

def readahead(filename):
    global _readahead_impl
    if _readahead_impl is None:
        _readahead_impl = _detect_platform()
    _readahead_impl(filename)

def _readahead_linux(readahead_func, filename):
    try:
        fd = os.open(filename, os.O_RDONLY)
        readahead_func(fd, 0, os.path.getsize(filename))
    finally:
        if fd != -1:
            os.close(fd)

def _readahead_naive(filename):
    with open(filename, "r+b") as fd:
        # read the database file in 4096 byte chunks
        while len(fd.read(2**12)) > 0:
            pass

def _detect_platform():
    global _readahead_func
    system = platform.system()

    try:
        import ctypes

        if system == "Linux":
            lib = ctypes.cdll.LoadLibrary("libc.so.6")

            # Use readahead rather than posix_fadvise. They do largely
            # the same thing, but readahead doesn't require us to
            # hardcode a constant for POSIX_FADV_WILLNEED.

            return lambda f: _readahead_linux(lib.readahead, f)
    except:
        logging.warn("Exception configuring readahead", exc_info=True)

    return _readahead_naive
