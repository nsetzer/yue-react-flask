
"""
A Resource for accessing the music library
"""
import os
import sys
import logging

from flask import jsonify, render_template, g, request, send_file

from ..dao.library import Song, LibraryException
from ..dao.util import pathCorrectCase

from ..framework.web_resource import WebResource, \
    get, post, put, delete, param, body, compressed, httpError, \
    int_range, int_min, send_generator, null_validator

from .util import requires_auth, datetime_validator, search_order_validator, \
    files_generator

from ..service.transcode_service import ImageScale

from ..service.exception import AudioServiceException

def song_validator(song):

    for field in [Song.artist, Song.album, Song.title]:
        if field not in song:
            raise Exception("missing field: %s" % field)

    return song

def song_list_validator(songs):

    for song in songs:
        # every record must have a song id (to update), and
        # at least one other field (that will be modified)
        if Song.id not in song:
            raise Exception("invalid song: missing id")

        if len(song) < 2:
            raise Exception("invalid song: missing field to update")

    return songs

def song_audio_path_validator(info):

    if 'root' not in info:
        raise Exception("Invalid request body: missing root")

    if 'path' not in info:
        raise Exception("Invalid request body: missing path")

    return info

def image_scale_type(name):

    index = ImageScale.fromName(name)
    if index == 0:
        raise Exception("invalid: %s" % name)
    return index

def audio_format(s):
    if s not in ("raw", "ogg", "mp3", "default"):
        raise Exception("Invalid audio format: %s" % s)
    return s

def audio_channels(s):
    if s not in ("stereo", "mono"):
        raise Exception("Invalid audio channel layout: %s" % s)
    return s

def audio_quality(s):
    if s not in ("low", "medium", "high"):
        raise Exception("Invalid audio quality: %s" % s)
    return s

class LibraryResource(WebResource):
    """LibraryResource

    features:
        library_read   - can view information about the domain library
        library_write  - can update information in this domain library
        library_read_song  - can stream music
        library_write_song  - can upload music
    """
    def __init__(self, user_service, audio_service,
      transcode_service, filesys_service):
        super(LibraryResource, self).__init__("/api/library")

        self.user_service = user_service
        self.audio_service = audio_service
        self.transcode_service = transcode_service
        self.filesys_service = filesys_service

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
    @body(song_list_validator)
    @requires_auth("library_write")
    def update_song(self):

        # for song in g.body:
        #     self._correct_path(song)

        try:
            self.audio_service.updateSongs(g.current_user, g.body)
        except LibraryException as e:
            # logging.exception(e)
            return jsonify(result="NOT OK"), 400

        return jsonify(result="OK"), 200

    @post("")
    @body(song_validator)
    @requires_auth("library_write")
    def create_song(self):

        # self._correct_path(g.body)

        song_id = self.audio_service.createSong(g.current_user, g.body)

        return jsonify(result=song_id), 201

    @get("info")
    @requires_auth("library_read")
    @compressed
    def get_domain_info(self):
        data = self.audio_service.getDomainSongUserInfo(g.current_user)
        return jsonify(result=data)

    @get("ref/<ref_id>")
    @requires_auth("library_read")
    def get_song_by_reference(self, ref_id):
        try:
            song = self.audio_service.findSongByReferenceId(g.current_user, int(ref_id))
            return jsonify(result=song)
        except AudioServiceException as e:
            return httpError(404, "No Song for reference id %s" % (ref_id))

    @get("<song_id>")
    @requires_auth("library_read")
    def get_song(self, song_id):
        song = self.audio_service.findSongById(g.current_user, song_id)
        return jsonify(result=song)

    @get("<song_id>/audio")
    @param("mode", type_=audio_format, default="default",
        doc="one of raw|ogg|mp3|default")
    @param("quality", type_=audio_quality, default="medium",
        doc="one of low|medium|high")
    @param("layout", type_=audio_channels, default="stereo",
        doc="one of stereo|mono")
    @requires_auth("library_read_song")
    def get_song_audio(self, song_id):

        # TODO: this default should be in the application config
        if g.args.mode == 'default':
            g.args.mode == "ogg"

        song = self.audio_service.findSongById(g.current_user, song_id)

        if not song:
            return httpError(404, "No Song for id %s" % (song_id))

        path = song[Song.path]

        if not path:
            return httpError(404, "No audio for %s" % (song_id))

        #if not os.path.exists(path):
        #    logging.error("Audio for %s not found at: `%s`" % (song_id, path))
        #    return httpError(404, "Audio File not found")

        # TODO: use storage service? or ask forgiveness instead of
        # making an s3 call here...
        if not self.audio_service.fs.exists(path):
            logging.error("Audio for %s not found at: `%s`" % (song_id, path))
            return httpError(404, "Audio File not found")

        if self.transcode_service.shouldTranscodeSong(song, g.args.mode):
            # TODO: Warning: this has the potential fr=or launching 3 IO threads
            #   2 for s3, read and writer side of a process file
            #   1 for transcode, pipeing s3 into a process
            channels = 2 if g.args.layout == "stereo" else 1
            go = self.transcode_service.transcodeSongGen(song,
                g.args.mode, g.args.quality, nchannels=channels)
            if go is not None:
                return send_generator(go, song[Song.id] + "." + g.args.mode)

        size = song[Song.file_size] or None
        _, name = self.audio_service.fs.split(song[Song.path])
        go = files_generator(self.audio_service.fs, path)
        return send_generator(go, name, file_size=size)

    @post("<song_id>/audio")
    @body(song_audio_path_validator)
    @requires_auth("library_write_song")
    def set_song_audio(self, song_id):

        abs_path = self.filesys_service.getPath(
            g.current_user, g.body['root'], g.body['path'])

        self.audio_service.setSongFilePath(
            g.current_user, song_id, abs_path)

        return jsonify(result="OK"), 200

    @get("<song_id>/art")
    @param("scale", type_=image_scale_type, default=ImageScale.MEDIUM)
    @requires_auth("library_read_song")
    def get_song_art(self, song_id):
        """ get album art for a specific song

        scale can be one of:
            large, medium, small, landscape, landscape_small
        which correspond to various square or rectangle image sizes
        """

        song = self.audio_service.findSongById(g.current_user, song_id)

        path = self.transcode_service.getScaledAlbumArt(song, g.args.scale)

        if not self.audio_service.fs.exists(path):
            logging.error("Art for %s not found at: `%s`" % (song_id, path))
            return httpError(404, "Album art not found")

        record = self.audio_service.fs.file_info(path)
        go = files_generator(self.audio_service.fs, path)
        return send_generator(go, record.name, file_size=record.size)

    @post("<song_id>/art")
    @body(song_audio_path_validator)
    @requires_auth("library_write_song")
    def set_song_art(self, song_id):

        abs_path = self.filesys_service.getPath(
            g.current_user, g.body['root'], g.body['path'])
        self.audio_service.setSongAlbumArtPath(
            g.current_user, song_id, abs_path)

        return jsonify(result="OK"), 200

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
    @body(null_validator)
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

    # def _correct_path(self, song):
    #     # TODO: revisit this: I may want to disable the feature entirely
    #     # or use the filesystem service to handle the path correction.
    #     if Song.path in song:
    #         root = self.audio_service.config.filesystem.media_root
    #         path = song[Song.path]
    #         if not os.path.isabs(path):
    #             path = os.path.join(root, path)
    #         # fix any windows / linux path inconsistencies
    #         # this ensures the path exists on the local filesystem
    #         try:
    #             path = pathCorrectCase(path)
    #         except Exception as e:
    #             return httpError(400, str(e))
    #         # enforce path to exist under media root
    #         # in the future, I may allow more than one media root
    #         if not path.startswith(root):
    #             return httpError(400, "Invalid Path: `%s`" % path)
    #         song[Song.path] = path
