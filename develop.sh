#!/bin/bash

# This script creates a new virtualenv and installs the current module
# there for development use. It requires virtualenv:
# http://pypi.python.org/pypi/virtualenv

VIRTUALENV_DIR=virtualenv

if ! virtualenv --no-site-packages $VIRTUALENV_DIR; then
    echo -e "virtualenv creation failed"
    exit 1
fi

oldenv=$VIRTUAL_ENV

# install links to this module in the new virtualenv
. $VIRTUALENV_DIR/bin/activate
python setup.py develop

if [ -z "$oldenv" ]; then
    echo
    echo "Run \"source $VIRTUALENV_DIR/bin/activate\" to activate this virtualenv."
fi
