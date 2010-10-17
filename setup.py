#!/usr/bin/env python

# Require setuptools. See http://pypi.python.org/pypi/setuptools for
# installation instructions, or run the ez_setup script found at
# http://peak.telecommunity.com/dist/ez_setup.py
from setuptools import setup, find_packages

setup(
    name = "cobe",
    version = "1.1.2",
    author = "Peter Teichman",
    author_email = "peter@teichman.org",
    url = "http://wiki.github.com/pteichman/cobe/",
    description = "A conversation simulator similar to MegaHAL",
    packages = ["cobe"],
    test_suite = "tests",
    install_requires = ["argparse>=1.1"],
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
