import logging
import os

import brain

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

        b = brain.Brain(filename)
        b.init(order)

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

        b = brain.Brain("hal.brain")
        b.init()
        b.clone(megahal_brain)

