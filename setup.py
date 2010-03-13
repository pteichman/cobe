#!/usr/bin/env python

from ez_setup import use_setuptools
use_setuptools()

from setuptools import setup, find_packages
setup(
    name = "cobe",
    version = "0.5",
    author = "Peter Teichman",
    author_email = "peter@teichman.org",
    packages = ["cobe"],
    test_suite = "tests.cobe_suite",
    classifiers = [
        "Development Status :: 4 - Beta",
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
            "cobe-control = cobe.control:main"
        ]
    }
)
