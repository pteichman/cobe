# Copyright (C) 2011 Peter Teichman

from flask import Flask
app = Flask(__name__)

@app.route("/")
def hello():
    return "Hello World!"
