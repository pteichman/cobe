#!/usr/bin/env python

import sys

# Require setuptools. See http://pypi.python.org/pypi/setuptools for
# installation instructions, or run the ez_setup script found at
# http://peak.telecommunity.com/dist/ez_setup.py
from setuptools import setup, find_packages, Command


class CheckCommand(Command):
    description = "Run tests."
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import subprocess

        print "Running pep8..."
        if subprocess.call(["pep8", "cobe", "tests"]):
            sys.exit("ERROR: failed pep8 checks")

        print "Running pyflakes..."
        if subprocess.call(["pyflakes", "cobe", "tests"]):
            sys.exit("ERROR: failed pyflakes checks")

        print "Running tests..."
        if subprocess.call(["coverage", "run", "--source=cobe,tests",
                            "./setup.py", "test"]):
            sys.exit("ERROR: failed unit tests")

        subprocess.call(['coverage', 'report', '-m'])


setup(
    name = "cobe",
    version = "2.0.4",
    author = "Peter Teichman",
    author_email = "peter@teichman.org",
    url = "http://wiki.github.com/pteichman/cobe/",
    description = "Markov chain based text generator library and chatbot",
    packages = ["cobe"],
    test_suite = "unittest2.collector",

    install_requires = [
        "PyStemmer==1.2.0",
        "argparse==1.2.1",
        "park==1.0",
        "python-irclib==0.4.8"
        ],

    # The PyPI entry for python-irclib points at a SourceForge files
    # page. These no longer work with pip's url discovery, as they
    # append the string "/download" to each filename. I have uploaded
    # python-irclib 0.4.8's zip file from SourceForge (unmodified) to
    # the page below so that "pip install cobe" will work.
    dependency_links = [
        "http://github.com/pteichman/python-irclib/downloads"
        ],

    classifiers = [
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Scientific/Engineering :: Artificial Intelligence"
        ],

    cmdclass = {
        "check": CheckCommand
        },

    entry_points = {
        "console_scripts" : [
            "cobe = cobe.control:main"
        ]
    }
)
