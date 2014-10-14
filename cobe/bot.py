# Copyright (C) 2014 Peter Teichman

import irc.client
import logging
import re

log = logging.getLogger("cobe.bot")


class Bot(irc.client.SimpleIRCClient):
    def __init__(self, brain, nick, channel, log_channel, ignored_nicks,
                 only_nicks):
        irc.client.SimpleIRCClient.__init__(self)

        # Fall back to latin-1 if invalid utf-8 is provided.
        irc.client.ServerConnection.buffer_class = irc.buffer.LenientDecodingLineBuffer

        self.brain = brain
        self.nick = nick
        self.channel = channel
        self.log_channel = log_channel
        self.ignored_nicks = ignored_nicks
        self.only_nicks = only_nicks

        if log_channel is not None:
            # set up a new logger
            handler = IrcLogHandler(self.connection, log_channel)
            handler.setLevel(logging.DEBUG)

            logging.root.addHandler(handler)

    def _dispatcher(self, c, e):
        log.debug("on_%s %s", e.type, (e.source, e.target, e.arguments))
        irc.client.SimpleIRCClient._dispatcher(self, c, e)

    def _delayed_check(self, delay=120):
        self.connection.execute_delayed(delay, self._check_connection)

    def _check_connection(self):
        conn = self.connection
        if conn.is_connected():
            log.debug("connection: ok")
            self._delayed_check()
            return

        try:
            log.debug("reconnecting to %s:%p", conn.server, conn.port)
            conn.connect(conn.server, conn.port, conn.nickname, conn.password,
                         conn.username, conn.ircname, conn.localaddress,
                         conn.localport)
        except irc.client.ServerConnectionError:
            log.info("failed reconnection, rescheduling", exc_info=True)
            self._delayed_check()

    def on_disconnect(self, conn, event):
        self._check_connection()

    def on_endofmotd(self, conn, event):
        self._delayed_check()
        self.connection.join(self.channel)

        if self.log_channel:
            self.connection.join(self.log_channel)

    def on_pubmsg(self, conn, event):
        user = irc.client.NickMask(event.source).nick

        if event.target == self.log_channel:
            # ignore input in the log channel
            return

        # ignore specified nicks
        if self.ignored_nicks and user in self.ignored_nicks:
            return

        # only respond on channels
        if not irc.client.is_channel(event.target):
            return

        msg = event.arguments[0].strip()

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

        if not self.only_nicks or user in self.only_nicks:
            self.brain.learn(text)

        if to == conn.nickname:
            reply = self.brain.reply(text)
            conn.privmsg(event.target, "%s: %s" % (user, reply))


class Runner:
    def run(self, brain, args):
        bot = Bot(brain, args.nick, args.channel, args.log_channel,
                  args.ignored_nicks, args.only_nicks)
        bot.connect(args.server, args.port, args.nick)
        log.info("connected to %s:%s", args.server, args.port)

        bot.start()


class IrcLogHandler(logging.Handler):
    def __init__(self, connection, channel):
        logging.Handler.__init__(self)

        self.connection = connection
        self.channel = channel

    def emit(self, record):
        conn = self.connection

        if conn.is_connected():
            conn.privmsg(self.channel, record.getMessage().encode("utf-8"))
