# Copyright (C) 2012 Peter Teichman

import hashlib

def md5(data):
    return hashlib.md5(data).hexdigest()
