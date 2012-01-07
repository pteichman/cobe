# Copyright (C) 2012 Peter Teichman

import datetime
import irclib
import logging
import re
import time

log = logging.getLogger("cobe.irc")


class Bot(irclib.SimpleIRCClient):
    def __init__(self, brain, nick, channel, log_channel, ignored_nicks,
                 only_nicks):
        irclib.SimpleIRCClient.__init__(self)

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
        log.debug("on_%s %s", e.eventtype(), (e.source(), e.target(),
                                              e.arguments()))
        irclib.SimpleIRCClient._dispatcher(self, c, e)

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
        except irclib.ServerConnectionError:
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
        user = irclib.nm_to_n(event.source())

        if event.target() == self.log_channel:
            # ignore input in the log channel
            return

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
        text = text.decode("utf-8").strip()

        if not self.only_nicks or user in self.only_nicks:
            self.brain.learn(text)

        if to == self.nick:
            reply = self.brain.reply(text).encode("utf-8")
            conn.privmsg(event.target(), "%s: %s" % (user, reply))


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


class IrssiLogFile(object):
    def __init__(self, fd):
        self._fd = fd
        self._now = datetime.datetime.now()

    def set_now(self, date):
        self._now = datetime.datetime.strptime(date, "%a %b %d %H:%M:%S %Y")

    def update_time(self, time_str):
        t = time.strptime(time_str, "%H:%M")
        self._now = self._now.replace(hour=t.tm_hour, minute=t.tm_min,
                                      second=0)

    def update_date(self, date_str):
        self._now = datetime.datetime.strptime(date_str, "%a %b %d %Y")

    def items(self):
        for line in self._fd:
            line = line.strip()

            # handle some special lines
            m = re.match("^--- Log opened (.*)", line)
            if m:
                self.set_now(m.group(1))
                continue

            m = re.match("^--- Day changed (.*)", line)
            if m:
                self.update_date(m.group(1))
                continue

            m = re.match("^--- Log closed (.*)", line)
            if m:
                # do nothing
                continue

            # parse the current time, update self._now
            m = re.match("^(\d\d:\d\d) (.*)", line)
            if not m:
                logging.info("Unrecogized line format: %s", line)
                continue

            self.update_time(m.group(1))

            msg = m.group(2)
            if msg.startswith("-!-"):
                # skip join/part info
                continue

            msg = unicode(msg.strip(), "utf-8", errors="replace")

            # detect speaker
            speaker = None

            m = re.search("^<(.*?)>(.*)", msg)
            if m:
                speaker = m.group(1).strip().lower()
                msg = m.group(2).strip()
            elif re.search("^\* (\S+)", msg):
                # skip actions
                continue

            if msg.startswith("!") or msg.startswith("-"):
                # server message
                continue

            if speaker is None:
                raise Exception(msg)

            yield (self._now, unicode(speaker), msg)
