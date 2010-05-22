import argparse
import logging
import sys

from . import commands
from . import instatrace

parser = argparse.ArgumentParser(description="Cobe control")
parser.add_argument("-b", "--brain", default="cobe.brain")
parser.add_argument("--debug", action="store_true", help=argparse.SUPPRESS)
parser.add_argument("--instatrace", metavar="FILE",
                    help="log performance statistics to FILE")

subparsers = parser.add_subparsers(title="Commands")
commands.ConsoleCommand.add_subparser(subparsers)
commands.InitCommand.add_subparser(subparsers)
commands.IrcClientCommand.add_subparser(subparsers)
commands.LearnCommand.add_subparser(subparsers)
commands.LearnIrcLogCommand.add_subparser(subparsers)

def main():
    args = parser.parse_args()

    formatter = logging.Formatter("%(levelname)s: %(message)s")
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logging.root.addHandler(console)

    if args.debug:
        logging.root.setLevel(logging.DEBUG)
    else:
        logging.root.setLevel(logging.INFO)

    if args.instatrace:
        instatrace.Instatrace().init(args.instatrace)

    try:
        args.run(args)
    except KeyboardInterrupt:
        print
        sys.exit(1)

if __name__ == "__main__":
    main()
