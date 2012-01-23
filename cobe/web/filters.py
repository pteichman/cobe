# Copyright (C) 2012 Peter Teichman

import datetime
import hashlib

def md5(data):
    return hashlib.md5(data).hexdigest()

def natural_datetime(when):
    diff = datetime.datetime.utcnow() - when

    s = diff.seconds
    if diff.days > 7 or diff.days < 0:
        return when.strftime("%d %B")
    elif diff.days == 1:
        return "1 day ago"
    elif diff.days > 1:
        return "%d days ago" % diff.days
    elif s <= 1:
        return "just now"
    elif s < 60:
        return "%d seconds ago" % s
    elif s < 120:
        return "1 minute ago"
    elif s < 3600:
        return "%d minutes ago" % (s / 60)
    elif s < 7200:
        return "1 hour ago"
    else:
        return "%d hours ago" % (s / 3600)
