import os, sys

from flask import Flask, render_template, jsonify, url_for

from .index import db, dbtables, app, cors
from .service.audio_service import AudioService

AudioService.init(db, dbtables)

from .dao.user import UserDao

from .endpoints import user
from .endpoints import message
from .endpoints import library
from .endpoints import queue

# serve the bundle
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/<path:path>', methods=['GET'])
def any_root_path(path):
    return render_template('index.html')

def list_routes():
    """List application endpoints"""

    output = []
    for rule in app.url_map.iter_rules():

        options = {}
        for arg in rule.arguments:
            options[arg] = "[{0}]".format(arg)

        methods = ','.join(rule.methods)
        url = url_for(rule.endpoint, **options)
        url = url.replace("%5B", ":").replace("%5D", "")
        output.append([rule.endpoint, methods, url])

    for endpoint, methods, url in sorted(output, key=lambda x: x[2]):
        line = "{:30s} {:20s} {}".format(endpoint, methods, url)

        print(line)



