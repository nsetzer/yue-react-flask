
from flask import request, jsonify, g

from ..index import app, db
from .util import requires_auth
from ..service.audio_service import AudioService

@app.route("/api/queue/head", methods=["GET"])
@requires_auth
def get_queue_head():
    """ return current song """
    return jsonify(result="ok")

@app.route("/api/queue/rest", methods=["GET"])
@requires_auth
def get_queue_rest():
    """ return queued songs, after the head """
    return jsonify(result="ok")

@app.route("/api/queue/next", methods=["GET"])
@requires_auth
def get_queue_next():
    """ remove head from the queue, return the new head """
    return jsonify(result="ok")
