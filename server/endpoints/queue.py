
from flask import request, jsonify, g
from flask_cors import cross_origin
from ..index import app, db
from .util import requires_auth
from ..dao.library import Song
from ..service.audio_service import AudioService

from .util import httpError, get_request_header, compressed, \
    requires_auth_query, requires_auth_feature

QUERY_LIMIT_MAX = 200

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
@requires_auth_feature("read_user")
@compressed
def get_queue():
    """ return current song """
    service = AudioService.instance()
    songs = service.getQueue(g.current_user)
    return jsonify(result=songs)

@app.route("/api/queue", methods=["POST"])
@cross_origin(supports_credentials=True)
@requires_auth_feature("write_user")
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

@app.route("/api/queue/populate", methods=["GET"])
@cross_origin(supports_credentials=True)
@requires_auth_feature("write_user")
def populate_queue():
    """ add songs to the queue using the default query """

    service = AudioService.instance()
    songs = service.populateQueue(g.current_user)

    return jsonify(result=songs)

@app.route("/api/queue/create", methods=["GET"])
@cross_origin(supports_credentials=True)
@requires_auth_feature("write_user")
def create_queue_from_query():
    """ create a new queue using a query, return the new song list """

    def_query = AudioService.instance().defaultQuery(g.current_user)
    query = request.args.get('query', def_query)
    limit = max(1, min(QUERY_LIMIT_MAX, int(request.args.get('limit', 50))))
    page = max(0, int(request.args.get('page', 0)))

    orderby = request.args.get('orderby', 'artist')
    offset = limit * page

    songs = AudioService.instance().search(g.current_user,
        query, limit=limit, orderby=orderby, offset=offset)

    song_ids = [song['id'] for song in songs]
    AudioService.instance().setQueue(g.current_user, song_ids)

    # set the default query to the last query used by the user
    # if the query used to create the playlist did not produce
    # more results than the limit, default to an empty query.
    if len(songs) < limit:
        query = ""
    AudioService.instance().setDefaultQuery(g.current_user, query)

    qstr = AudioService.instance().defaultQuery(g.current_user)
    return jsonify(result=songs)

@app.route("/api/queue/query", methods=["GET"])
@cross_origin(supports_credentials=True)
@requires_auth_feature("read_user")
def get_queue_query():
    """ return the default query for the user """

    qstr = AudioService.instance().defaultQuery(g.current_user)

    return jsonify(result=qstr)

@app.route("/api/queue/query", methods=["POST"])
@cross_origin(supports_credentials=True)
@requires_auth_feature("write_user")
def set_queue_query():
    """ set the defualt query for the user """

    if content_type != "application/json":
        return httpError(400, "invalid content-type: %s" %
            request.headers['content-type'])

    req = request.get_json()

    if 'query' not in req:
        return httpError(400, "invalid request: missing `text`")

    AudioService.instance().setDefaultQuery(g.current_user, req['query'])

    return jsonify(result="OK")


