# Copyright (C) 2012 Peter Teichman

from flask import Flask
app = Flask(__name__)

from .base import base

def create_app(brain):
    app.config.from_object("cobe.web.settings")
    app.config["brain"] = brain

    app.register_blueprint(base)

    return app
