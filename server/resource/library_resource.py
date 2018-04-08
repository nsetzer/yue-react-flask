
import os
import sys
import logging

from flask import jsonify, render_template, g, request, send_file

from ..dao.library import Song
from ..dao.util import pathCorrectCase

from ..framework.web_resource import WebResource, \
    get, post, put, delete, param, compressed, httpError, int_range, int_min

from .util import requires_auth, datetime_validator, search_order_validator

class LibraryResource(WebResource):
    """LibraryResource

    features:
        library_read   - can view information about the domain library
        library_write  - can update information in this domain library
        library_read_song  - can stream music
        library_write_song  - can upload music
    """
    def __init__(self, user_service, audio_service, transcode_service):
        super(LibraryResource, self).__init__("/api/library")

        self.user_service = user_service
        self.audio_service = audio_service
        self.transcode_service = transcode_service

    @get("")
    @param("query", default=None)
    @param("limit", type_=int_range(0, 500), default=50)
    @param("page", type_=int_min(0), default=0)
    @param("orderby", type_=search_order_validator, default=Song.artist)
    @requires_auth("library_read")
    @compressed
    def search_library(self):
        """ return song information from the library """

        offset = g.args.limit * g.args.page

        songs = self.audio_service.search(g.current_user,
            g.args.query, limit=g.args.limit,
            orderby=g.args.orderby, offset=offset)

        return jsonify({
            "result": songs,
            "page": g.args.page,
            "page_size": g.args.limit,
        })

    @put("")
    @requires_auth("library_write")
    def update_song(self):

        songs = request.json

        response = self._validate_song_list(app, songs)
        if response is not None:
            return response

        self.audio_service.updateSongs(g.current_user, songs)

    @post("")
    @requires_auth("library_write")
    def create_song(self):
        song = request.json

        response = self._validate_song_list(app, [song,])
        if response is not None:
            return response

        # first quickly verify the data is well formed
        for field in [Song.artist, Song.album, Song.title]:
            if field not in song:
                return httpError(400, "`%s` missing from song meta data" % field)

        song_id = self.audio_service.createSong(g.current_user, song)

        return jsonify(result=song_id)

    @get("info")
    @requires_auth("library_read")
    @compressed
    def get_domain_info(self):
        data = self.audio_service.getDomainSongUserInfo(g.current_user)
        return jsonify(result=data)

    @get("<song_id>")
    @requires_auth("library_read")
    def get_song(self, song_id):
        song = self.audio_service.findSongById(g.current_user, song_id)
        return jsonify(result=song)

    @get("<song_id>/audio")
    @param("mode", default="default")
    @requires_auth("library_read_song")
    def get_song_audio(self, song_id):

        song = self.audio_service.findSongById(g.current_user, song_id)

        if not song:
            return httpError(404, "No Song for id %s" % (song_id))

        path = song[Song.path]

        if not path:
            return httpError(404, "No audio for %s" % (song_id))

        if not os.path.exists(path):
            logging.error("Audio for %s not found at: `%s`" % (song_id, path))
            return httpError(404, "Audio File not found")

        if self.transcode_service.shouldTranscodeSong(song, g.args.mode):
            path = self.transcode_service.transcodeSong(song, g.args.mode)

        if not os.path.exists(path):
            logging.error("Audio for %s not found at: `%s`" % (song_id, path))
            return httpError(404, "Audio File not found")

        return send_file(path)

    @post("<song_id>/audio")
    @requires_auth("library_write_song")
    def set_song_audio(self, song_id):
        return jsonify(result="NOT OK"), 501

    @get("<song_id>/art")
    @requires_auth("library_read_song")
    def get_song_art(self, song_id):
        """ get album art for a specific song

        TODO: query options should be used to specify
            large: a standardized square image (e.g. 512 x 512)
            medium: a standardized square image (eg 256 x 256)
            small: a standardized square image (eg 128 x 128)
            half: a standardized 16x9 image (e.g. 256 x 144)

        Note: the art path should always point to the original file
            the transcode service can be used to generate alternatives on demand
        """

        path = self.audio_service.getSongArtPath(g.current_user, song_id)

        if not os.path.exists(path):
            logging.error("Art for %s not found at: `%s`" % (song_id, path))
            return httpError(404, "Album art not found")

        return send_file(path)

    @post("<song_id>/art")
    @requires_auth("library_write_song")
    def set_song_art(self, song_id):
        return jsonify(result="NOT OK"), 501

    @get("history")
    @param("start", type_=datetime_validator, required=True)
    @param("end", type_=datetime_validator, required=True)
    @param("page", type_=int, default=0)
    @param("page_size", type_=int, default=500)
    @requires_auth("user_read")
    def get_history(self):
        """
        get song history between a date range

        the start and end time can be an integer or ISO string.
        """

        offset = g.args.page * g.args.page_size

        records = self.audio_service.getPlayHistory(
            g.current_user, g.args.start, g.args.end,
            offset=offset, limit=g.args.page_size)

        return jsonify({
            "result": records,
            "page": g.args.page,
            "page_size": g.args.page_size
        })

    @post("history")
    @requires_auth("user_write")
    def update_history(self):
        """

        the json payload is a list of history records.
            {"timestamp": <epoch_time>, "song_id": <song_id>}

        epoch_time is the number of seconds since the UNIX epoch as an integer
        """

        records = request.json
        if records is None or len(records) == 0:
            return httpError(400, "no data sent")

        count = self.audio_service.insertPlayHistory(g.current_user, records)

        return jsonify({"result": count, "records": len(records)})

    def _validate_song_list(self, songs):

        for song in songs:
            # every record must have a song id (to update), and
            # at least one other field (that will be modified)
            if Song.id not in song or len(song) < 2:
                return httpError(400, "invalid update request")

            # if a path is given, it must already exist
            # see create_song and upload_song_audio for setting a path
            # when the file does not yet exist.
            if Song.path in song:
                root = Config.instance().filesystem.media_root
                path = song[Song.path]
                if not os.path.isabs(path):
                    path = os.path.join(root, path)

                # fix any windows / linux path inconsistencies
                # this ensures the path exists on the local filesystem
                try:
                    path = pathCorrectCase(path)
                except Exception as e:
                    return httpError(400, str(e))

                # enforce path to exist under media root
                # in the future, I may allow more than one media root
                if not path.startswith(root):
                    return httpError(400, "Invalid Path: `%s`" % path)

                song[Song.path] = path
                logging.error("upload (w/ path): %s", song)
            else:
                logging.error("upload (no path): %s", song)

        return None