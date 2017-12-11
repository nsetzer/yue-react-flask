
import os
from flask import request, jsonify, g, send_file

from ..index import app
from ..service.audio_service import AudioService
from ..service.transcode_service import TranscodeService
from .util import requires_auth, requires_no_auth, requires_auth_role, \
                  httpError, verify_token
from itsdangerous import SignatureExpired, BadSignature
from ..dao.library import Song

@app.route("/api/library/info", methods=["GET"])
@requires_auth
def get_domain_info():

    domain_id = g.current_user['domain_id']
    data = AudioService.instance().getDomainSongInfo(domain_id)
    return jsonify(result=data)

@app.route("/api/library", methods=["GET"])
@requires_auth
def search_library():
    """ return song information from the library """

    text = request.args.get('text', None)
    limit = max(1, min(100, int(request.args.get('limit', 50))))
    page = max(0, int(request.args.get('page', 0)))
    orderby = request.args.get('orderby', 'artist')
    offset = limit * page

    songs = AudioService.instance().search(g.current_user,
        text, limit=limit, orderby=orderby, offset=offset)

    return jsonify({
        "result": songs,
        "page": page,
        "page_size": limit,
    })

@app.route("/api/library", methods=["POST"])
@requires_auth
def create_song(song_id):
    """ create/update a song record, returns song_id on success """
    return jsonify(result="ok")

@app.route("/api/library/<song_id>", methods=["GET"])
@requires_auth_role('fizzbuzz')
def get_song(song_id):
    """ return information about a specific song """
    song = AudioService.instance().findSongById(g.current_user, song_id)
    return jsonify(result=song)

@app.route("/api/library/<song_id>/audio", methods=["GET"])
@requires_no_auth
def get_song_audio(song_id):
    """ stream audio for a specific song
    TODO: a user API token should be sent using a query parameter

    this needs to accessable with a simple GET request, any auth parameters
    must be passed as query parameters, not headers
    """

    token = request.args.get('token', None)

    if token is None:
        return httpError(400, "Authorization token not specified")

    try:
        user = verify_token(token)

    except BadSignature:
        return httpError(401,
            "Bad token encountered")
    except SignatureExpired:
        return httpError(401,
            "Token has expired")

    song = AudioService.instance().findSongById(user, song_id)

    if not song or not song[Song.path]:
        return httpError(404, "No Audio for %s" % song_id)

    path = song[Song.path]
    if TranscodeService.instance().shouldTranscodeSong(song):
        path = TranscodeService.instance().transcodeSong(song)

    if not os.path.exists(path):
        return httpError(404, "No Audio for %s" % song_id)

    return send_file(path)


@app.route("/api/library/<song_id>/audio", methods=["POST"])
@requires_auth
def set_song_audio(song_id):
    """ upload audio for a song """
    return jsonify(result="ok")

@app.route("/api/library/<song_id>/art", methods=["GET"])
@requires_no_auth
def get_song_art(song_id):
    """ get album art for a specific song
    TODO: a user API token should be sent using a query parameter
    """

    token = request.args.get('token', None)

    if token is None:
        return httpError(400, "Authorization token not specified")

    try:
        user = verify_token(token)

    except BadSignature:
        return httpError(401,
            "Bad token encountered")
    except SignatureExpired:
        return httpError(401,
            "Token has expired")

    path = AudioService.instance().getSongArtPath(g.current_user, song_id)

    if path or not os.path.exists(path):
        return send_file(path)

    return httpError(404, "No Art for %s" % song_id)

@app.route("/api/library/<song_id>/art", methods=["POST"])
@requires_auth
def set_song_art(song_id):
    """ upload album art for a specific song """
    return jsonify(result="ok")
