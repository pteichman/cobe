import unittest

from cobe.commands import LearnIrcLogCommand


class TestIrcLogParsing(unittest.TestCase):
    def setUp(self):
        self.command = LearnIrcLogCommand()

    def test_non_pubmsg(self):
        msg = "this is some non-pubmsg text found in a log"
        cmd = self.command

        self.assertEqual(None, cmd._parse_irc_message(msg))

    def test_normal_pubmsg(self):
        msg = "12:00 <foo> bar baz"
        cmd = self.command

        self.assertEqual("bar baz", cmd._parse_irc_message(msg))

    def test_pubmsg_to_cobe(self):
        msg = "12:00 <foo> cobe: bar baz"
        cmd = self.command

        self.assertEqual("bar baz", cmd._parse_irc_message(msg))

    def test_normal_pubmsg_with_wpaces(self):
        msg = "12:00 < foo> bar baz"
        cmd = self.command

        self.assertEqual("bar baz", cmd._parse_irc_message(msg))

    def test_kibot_quote_pubmsg(self):
        msg = "12:00 <foo> \"bar baz\" --user, 01-oct-09"
        cmd = self.command

        self.assertEqual("bar baz", cmd._parse_irc_message(msg))

    def test_ignored_nick_pubmsg(self):
        msg = "12:00 <foo> bar baz"
        cmd = self.command

        self.assertEqual(None, cmd._parse_irc_message(msg, ["foo"]))
