# Copyright (C) 2012 Peter Teichman

import sqlite3

from flask import Flask, g
from flaskext.sqlalchemy import SQLAlchemy

from .base import base
from .filters import md5, natural_datetime

app = Flask(__name__)


@app.before_request
def before_request():
    conn = sqlite3.connect(app.config["CORPUS"],
                           detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row

    g.db = conn


@app.teardown_request
def teardown_request(exception):
    if hasattr(g, 'db'):
        g.db.close()


def register_filters(app):
    app.jinja_env.filters["md5"] = md5
    app.jinja_env.filters["natural_datetime"] = natural_datetime


def create_app():
    app.config.from_object("cobe.web.settings")

    app.register_blueprint(base)
    register_filters(app)

    return app
