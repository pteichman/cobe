# Copyright (C) 2010 Peter Teichman

import irclib
import logging
import re

log = logging.getLogger("cobe.irc")


class Bot(irclib.SimpleIRCClient):
    def __init__(self, brain, nick, channel, ignored_nicks, only_nicks):
        irclib.SimpleIRCClient.__init__(self)

        self.brain = brain
        self.nick = nick
        self.channel = channel
        self.ignored_nicks = ignored_nicks
        self.only_nicks = only_nicks

    def _dispatcher(self, c, e):
        log.debug("on_%s %s", e.eventtype(), (e.source(), e.target(),
                                              e.arguments()))
        irclib.SimpleIRCClient._dispatcher(self, c, e)

    def on_endofmotd(self, conn, event):
        self.connection.join(self.channel)

    def on_pubmsg(self, conn, event):
        user = irclib.nm_to_n(event.source())

        # ignore specified nicks
        if self.ignored_nicks and user in self.ignored_nicks:
            return

        # only respond on channels
        if not irclib.is_channel(event.target()):
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
        text = text.decode("utf-8")

        if not self.only_nicks or user in self.only_nicks:
            self.brain.learn(text)

        if to == self.nick:
            reply = self.brain.reply(text).encode("utf-8")
            conn.privmsg(event.target(), "%s: %s" % (user, reply))


class Runner:
    def run(self, brain, args):
        bot = Bot(brain, args.nick, args.channel, args.ignored_nicks,
                  args.only_nicks)
        bot.connect(args.server, args.port, args.nick)
        log.info("connected to %s:%s", args.server, args.port)

        bot.start()
