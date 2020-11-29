import os
import sys
import logging

from calendar import timegm
import time

from yueserver.framework2.server_core import Response, send_file, send_generator

from yueserver.framework2.openapi import Resource, \
    get, put, post, delete, \
    header, param, body, timed, returns, compressed, \
    String, Integer, Boolean, URI, \
    BinaryStreamOpenApiBody, JsonOpenApiBody, OpenApiParameter, \
    EmptyBodyOpenApiBody, BinaryStreamResponseOpenApiBody, StringOpenApiBody, \
    ArrayOpenApiBody, \
    int_range

from yueserver.framework2.security import requires_no_auth, requires_auth, \
    register_handler, register_security, ExceptionHandler

from .util import files_generator, files_generator_v2, DateTimeType, ImageScaleType


from ..dao.library import Song, LibraryException
from ..dao.util import pathCorrectCase
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


class LibraryResource(Resource):
    def __init__(self):
        super(LibraryResource, self).__init__()

        self.user_service = None
        self.audio_service = None
        self.transcode_service = None
        self.filesys_service = None

    @get("/api/library")
    @param("query", type_=String().default(None))
    @param("limit", type_=Integer().min(0).max(5000).default(50))
    @param("page", type_=Integer().min(0).default(0))
    @param("orderby", type_=SearchOrderType().default(Song.artist_key))
    @param("showBanished", type_=Boolean().default(False))
    @requires_auth("library_read")
    @compressed
    def search_library(self, request):
        """ return song information from the library

        note: when paginating, set orderby to "id" or use the paginate api
        """

        offset = request.query.limit * request.query.page

        songs = self.audio_service.search(request.current_user,
            request.query.query, limit=request.query.limit,
            orderby=request.query.orderby, offset=offset,
            showBanished=request.query.showBanished)

        obj = {
            "result": songs,
            "page": request.query.page,
            "page_size": request.query.limit,
        }
        return Response(200, {}, obj)

    @get("/api/library/paginate")
    @param("query", type_=String().default(None))
    @param("limit", type_=Integer().min(0).max(5000).default(50))
    @param("last_id", type_=String().default(None))
    @param("showBanished", type_=Boolean().default(False))
    @requires_auth("library_read")
    @compressed
    def paginate_library(self, request):
        """ return song information from the library """

        songs = self.audio_service.paginate(request.current_user,
            request.query.query, limit=request.query.limit,
            last_id=request.query.last_id,
            showBanished=request.query.showBanished)

        obj = {
            "result": songs,
        }
        return Response(200, {}, obj)

    @get("/api/library/forest")
    @param("query", type_=String().default(None))
    @param("showBanished", type_=Boolean().default(False))
    @requires_auth("library_read")
    @compressed
    def search_library_forest(self, request):
        """ return song information from the library """

        forest = self.audio_service.search_forest(request.current_user,
            request.query.query, showBanished=request.query.showBanished)

        return Response(201, {}, {"result": forest})

    @put("/api/library")
    @body(ArrayOpenApiBody(UpdateSongOpenApiBody()))
    @requires_auth("library_write")
    def update_song(self, request):

        # for song in g.body:
        #     self._correct_path(song)

        error = 200
        try:
            n = self.audio_service.updateSongs(request.current_user, request.body)

            error = 200 if n==1 else 400
        except LibraryException as e:
            # logging.exception(e)
            return Response(400, {}, {"error": "%s" % e})

        return Response(200, {}, {"result": "OK"})

    @post("/api/library")
    @body(NewSongOpenApiBody())
    @requires_auth("library_write")
    def create_song(self, request):

        song_id = self.audio_service.createSong(request.current_user, request.body)

        return Response(201, {}, {"result": song_id})



    @get("/api/library/info")
    @requires_auth("library_read")
    @compressed
    def get_domain_info(self, request):
        data = self.audio_service.getDomainSongUserInfo(request.current_user)
        return Response(200, {}, {"result": data})

    @get("/api/library/ref/:ref_id")
    @requires_auth("library_read")
    def get_song_by_reference(self, ref_id):
        try:
            song = self.audio_service.findSongByReferenceId(request.current_user, int(ref_id))
            return Response(200, {}, {"result": song})
        except AudioServiceException as e:
            return Response(404, {}, {"error": "No Song for reference id %s" % (ref_id)})

    @get("/api/library/:song_id")
    @requires_auth("library_read")
    def get_song(self, request):
        try:
            song = self.audio_service.findSongById(request.current_user, request.args.song_id)
            return Response(200, {}, {"result": song})
        except AudioServiceException as e:
            return Response(404, {}, {"error": "No Song for id %s" % (request.args.song_id)})

    @delete("/api/library/:song_id")
    @requires_auth("library_write")
    def delete_song(self, request):

        try:
            success = self.audio_service.deleteSong(
                request.current_user,
                request.args.song_id)
        except AudioServiceException as e:
            success = False

        return Response(200 if success else 404, {},
            {"result": "OK" if success else "ERROR"})

    @get("/api/library/:song_id/audio")
    @param("mode", type_=audio_format)
    @param("quality", type_=audio_quality)
    @param("layout", type_=audio_channels)
    @requires_auth("library_read_song")
    def get_song_audio(self, request):

        if request.query.mode == 'default':
            request.query.mode = "ogg"

        channels = {
            "stereo": 2,
            "mono": 1,
            "default": 0,
        }.get(request.query.layout)

        song = self.audio_service.findSongById(request.current_user, request.args.song_id)
        path = self.audio_service.getPathFromSong(request.current_user, song)

        if self.transcode_service.shouldTranscodeSong(song, request.query.mode):
            # TODO: Warning: this has the potential for launching 3 IO threads
            #   2 for s3, read and writer side of a process file
            #   1 for transcode, pipeing s3 into a process

            name = self.transcode_service.audioName(song,
                request.query.mode, request.query.quality, nchannels=channels)
            go = self.transcode_service.transcodeSongGen(song,
                request.query.mode, request.query.quality, nchannels=channels)
            if go is not None:
                return send_generator(go, name)

        size = song[Song.file_size] or None
        _, name = self.audio_service.fs.split(path)
        go = files_generator(self.audio_service.fs, path)
        return send_generator(go, name, file_size=size)

    @post("/api/library/:song_id/audio")
    @body(SongResourcePathOpenApiBody())
    @requires_auth("library_write_song")
    def set_song_audio(self, request):

        self.audio_service.setSongFilePath(
            request.current_user, request.args.song_id, request.body['root'], request.body['path'])

        return Response(200, {}, {"result": "OK"})

    @get("/api/library/:song_id/art")
    @param("scale", type_=ImageScaleType().default('medium'))
    @requires_auth("library_read_song")
    def get_song_art(self, request):
        """ get album art for a specific song

        scale can be one of:
            large, medium, small, landscape, landscape_small
        which correspond to various square or rectangle image sizes
        """

        song = self.audio_service.findSongById(request.current_user, request.args.song_id)

        path = self.transcode_service.getScaledAlbumArt(song, request.query.scale)

        if not self.audio_service.fs.exists(path):
            logging.error("Art for %s not found at: `%s`" % (request.args.song_id, path))
            return Response(404, {}, {"error":"Album art not found"})

        record = self.audio_service.fs.file_info(path)
        go = files_generator(self.audio_service.fs, path)
        return send_generator(go, record.name, file_size=record.size)

    @post("/api/library/:song_id/art")
    @body(SongResourcePathOpenApiBody())
    @requires_auth("library_write_song")
    def set_song_art(self, request):

        self.audio_service.setSongAlbumArtPath(
            request.current_user, request.args.song_id, request.body['root'], request.body['path'])

        return Response(200, {}, {"result": "OK"})

    @post("/api/library/history/increment")
    @body(ArrayOpenApiBody(StringOpenApiBody()))
    @requires_auth("library_write_song")
    def increment_playcount(self, request):
        """
        curl -u admin:admin --header "Content-Type: application/json" \
              -X POST -d '["7065c940-3c6f-429f-bfd9-27cccc402447"]' \
              http://localhost:4200/api/library/history/increment
        """

        timestamp = timegm(time.localtime(time.time()))

        records = [{'song_id': sid, 'timestamp': timestamp} for sid in request.body]

        self.audio_service.updatePlayCount(request.current_user, records)

        return Response(200, {}, {"result": "OK"})

    @get("/api/library/history")
    @param("start", type_=DateTimeType().required(True))
    @param("end", type_=DateTimeType().required(True))
    @param("page", type_=Integer().default(0))
    @param("page_size", type_=Integer().default(500))
    @requires_auth("user_read")
    def get_history(self, request):
        """
        get song history between a date range

        the start and end time can be an integer or ISO string.
        """

        offset = request.query.page * request.query.page_size

        records = self.audio_service.getPlayHistory(
            request.current_user, request.query.start, request.query.end,
            offset=offset, limit=request.query.page_size)

        obj = {
            "result": records,
            "page": request.query.page,
            "page_size": request.query.page_size
        }
        return Response(200, {}, obj)

        """
        get song history between a date range
        the start and end time can be an integer or ISO string.
        """

        offset = request.query.page * request.query.page_size

        records = self.audio_service.getPlayHistory(
            request.current_user, request.query.start, request.query.end,
            offset=offset, limit=request.query.page_size)

        obj = {
            "result": records,
            "page": request.query.page,
            "page_size": request.query.page_size
        }
        return Response(200, {}, obj)

    @post("/api/library/history")
    @body(ArrayOpenApiBody(SongHistoryOpenApiBody()))
    @requires_auth("user_write")
    def update_history(self, request):
        """

        the json payload is a list of history records.
            {"timestamp": <epoch_time>, "song_id": <song_id>}

        epoch_time is the number of seconds since the UNIX epoch as an integer
        """

        records = request.json
        if records is None or len(records) == 0:
            return Response(400, {}, {"error": "no data sent"})

        count = self.audio_service.insertPlayHistory(request.current_user, records)

        obj = {"result": count, "records": len(records)}
        return Response(200, {}, obj)
