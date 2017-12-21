
import os
from flask import Response, request, jsonify, g, send_file

from ..index import app
from ..service.audio_service import AudioService
from ..service.transcode_service import TranscodeService
from .util import requires_auth, requires_no_auth, requires_auth_role, \
                  httpError, verify_token, compressed, requires_auth_query
from itsdangerous import SignatureExpired, BadSignature
from ..dao.library import Song
from ..dao.util import parse_iso_format

from re import findall

def send_file_v2(filepath):
    """
    this currently works only on firefox,

    send a file and allow seeking when streaming
    """

    if not request.headers.has_key("Range"):
        print("content length: " , os.stat(filepath).st_size)
        return send_file(filepath)

    ranges = findall(r"\d+", request.headers["Range"])
    begin  = int( ranges[0] )

    if len(ranges)>1:
        end = int( ranges[1] )
    else:
        end = os.stat(filepath).st_size

    with open(filepath,"rb") as rf:
        rf.seek(begin)
        data = rf.read(end-begin)

    ext = os.path.splitext(filepath)[1]
    mimetype = "audio/mpeg" if ext == ".mp3" else "application/octet-stream"
    rv = Response(data, 206,
        mimetype=mimetype, direct_passthrough=True)

    range = 'bytes {0}-{1}/{2}'.format(begin, end, len(data))
    rv.headers.add('Content-Range', range)
    rv.headers.add('Accept-Ranges','bytes')
    rv.headers.add('Content-Length',len(data))
    rv.headers.add('Content-Disposition', 'attachment',
        filename=os.path.split(filepath)[1])

    print("%s %d" % (range, len(data)))

    return rv

QUERY_LIMIT_MAX = 500

@app.route("/api/library/info", methods=["GET"])
@requires_auth
@compressed
def get_domain_info():

    domain_id = g.current_user['domain_id']
    data = AudioService.instance().getDomainSongInfo(domain_id)
    return jsonify(result=data)

@app.route("/api/library", methods=["GET"])
@requires_auth
@compressed
def search_library():
    """ return song information from the library """

    query = request.args.get('query', None)
    if query is None:
        print("warning: received null query")
    limit = max(1, min(QUERY_LIMIT_MAX, int(request.args.get('limit', 50))))
    page = max(0, int(request.args.get('page', 0)))
    orderby = request.args.get('orderby', 'artist')
    offset = limit * page

    songs = AudioService.instance().search(g.current_user,
        query, limit=limit, orderby=orderby, offset=offset)

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
@requires_auth_query
def get_song_audio(song_id):
    """ stream audio for a specific song
    TODO: a user API token should be sent using a query parameter

    this needs to accessable with a simple GET request, any auth parameters
    must be passed as query parameters, not headers
    """

    song = AudioService.instance().findSongById(g.current_user, song_id)

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
@requires_auth_query
def get_song_art(song_id):
    """ get album art for a specific song

    TODO: query options should be used to specify
        large: a standardized square image (e.g. 512 x 512)
        medium: a standardized square image (eg 256 x 256)
        small: a standardized square image (eg 128 x 128)
        half: a standardized 16x9 image (e.g. 256 x 144)

    Note: the art path should always point to the original file
        the transcode service can be used to generate alternatives on demand
    """

    path = AudioService.instance().getSongArtPath(g.current_user, song_id)

    if not os.path.exists(path):
        return httpError(404, "No Art for %s" % song_id)

    return send_file(path)

@app.route("/api/library/<song_id>/art", methods=["POST"])
@requires_auth
def set_song_art(song_id):
    """ upload album art for a specific song """
    return jsonify(result="ok")

@app.route("/api/library/history", methods=["GET"])
@requires_auth
def get_history():
    """
    returns playback records for the logged in user

    query arguments:
    start: the begining date to return records from
    end: (optional) the last date to return records from , or now.

    start and end time can be in iso format, or unix time stamp
    """
    start = request.args.get('start', None)
    if start is None:
        return httpError(400, "start time must be provided")
    try:
        try:
            start = int(start)
        except ValueError:
            start = int(parse_iso_format(start).timestamp())
    except:
        return httpError(400, "start timestamp not integer or iso date")

    end = request.args.get('end', None)
    if end is not None:
        try:
            try:
                end = int(end)
            except ValueError:
                end = int(parse_iso_format(end).timestamp())
        except:
            return httpError(400, "end timestamp not integer or iso date")

    page = int(request.args.get('page', "0"))
    page_size = int(request.args.get('page_size', "500"))
    offset = page * page_size

    records = AudioService.instance().getPlayHistory(
        g.current_user, start, end, offset=offset, limit=page_size)
    return jsonify({
        "result": records,
        "page": page,
        "page_size": page_size
    })

@app.route("/api/library/history", methods=["POST"])
@requires_auth
def post_history():

    records = request.json
    if records is None or len(records) == 0:
        return httpError(400, "no data sent")
    AudioService.instance().insertPlayHistory(g.current_user, records)

    return jsonify(result="ok")












