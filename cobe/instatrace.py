# Copyright (C) 2010 Peter Teichman

import datetime
import math
import os
import time

def singleton(cls):
    instances = {}
    def getinstance():
        if cls not in instances:
            instances[cls] = cls()
        return instances[cls]
    return getinstance

@singleton
class Instatrace:
    def __init__(self):
        self._fd = None

    def init(self, filename):
        if self._fd is not None:
            self._fd.close()

        if filename is None:
            self._fd = None
        else:
        # rotate logs
            if os.path.exists(filename):
                now = datetime.datetime.now()
                stamp = now.strftime("%Y-%m-%d.%H%M%S")
                os.rename(filename, "%s.%s" % (filename, stamp))

            self._fd = open(filename, "w")

    def is_enabled(self):
        return self._fd is not None

    def now(self):
        """Microsecond resolution, integer now"""
        if not self.is_enabled():
            return 0
        return int(time.time()*100000)

    def now_ms(self):
        """Millisecond resolution, integer now"""
        if not self.is_enabled():
            return 0
        return int(time.time()*1000)

    def trace(self, statName, statValue, userData=None):
        if not self.is_enabled():
            return
        extra = ""
        if userData is not None:
            extra = " " + repr(userData)

        self._fd.write("%s %d%s\n" % (statName, statValue, extra))
