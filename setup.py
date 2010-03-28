#!/usr/bin/env python

from ez_setup import use_setuptools
use_setuptools()

from setuptools import setup, find_packages
setup(
    name = "cobe",
    version = "1.0.1",
    author = "Peter Teichman",
    author_email = "peter@teichman.org",
    url = "http://wiki.github.com/pteichman/cobe/",
    description = "A conversation simulator similar to MegaHAL",
    packages = ["cobe"],
    test_suite = "tests.cobe_suite",
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
