import unittest

from cobe.commands import LearnIrcLogCommand

class testIrcLogParsing(unittest.TestCase):
    def setUp(self):
        self.command = LearnIrcLogCommand()

    def testNonPubmsg(self):
        msg = "this is some non-pubmsg text found in a log"
        cmd = self.command

        self.assertEqual(None, cmd._parse_irc_message(msg))

    def testNormalPubmsg(self):
        msg = "12:00 <foo> bar baz"
        cmd = self.command

        self.assertEqual("bar baz", cmd._parse_irc_message(msg)[1])

    def testPubmsgToCobe(self):
        msg = "12:00 <foo> cobe: bar baz"
        cmd = self.command

        self.assertEqual(("cobe", "bar baz"), cmd._parse_irc_message(msg))

    def testNormalPubmsgWithSpaces(self):
        msg = "12:00 < foo> bar baz"
        cmd = self.command

        self.assertEqual("bar baz", cmd._parse_irc_message(msg)[1])

    def testKibotQuotePubmsg(self):
        msg = "12:00 <foo> \"bar baz\" --user, 01-oct-09"
        cmd = self.command

        self.assertEqual("bar baz", cmd._parse_irc_message(msg)[1])

    def testIgnoredNickPubmsg(self):
        msg = "12:00 <foo> bar baz"
        cmd = self.command

        self.assertEqual(None, cmd._parse_irc_message(msg, ["foo"]))

if __name__ == '__main__':
    unittest.main()
