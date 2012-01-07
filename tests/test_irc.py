# Copyright (C) 2012 Peter Teichman

import os
import unittest

from cStringIO import StringIO

from cobe.irc import IrssiLogFile


class testInit(unittest.TestCase):
    def testNonPubmsg(self):
        msg = "this is some non-pubmsg text found in a log\n"
        items = list(IrssiLogFile(StringIO(msg)).items())

        self.assertEqual(0, len(items))

    def testNormalPubmsg(self):
        msg = "12:00 <foo> bar baz"
        item = IrssiLogFile(StringIO(msg)).items().next()

        self.assertEqual("foo", item[1])
        self.assertEqual("bar baz", item[2])

    def testNormalPubmsgWithSpaces(self):
        msg = "12:00 < foo> bar baz"
        item = IrssiLogFile(StringIO(msg)).items().next()

        self.assertEqual("foo", item[1])
        self.assertEqual("bar baz", item[2])


if __name__ == '__main__':
    unittest.main()
