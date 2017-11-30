

from flask import request, jsonify, g, send_file

from ..index import app
from ..service.audio_service import AudioService
from .util import requires_auth, httpError

@app.route("/api/library", methods=["GET"])
@requires_auth
def get_library():
    """ return song information from the library """

    songs = AudioService.instance().search(g.current_user, song_id)

    return jsonify(result=songs)

@app.route("/api/library", methods=["POST"])
@requires_auth
def create_song(song_id):
    """ create/update a song record, returns song_id on success """
    return jsonify(result="ok")

@app.route("/api/library/<song_id>", methods=["GET"])
@requires_auth
def get_song(song_id):
    """ return information about a specific song """
    song = AudioService.instance().findSongById(g.current_user, song_id)
    return jsonify(result=song)

@app.route("/api/library/<song_id>/audio", methods=["GET"])
@requires_auth
def get_song_audio(song_id):
    """ stream audio for a specific song """

    path = AudioService.instance().getSongAudioPath(g.current_user, song_id)

    return send_file(path)

@app.route("/api/library/<song_id>/audio", methods=["POST"])
@requires_auth
def set_song_audio(song_id):
    """ upload audio for a song """
    return jsonify(result="ok")

@app.route("/api/library/<song_id>/art", methods=["GET"])
@requires_auth
def get_song_art(song_id):
    """ get album art for a specific song """
    return jsonify(result="ok")

@app.route("/api/library/<song_id>/art", methods=["POST"])
@requires_auth
def set_song_art(song_id):
    """ upload album art for a specific song """
    return jsonify(result="ok")
