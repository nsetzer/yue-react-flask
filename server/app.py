import os, sys

from flask import Flask, request, render_template, jsonify, url_for

from .index import db, dbtables, app, cors
from .service.audio_service import AudioService
from .service.user_service import UserService
from .service.transcode_service import TranscodeService

# init services before endpoints
AudioService.init(db, dbtables)
UserService.init(db, dbtables)
TranscodeService.init(db, dbtables)

"""
@app.before_request
def csrf_protect():
    if request.method == "POST":
        token = request.headers.get('X-CSRF-TOKEN', None)
        cookie = request.cookies.get('CSRF-TOKEN', None)
        sys.stderr.write("TODO: ON-POST: validate X-CSRF-TOKEN %s %s\n" % (
            token, cookie))
"""

from .endpoints import user
from .endpoints import library
from .endpoints import queue

# serve the bundle when requesting the default path
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

# serve the bundle when requesting the any path
@app.route('/<path:path>', methods=['GET'])
def index_any(path):
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



