import logging
import os
import re
import readline
import sys

from brain import Brain

from cmdparse import Command

log = logging.getLogger("hal")

class InitCommand(Command):
    def __init__(self):
        Command.__init__(self, "init", summary="Initialize a new brain")

        self.add_option("", "--force", action="store_true") 
        self.add_option("", "--order", type="int", default=5)

    def run(self, options, args):
        filename = "hal.brain"

        if os.path.exists(filename):
            if options.force:
                os.remove(filename)
            else:
                log.error("%s already exists!", filename)
                return

        Brain.init(filename, options.order)

class CloneCommand(Command):
    def __init__(self):
        Command.__init__(self, "clone", summary="Clone a MegaHAL brain")

    def run(self, options, args):
        if len(args) != 1:
            log.error("usage: clone <MegaHAL brain>")
            return

        if os.path.exists("hal.brain"):
            log.error("hal.brain already exists")
            return

        megahal_brain = args[0]

        Brain.init("hal.brain")
        b.clone(megahal_brain)

class LearnCommand(Command):
    def __init__(self):
        Command.__init__(self, "learn", summary="Learn a file of text")

    def run(self, options, args):
        if len(args) != 1:
            log.error("usage: learn <text file>")
            return

        filename = args[0]

        b = Brain("hal.brain")

        fd = open(filename)
        for line in fd.xreadlines():
            b.learn(line.strip())

class LearnIrcLogCommand(Command):
    def __init__(self):
        Command.__init__(self, "learn-irc-log", summary="Learn an irc log")

    def run(self, options, args):
        if len(args) != 1:
            log.error("usage: learn-irc-log <irc log file>")
            return

        filename = args[0]

        b = Brain("hal.brain")

        s = os.stat(filename)
        size_left = s.st_size

        count = 0

        fd = open(filename)
        for line in fd.xreadlines():
            size_left = size_left - len(line)

            count = count + 1
            if (count % 100) == 0:
                complete = 100 * (1. - float(size_left) / float(s.st_size))
                sys.stdout.write("\r%.0f%%" % complete)
                sys.stdout.flush()

            msg = self._parse_irc_message(line.strip())
            if msg:
                b.learn(msg)

        sys.stdout.write("\r100%\n")
        sys.stdout.flush()

    def _parse_irc_message(self, msg):
        # only match lines of the form "HH:MM <nick> message"
        match = re.match("\d+:\d+\s+<\S+>\s+(.*)", msg)
        if not match:
            return None

        msg = match.group(1)

        # strip "username: " at the beginning of messages
        msg = re.sub("^\S+[,:]\s+", "", msg)

        # strip kibot style '"asdf" --user, 06-oct-09' quotes
        msg = re.sub("\"(.*)\" --\S+,\s+\d+-\S+-\d+",
                     lambda m: m.group(1), msg)

        return msg

class ConsoleCommand(Command):
    def __init__(self):
        Command.__init__(self, "console", summary="Speak with Hal.")

    def run(self, options, args):
        b = Brain("hal.brain")

        while True:
            try:
                cmd = raw_input("> ")
            except EOFError:
                print
                sys.exit(0)

            b.learn(cmd)
            print b.reply(cmd).capitalize()
