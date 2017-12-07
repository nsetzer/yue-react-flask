
from flask import request, jsonify, g
from flask_cors import cross_origin
from ..index import app, db
from .util import requires_auth
from ..dao.library import Song
from ..service.audio_service import AudioService

from .util import httpError, get_request_header

"""
curl -v \
    --cookie "CSRF-TOKEN=ANYSTRING" \
    -H "X-CSRF-TOKEN: ANYSTRING" \
    -H "Origin: http://localhost:4100" \
    -H 'Content-Type: application/json' \
    -u user000:user000 \
    -X POST -d "[]" localhost:4200/api/queue

curl -v \
    -H "Origin: http://localhost:4100" \
    -H "Access-Control-Request-Method: POST" \
    -H "Access-Control-Request-Headers: X-Requested-With" \
    -X OPTIONS  http://localhost:4200/api/queue

"""
@app.route("/api/queue", methods=["GET"])
@cross_origin(supports_credentials=True)
@requires_auth
def get_queue():
    """ return current song """
    service = AudioService.instance()
    songs = service.getQueue(g.current_user)
    return jsonify(result=songs)

@app.route("/api/queue", methods=["POST"])
@cross_origin(supports_credentials=True)
@requires_auth
def set_queue():
    """ set the songs in the queue """
    content_type = get_request_header(request, "Content-Type")

    if content_type != "application/json":
        return httpError(400, "invalid content-type: %s" %
            request.headers['content-type'])

    service = AudioService.instance()
    song_ids = request.get_json()
    service.setQueue(g.current_user, song_ids)

    return jsonify(result="OK")

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


