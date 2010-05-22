# Copyright (C) 2010 Peter Teichman

import re
import sys
import time

from twisted.words.protocols import irc
from twisted.internet import reactor, protocol
from twisted.python import log

class CobeBot(irc.IRCClient):
    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        log.msg("[connected]")
        self.setNick(self.factory.nickname)

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)
        log.msg("[disconnected]")

    def signedOn(self):
        """Called when bot has succesfully signed on to server."""
        self.join(self.factory.channel)

    def joined(self, channel):
        """This will get called when the bot joins the channel."""
        log.msg("[joined %s]" % channel)

    def privmsg(self, user, channel, msg):
        """This will get called when the bot receives a message."""
        user = user.split('!', 1)[0]

        # only respond on channels
        if not channel.startswith("#"):
            return

        # strip pasted nicks from messages
        msg = re.sub("<\S+>", "", msg)

        # strip kibot style quotes from messages
        match = re.match("\"(.*)\" --\S+, \d+-\S+\d+.", msg)
        if match:
            msg = match.group(1)

        # look for messages directed to a user
        match = re.match("\s*(\S+)\s*[,:]\s*(.*?)\s*$", msg)

        if match:
            to = match.group(1)
            text = match.group(2)
        else:
            to = None
            text = msg

        # convert message to unicode
        text = text.decode("utf-8")
        self.factory.brain.learn(text)

        if to == self.nickname:
            reply = self.factory.brain.reply(text).encode("utf-8")
            self.say(channel, "%s: %s" % (user, reply))

    def nickChanged(self, nick):
        log.msg("nick changed to %s", nick)
        self.nickname = nick

class CobeBotFactory(protocol.ClientFactory):
    # the class of the protocol to build when new connection is made
    protocol = CobeBot

    def __init__(self, brain, channel, nickname):
        self.brain = brain
        self.channel = channel
        self.nickname = nickname

    def clientConnectionLost(self, connector, reason):
        """If we get disconnected, reconnect to server."""
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print "connection failed:", reason
        reactor.stop()

class Runner:
    def run(self, brain, args):
        log.startLogging(sys.stdout)
        f = CobeBotFactory(brain, args.channel, args.nick)

        reactor.connectTCP(args.server, args.port, f)
        reactor.run()
