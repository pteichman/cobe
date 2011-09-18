#!/usr/bin/env python

# Require setuptools. See http://pypi.python.org/pypi/setuptools for
# installation instructions, or run the ez_setup script found at
# http://peak.telecommunity.com/dist/ez_setup.py
from setuptools import setup, find_packages

setup(
    name = "cobe",
    version = "2.0.0",
    author = "Peter Teichman",
    author_email = "peter@teichman.org",
    url = "http://wiki.github.com/pteichman/cobe/",
    description = "Markov chain based text generator library and chatbot",
    packages = ["cobe"],
    test_suite = "tests",

    setup_requires = [
        "nose==1.1.2",
        "coverage==3.5"
        ],

    install_requires = [
        "PyStemmer==1.2.0",
        "argparse==1.2.1",
        "python-irclib==0.4.6"
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

    entry_points = {
        "console_scripts" : [
            "cobe = cobe.control:main"
        ]
    }
)
