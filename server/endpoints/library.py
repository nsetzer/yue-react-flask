

from flask import request, jsonify, g

from ..index import app, db
from ..models.user import User
from ..models.song import Song, Library
from .util import requires_auth

@app.route("/api/library", methods=["GET"])
@requires_auth
def get_library():
    """ return song information from the library """
    return jsonify(result="ok")

@app.route("/api/library", methods=["POST"])
@requires_auth
def create_song(song_id):
    """ create/update a song record, returns song_id on success """
    return jsonify(result="ok")

@app.route("/api/library/<song_id>", methods=["GET"])
@requires_auth
def get_song(song_id):
    """ return information about a specific song """
    song = g.library.findSongById(song_id)
    return jsonify(result=song)

@app.route("/api/library/<song_id>/audio", methods=["GET"])
@requires_auth
def get_song_audio(song_id):
    """ stream audio for a specific song """
    return jsonify(result="ok")

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
