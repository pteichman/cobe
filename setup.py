#!/usr/bin/env python

# Require setuptools. See http://pypi.python.org/pypi/setuptools for
# installation instructions, or run the ez_setup script found at
# http://peak.telecommunity.com/dist/ez_setup.py
from setuptools import setup, find_packages

setup(
    name = "cobe",
    version = "3.0.0",
    author = "Peter Teichman",
    author_email = "peter@teichman.org",
    url = "https://github.com/pteichman/cobe/wiki",
    description = "Markov chain based text generator library and chatbot",
    packages = ["cobe"],
    test_suite = "tests",

    install_requires = [
        "Cython==0.29.17",
        "PyStemmer==2.0.0.1",
        "irc==18.0.0"
        ],

    classifiers = [
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Topic :: Scientific/Engineering :: Artificial Intelligence"
        ],

    entry_points = {
        "console_scripts" : [
            "cobe = cobe.control:main"
        ]
    }
)
