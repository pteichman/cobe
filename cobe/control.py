import cmdparse
import commands
import logging
import optparse
import sys

parser = cmdparse.CommandParser()
parser.add_option("-b", "--brain", type="string", default="cobe.brain",
                  help="Specify an alternate brain file")
parser.add_option("", "--debug", action="store_true",
                  help=optparse.SUPPRESS_HELP)

parser.add_command(commands.InitCommand(), "Control")
parser.add_command(commands.ConsoleCommand(), "Control")
parser.add_command(commands.LearnCommand(), "Learning")
parser.add_command(commands.LearnIrcLogCommand(), "Learning")

def main():
    (command, options, args) = parser.parse_args()

    formatter = logging.Formatter("%(levelname)s: %(message)s")
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logging.root.addHandler(console)

    if options.debug:
        logging.root.setLevel(logging.DEBUG)
    else:
        logging.root.setLevel(logging.INFO)

    if command is None:
        parser.print_help()
        sys.exit(1)

    try:
        command.run(options, args)
    except KeyboardInterrupt:
        print
        sys.exit(1)

if __name__ == "__main__":
    main()
