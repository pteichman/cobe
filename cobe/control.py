import argparse
import codecs
import logging
import sys

from . import commands

parser = argparse.ArgumentParser(description="Cobe control")
parser.add_argument("--debug", action="store_true", help=argparse.SUPPRESS)

subparsers = parser.add_subparsers(title="Commands")
commands.ConsoleCommand.add_subparser(subparsers)
commands.DumpCommand.add_subparser(subparsers)
commands.LearnCommand.add_subparser(subparsers)


def main():
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
