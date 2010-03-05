import logging
import os

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
