# Copyright (C) 2012 Peter Teichman

import mock
import unittest2 as unittest

from cobe import irc_commands


@mock.patch("irc.client.Connection", nickname="cobe")
class TestIrcClient(unittest.TestCase):
    def pubmsg_event(self, message):
        event = mock.Mock()

        event.eventtype.return_value = "pubmsg"
        event.source.return_value = "speaker!user@example.org"
        event.target.return_value = "#channel"
        event.arguments.return_value = [message]

        return event

    def setUp(self):
        self.brain = mock.Mock()

    def test_not_channel(self, mock_conn):
        client = irc_commands.IrcClient(self.brain)

        # ensure a message that isn't on a channel is ignored
        event = self.pubmsg_event("test message")
        event.target.return_value = "not_channel"

        client.on_pubmsg(mock_conn, event)
        self.assertFalse(self.brain.train.called)
        self.assertFalse(self.brain.reply.called)

    def test_train_on_pubmsg(self, mock_conn):
        client = irc_commands.IrcClient(self.brain)

        # make sure an untargeted message is learned but not replied
        client.on_pubmsg(mock_conn, self.pubmsg_event("test message"))
        self.brain.train.assert_called_once_with("test message")
        self.assertFalse(self.brain.reply.called)

        self.brain.reset_mock()

        # and the same with a targeted message that isn't to this bot
        client.on_pubmsg(mock_conn, self.pubmsg_event("user: test message2"))
        self.brain.train.assert_called_once_with("test message2")
        self.assertFalse(self.brain.reply.called)

    def test_reply_on_pubmsg(self, mock_conn):
        client = irc_commands.IrcClient(self.brain)

        # make sure a targeted message is trained properly
        client.on_pubmsg(mock_conn, self.pubmsg_event("cobe: test message"))
        self.brain.train.assert_called_once_with("test message")
        self.brain.reply.assert_called_once_with("test message")

    def test_ignored_nicks(self, mock_conn):
        client = irc_commands.IrcClient(self.brain, ignored_nicks=["ignored"])

        client.on_pubmsg(mock_conn, self.pubmsg_event("cobe: test message"))
        self.brain.train.assert_called_once_with("test message")
        self.brain.reply.assert_called_once_with("test message")

        self.brain.reset_mock()

        # create an ignored message event
        event = self.pubmsg_event("test message")
        event.source.return_value = "ignored!user@example.org"

        client.on_pubmsg(mock_conn, event)
        self.assertFalse(self.brain.train.called)
        self.assertFalse(self.brain.reply.called)

    def test_only_nicks(self, mock_conn):
        client = irc_commands.IrcClient(self.brain, only_nicks=["speaker"])

        client.on_pubmsg(mock_conn, self.pubmsg_event("cobe: test message"))
        self.brain.train.assert_called_once_with("test message")
        self.brain.reply.assert_called_once_with("test message")

        self.brain.reset_mock()

        # create an ignored message event
        event = self.pubmsg_event("test message")
        event.source.return_value = "ignored!user@example.org"

        client.on_pubmsg(mock_conn, event)
        self.assertFalse(self.brain.train.called)
        self.assertFalse(self.brain.reply.called)
