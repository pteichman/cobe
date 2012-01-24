# Copyright (C) 2012 Peter Teichman

from functools import wraps
from flask import flash, g, session, request, redirect


def get_user():
    if "email" in session:
        user = g.db.execute("SELECT * FROM voters WHERE email = ?",
                            (session["email"],)).fetchone()
        if not user:
            flash("Removing unknown user from session: %s" % session["email"])
            del session["email"]

        return user


def require_session(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_user()
        if not user:
            return redirect("/")

        return f(*args, **kwargs)
    return decorated
