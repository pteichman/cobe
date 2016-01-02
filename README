COBE stands for Code of Business Ethics. Cobe is a conversation
simulator, originally a database backed port of MegaHAL but a bit
more now.

According to the Nobel Prize committee, "the COBE project can also
be regarded as the starting point for cosmology as a precision
science."

There are a few relevant posts here:
http://teichman.org/blog/2011/09/cobe-2.0.html
http://teichman.org/blog/2011/05/singularity.html
http://teichman.org/blog/2011/02/cobe.html

You can read its release history here:
https://github.com/pteichman/cobe/wiki

Cobe has been inspired by the success of Hailo:
http://blogs.perl.org/users/aevar_arnfjor_bjarmason/2010/01/hailo-a-perl-rewrite-of-megahal.html

Our goals are similar to Hailo: an on-disk data store for lower memory
usage, better support for Unicode, and general stability.

You can read about the original MegaHAL here:
http://megahal.alioth.debian.org/How.html

In short, it uses Markov modeling to generate text responses after
learning from input text.

Cobe creates a directed graph of word n-grams (default n=3) from the
text it learns. When generating a response, it performs random walks
on this graph to create as many candidate replies as it can in half a
second.

As the candidate responses are created, they're run through a scoring
algorithm that identifies which is the best of the group. After the
half second is over, the best candidate is returned as the response.

Cobe installs a command line tool (called cobe) for interacting with a
brain database, though it is also intended to be used as a Python
api. See the documentation in the cobe.brain module for details.

To install from a tarball:

  $ python setup.py install

Or from the Python Package Index:

  $ easy_install pip
  # pip install cobe

Usage:

  $ cobe init
  $ cobe learn <text file>
  $ cobe console
