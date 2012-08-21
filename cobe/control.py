# Copyright (C) 2012 Peter Teichman

import argparse
import codecs
import logging
import sys

from . import commands


def get_parser():
    def add_module(parsers, submodule):
        for name in dir(submodule):
            obj = getattr(submodule, name)
            if hasattr(obj, "add_subparser"):
                obj.add_subparser(parsers)

    parser = argparse.ArgumentParser(description="Cobe control")
    parser.add_argument("--debug", action="store_true", help=argparse.SUPPRESS)
    cmd_parsers = parser.add_subparsers()

    add_module(cmd_parsers, commands)

    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()

    formatter = logging.Formatter("%(levelname)s: %(message)s")
    console = logging.StreamHandler(codecs.getwriter('utf8')(sys.stderr))
    console.setFormatter(formatter)
    logging.root.addHandler(console)

    if args.debug:
        logging.root.setLevel(logging.DEBUG)
    else:
        logging.root.setLevel(logging.INFO)

    try:
        args.run(args)
    except KeyboardInterrupt:
        print
        sys.exit(1)

if __name__ == "__main__":
    main()
