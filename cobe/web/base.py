# Copyright (C) 2012 Peter Teichman

import hashlib
import httplib
import json
import requests
import urllib2

from flask import Blueprint, g, jsonify, redirect, request, render_template, \
    session, url_for

from .auth import get_user, require_session
from .model import Exchange

base = Blueprint("base", __name__)


@base.route("/")
def index():
    user = get_user()

    return render_template("base.html", user=user)


@base.route("/recent/")
@base.route("/recent/<int:page>/")
@require_session
def recent(page=1):
    user = get_user()

    return render_template("vote.html", user=user,
                           items=url_for(".recent_json"))


@base.route("/recent/json/")
@require_session
def recent_json(page=1):
    user = get_user()

    exchanges = []
    for e in Exchange.get_recent_unrated(user):
        exchanges.append(dict(hash=e["hash"], input=e["input"],
                              output=e["output"]))

    return jsonify(dict(exchanges=exchanges))


@base.route("/id/login", methods=["POST"])
def login():
    payload = dict(assertion=request.form["assertion"],
                   audience=url_for(".index", _external=True))

    r = requests.post("https://browserid.org/verify", verify=True,
                      data=payload)

    if not r.ok:
        return jsonify(
            error="error response from browserid: %d" % r.status_code)

    ct = r.headers["content-type"]
    if not ct.startswith("application/json"):
        return jsonify(
            error="non-JSON response from browserid: %s" % ct)

    data = json.loads(r.content)

    # handle failures from browserid
    if data.get("status") == "failure":
        return jsonify(error=data["reason"])

    # check our own users
    if data.get("status") != "okay":
        return jsonify(
            error="unknown status from browserid: %s" % data["status"])

    email = data["email"].strip()
    session["email"] = email

    digest = hashlib.md5(email.lower()).hexdigest()
    picture = "http://www.gravatar.com/avatar/%s?s=24" % digest

    # validate, login to the session
    return jsonify(email=email, picture=picture)


@base.route("/id/logout")
def logout():
    session.clear()

    return redirect(url_for("base.index"))
