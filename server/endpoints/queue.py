
from flask import request, jsonify, g

from ..index import app, db
from .util import requires_auth
from ..dao.library import Song
from ..service.audio_service import AudioService

from .util import httpError

@app.route("/api/queue", methods=["GET"])
@requires_auth
def get_queue():
    """ return current song """
    service = AudioService.instance()
    songs = service.getQueue(g.current_user)
    return jsonify(result=songs)

@app.route("/api/queue", methods=["POST"])
@requires_auth
def set_queue():
    """ set the songs in the queue """

    if request.headers['content-type'] != "application/json":
        return httpError(400, "invalid content-type: %s" %
            request.headeres['content-type'])

    service = AudioService.instance()
    song_ids = request.get_json()
    service.setQueue(g.current_user, song_ids)
    return jsonify(result="ok")

@app.route("/api/queue/head", methods=["GET"])
@requires_auth
def get_queue_head():
    """ return current song """
    service = AudioService.instance()
    song = service.getQueueHead(g.current_user)
    return jsonify(result=song)

@app.route("/api/queue/rest", methods=["GET"])
@requires_auth
def get_queue_rest():
    """ return queued songs, after the head """
    service = AudioService.instance()
    songs = service.getQueueRest(g.current_user)
    return jsonify(result=songs)

@app.route("/api/queue/next", methods=["GET"])
@requires_auth
def get_queue_next():
    """ remove head from the queue, return the new head """

    service = AudioService.instance()
    songs = service.getQueue(g.current_user)
    songs = songs[1:]

    service.setQueue(g.current_user, songs)

    if len(songs) == 0:
        return httpError(404, "empty queue")

    return jsonify(result=songs[0])

@app.route("/api/queue/populate", methods=["GET"])
@requires_auth
def populate_queue():
    """ add songs to the queue using the default query """

    service = AudioService.instance()
    songs = service.populateQueue(g.current_user)

    return jsonify(result=songs)


