
"""
A Resource for accessing the music library
"""
import os
import sys
import logging

from calendar import timegm
import time
from flask import jsonify, render_template, g, request, send_file

from ..dao.library import Song, LibraryException
from ..dao.util import pathCorrectCase

from ..framework.web_resource import WebResource, \
    get, post, put, delete, param, body, compressed, httpError, \
    int_range, int_min, send_generator, null_validator, \
    OpenApiParameter, Integer, String, Boolean, \
    JsonOpenApiBody, ArrayOpenApiBody, StringOpenApiBody

from .util import requires_auth, DateTimeType, files_generator, \
    ImageScaleType

from ..service.transcode_service import ImageScale

from ..service.exception import AudioServiceException

class SearchOrderType(String):
    def __init__(self):
        super(SearchOrderType, self).__init__()
        items = list(Song.fields()) + ['forest', 'random', 'artist_key']
        items.sort()
        self.enum(items)

    def __call__(self, value):
        s = value.lower()

        if s == 'forest':
            return [Song.artist_key, Song.album, Song.title]

        if s == 'random':
            return s

        return super().__call__(s)

class NewSongOpenApiBody(JsonOpenApiBody):

    def model(self):

        model = {}

        for key in Song.textFields():
            model[key] = {"type": "string"}

        for key in Song.numberFields():
            model[key] = {"type": "integer"}

        for key in Song.dateFields():
            model[key] = {"type": "integer", "format": "date"}

        for key in [Song.artist, Song.album, Song.title]:
            model[key]["required"] = True

        return model

class UpdateSongOpenApiBody(JsonOpenApiBody):

    def model(self):

        model = {}

        for key in Song.textFields():
            model[key] = {"type": "string"}

        for key in Song.numberFields():
            model[key] = {"type": "integer"}

        for key in Song.dateFields():
            model[key] = {"type": "integer", "format": "date"}

        for key in [Song.id]:
            model[key]["required"] = True

        return model

class SongResourcePathOpenApiBody(JsonOpenApiBody):

    def model(self):

        return {
            "root": {"type": "string", "required": True},
            "path": {"type": "string", "required": True}
        }

class SongHistoryOpenApiBody(JsonOpenApiBody):
    def model(self):

        return {
            "timestamp": {"type": "integer", "format": "date", "required": True},
            "song_id": {"type": "string", "required": True}
        }



audio_format = String().enum(("raw", "ogg", "mp3", "default")).default("default")

audio_channels = String().enum(("stereo", "mono", "default")).default("stereo")

audio_quality = String().enum(("low", "medium", "high")).default("medium")

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
    @param("query", type_=String().default(None))
    @param("limit", type_=Integer().min(0).max(5000).default(50))
    @param("page", type_=Integer().min(0).default(0))
    @param("orderby", type_=SearchOrderType().default(Song.artist_key))
    @param("showBanished", type_=Boolean().default(False))
    @requires_auth("library_read")
    @compressed
    def search_library(self):
        """ return song information from the library """

        offset = g.args.limit * g.args.page

        songs = self.audio_service.search(g.current_user,
            g.args.query, limit=g.args.limit,
            orderby=g.args.orderby, offset=offset,
            showBanished=g.args.showBanished)

        return jsonify({
            "result": songs,
            "page": g.args.page,
            "page_size": g.args.limit,
        })

    @get("forest")
    @param("query", type_=String().default(None))
    @param("showBanished", type_=Boolean().default(False))
    @requires_auth("library_read")
    @compressed
    def search_library_forest(self):
        """ return song information from the library """

        forest = self.audio_service.search_forest(g.current_user,
            g.args.query, showBanished=g.args.showBanished)

        return jsonify({
            "result": forest,
        })

    @put("")
    @body(ArrayOpenApiBody(UpdateSongOpenApiBody()))
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
    @body(NewSongOpenApiBody())
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
    @param("mode", type_=audio_format)
    @param("quality", type_=audio_quality)
    @param("layout", type_=audio_channels)
    @requires_auth("library_read_song")
    def get_song_audio(self, song_id):

        if g.args.mode == 'default':
            g.args.mode = "ogg"

        channels = {
            "stereo": 2,
            "mono": 1,
            "default": 0,
        }.get(g.args.layout)

        song = self.audio_service.findSongById(g.current_user, song_id)
        path = self.audio_service.getPathFromSong(g.current_user, song)

        if self.transcode_service.shouldTranscodeSong(song, g.args.mode):
            # TODO: Warning: this has the potential for launching 3 IO threads
            #   2 for s3, read and writer side of a process file
            #   1 for transcode, pipeing s3 into a process

            name = self.transcode_service.audioName(song,
                g.args.mode, g.args.quality, nchannels=channels)
            go = self.transcode_service.transcodeSongGen(song,
                g.args.mode, g.args.quality, nchannels=channels)
            if go is not None:
                return send_generator(go, name)

        size = song[Song.file_size] or None
        _, name = self.audio_service.fs.split(path)
        go = files_generator(self.audio_service.fs, path)
        return send_generator(go, name, file_size=size)

    @post("<song_id>/audio")
    @body(SongResourcePathOpenApiBody())
    @requires_auth("library_write_song")
    def set_song_audio(self, song_id):

        self.audio_service.setSongFilePath(
            g.current_user, song_id, g.body['root'], g.body['path'])

        return jsonify(result="OK"), 200

    @get("<song_id>/art")
    @param("scale", type_=ImageScaleType().default(ImageScale.MEDIUM))
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
    @body(SongResourcePathOpenApiBody())
    @requires_auth("library_write_song")
    def set_song_art(self, song_id):

        self.audio_service.setSongAlbumArtPath(
            g.current_user, song_id, g.body['root'], g.body['path'])

        return jsonify(result="OK"), 200

    @post("history/increment")
    @body(ArrayOpenApiBody(StringOpenApiBody()))
    @requires_auth("library_write_song")
    def increment_playcount(self):
        """
        curl -u admin:admin --header "Content-Type: application/json" \
              -X POST -d '["7065c940-3c6f-429f-bfd9-27cccc402447"]' \
              http://localhost:4200/api/library/history/increment
        """

        timestamp = timegm(time.localtime(time.time()))

        records = [{'song_id': sid, 'timestamp': timestamp} for sid in g.body]

        print(records)
        self.audio_service.updatePlayCount(g.current_user, records)

        return jsonify(result="OK"), 200

    @get("history")
    @param("start", type_=DateTimeType().required(True))
    @param("end", type_=DateTimeType().required(True))
    @param("page", type_=Integer().default(0))
    @param("page_size", type_=Integer().default(500))
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
    @body(ArrayOpenApiBody(SongHistoryOpenApiBody()))
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
