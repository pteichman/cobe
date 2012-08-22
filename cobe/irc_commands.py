# Copyright (C) 2012 Peter Teichman

import irc.client
import logging
import re

from cobe.brain import Brain

logger = logging.getLogger(__name__)


class IrcClient(irc.client.SimpleIRCClient):
    def __init__(self, brain, ignored_nicks, only_nicks):
        super(IrcClient, self).__init__()

        self.brain = brain
        self.ignored_nicks = ignored_nicks
        self.only_nicks = only_nicks

        self.channels = set()

    def _delayed_check(self, delay=120):
        self.connection.execute_delayed(delay, self._check_connection)

    def _check_connection(self):
        connection = self.connection

        if connection.is_connected():
            logger.debug("connection: ok")
            self._delayed_check()
            return

        try:
            logger.debug("reconnecting to %s:%p", connection.server,
                         connection.port)
            connection.reconnect()
        except irc.ServerConnectionError:
            logger.info("failed reconnection, rescheduling", exc_info=True)
            self._delayed_check()

    def join(self, channel, key=""):
        self.channels.add((channel, key))

        # Join immediately if already connected. If not, the channel
        # will be joined in the on_endofmotd handler.
        if self.connection.is_connected():
            self.connection.join(channel, key=key)

    def on_endofmotd(self, conn, event):
        # Queue a connection check
        self._delayed_check()

        for channel, key in self.channels:
            self.connection.join(channel, key=key)

    def on_disconnect(self, conn, event):
        self._check_connection()

    def on_pubmsg(self, conn, event):
        user = irc.client.nm_to_n(event.source())

        # ignore specified nicks
        if self.ignored_nicks and user in self.ignored_nicks:
            return

        # only respond on channels
        if not irc.client.is_channel(event.target()):
            return

        msg = event.arguments()[0]

        # strip pasted nicks from messages
        msg = re.sub("<\S+>\s+", "", msg)

        # strip kibot style quotes from messages
        match = re.match("\"(.*)\" --\S+, \d+-\S+\d+.", msg)
        if match:
            msg = match.group(1)

        # look for messages directed to a user
        match = re.match("\s*(\S+)[,:]\s+(.*?)\s*$", msg)

        if match:
            to = match.group(1)
            text = match.group(2)
        else:
            to = None
            text = msg

        # convert message to unicode
        text = text.decode("utf-8").strip()

        if not self.only_nicks or user in self.only_nicks:
            self.brain.train(text)

        if to == self.nick:
            reply = self.brain.reply(text).encode("utf-8")
            conn.privmsg(event.target(), "%s: %s" % (user, reply))


class IrcClientCommand(object):
    @classmethod
    def add_subparser(cls, parser):
        subparser = parser.add_parser("irc-client", help="Run an irc robot")

        subparser.add_argument("-i", "--ignore-nick", action="append",
                               dest="ignored_nicks", help="Ignore a nick.")
        subparser.add_argument("-o", "--only-nick", action="append",
                               dest="only_nicks",
                               help="Only learn from a specific nick.")

        subparser.add_argument("-s", "--server", required=True,
                               help="IRC server hostname")
        subparser.add_argument("-p", "--port", type=int, default=6667,
                               help="IRC server port")
        subparser.add_argument("-n", "--nick", default="cobe",
                               help="IRC nickname")
        subparser.add_argument("-c", "--channel", action="append",
                               help="IRC channel")

        subparser.set_defaults(run=cls.run)

    @staticmethod
    def run(args):
        brain = Brain("cobe.store")

        client = IrcClient(brain, args.ignored_nicks, args.only_nicks)
        client.connect(args.server, args.port, args.nick)

        for channel in args.channel:
            client.join(channel)

        client.start()
