# Copyright (C) 2010 Peter Teichman

import logging
import os
import re
import readline
import sys
import time

from brain import Brain

from cmdparse import Command

log = logging.getLogger("cobe")

def check_for_brain_file(filename):
    if not os.path.exists(filename):
        print "ERROR: %s file not found. Run init?" % filename
        return False
    return True

class InitCommand(Command):
    def __init__(self):
        Command.__init__(self, "init", summary="Initialize a new brain")

        self.add_option("", "--force", action="store_true")
        self.add_option("", "--order", type="int", default=5)

    def run(self, options, args):
        filename = options.brain

        if os.path.exists(filename):
            if options.force:
                os.remove(filename)
            else:
                log.error("%s already exists!", filename)
                return

        Brain.init(filename, options.order)

def progress_generator(filename):
    s = os.stat(filename)
    size_left = s.st_size

    fd = open(filename)
    for line in fd.xreadlines():
        size_left = size_left - len(line)
        progress = 100 * (1. - (float(size_left) / float(s.st_size)))

        yield line, progress

    fd.close()

class LearnCommand(Command):
    def __init__(self):
        Command.__init__(self, "learn", summary="Learn a file of text")

    def run(self, options, args):
        if len(args) == 0:
            log.error("usage: learn <text file>")
            return

        if not check_for_brain_file(options.brain):
            return 1

        b = Brain(options.brain)

        for filename in args:
            now = time.time()
            print filename

            b.start_batch_learning()

            count = 0
            for line, progress in progress_generator(filename):
                show_progress = ((count % 100) == 0)

                if show_progress:
                    elapsed = time.time() - now
                    sys.stdout.write("\r%.0f%% (%d/s)" % (progress,
                                                          count/elapsed))
                    sys.stdout.flush()

                b.learn(line.strip())
                count = count + 1

            b.stop_batch_learning()
            elapsed = time.time() - now
            print "\r100%% (%d/s)" % (count/elapsed)

class LearnIrcLogCommand(Command):
    def __init__(self):
        Command.__init__(self, "learn-irc-log", summary="Learn an irc log")
        self.add_option("-i", "--ignore-nick",
                        action="append", dest="ignored_nicks",
                        help="Ignore an IRC nick (can be specified multiple times)")

    def run(self, options, args):
        if len(args) == 0:
            log.error("usage: learn-irc-log <irc log file>")
            return

        if not check_for_brain_file(options.brain):
            return 1

        b = Brain(options.brain)

        for filename in args:
            now = time.time()
            print filename

            b.start_batch_learning()

            count = 0
            for line, progress in progress_generator(filename):
                show_progress = ((count % 100) == 0)

                if show_progress:
                    elapsed = time.time() - now
                    sys.stdout.write("\r%.0f%% (%d/s)" % (progress,
                                                          count/elapsed))
                    sys.stdout.flush()

                msg = self._parse_irc_message(line.strip(),
                                              options.ignored_nicks)
                if msg:
                    b.learn(msg)
                    count = count + 1

            b.stop_batch_learning()
            elapsed = time.time() - now
            print "\r100%% (%d/s)" % (count/elapsed)

    def _parse_irc_message(self, msg, ignored_nicks=None):
        # only match lines of the form "HH:MM <nick> message"
        match = re.match("\d+:\d+\s+<(.+?)>\s+(.*)", msg)
        if not match:
            return None

        nick = match.group(1)
        msg = match.group(2)

        if ignored_nicks is not None and nick in ignored_nicks:
            return None

        # strip "username: " at the beginning of messages
        msg = re.sub("^\S+[,:]\s+", "", msg)

        # strip kibot style '"asdf" --user, 06-oct-09' quotes
        msg = re.sub("\"(.*)\" --\S+,\s+\d+-\S+-\d+",
                     lambda m: m.group(1), msg)

        return msg

class ConsoleCommand(Command):
    def __init__(self):
        Command.__init__(self, "console", summary="Interactive console")

    def run(self, options, args):
        if not check_for_brain_file(options.brain):
            return 1

        b = Brain(options.brain)

        while True:
            try:
                cmd = raw_input("> ")
            except EOFError:
                print
                sys.exit(0)

            b.learn(cmd)
            print b.reply(cmd).capitalize().encode("utf-8")
