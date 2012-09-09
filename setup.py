#!/usr/bin/env python

# Require setuptools. See http://pypi.python.org/pypi/setuptools for
# installation instructions, or run the ez_setup script found at
# http://peak.telecommunity.com/dist/ez_setup.py
from setuptools import setup


setup(
    name="cobe",
    version="2.0.4",
    author="Peter Teichman",
    author_email="peter@teichman.org",
    url="http://wiki.github.com/pteichman/cobe/",
    description="Markov chain based text generator library and chatbot",
    packages=["cobe"],

    # setup_require nosetests, so that the nosetests command is
    # available immediately in a fresh checkout
    setup_requires=[
        "nose==1.1.2"
    ],

    test_suite="unittest2.collector",

    # mock and unittest2 are required by the tests; coverage is
    # required by the [nosetests] section of setup.cfg.
    tests_require=[
        "coverage==3.5.2",
        "mock==1.0b1",
        "unittest2==0.5.1"
    ],

    install_requires=[
        "PyStemmer==1.2.0",
        "argparse==1.2.1",
        "irc==3.0",
        "park==1.0"
    ],

    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Scientific/Engineering :: Artificial Intelligence"
    ],

    entry_points={
        "console_scripts": [
            "cobe = cobe.control:main"
        ]
    }
)
