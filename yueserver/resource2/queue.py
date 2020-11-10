import os
import sys
import logging

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

from ..dao.library import Song
from ..dao.util import parse_iso_format, pathCorrectCase
from ..dao.shuffle import binshuffle

from .util import requires_auth, search_order_validator, \
    uuid_validator, uuid_list_validator


class QueueResource(Resource):

    def __init__(self):
        super(QueueResource, self).__init__()

        self.user_service = None
        self.audio_service = None

    @get("/api/queue")
    @requires_auth("user_read")
    @compressed
    def get_queue(self, request):
        songs = self.audio_service.getQueue(request.current_user)
        return Response(200, {}, {"result": songs})

    @post("/api/queue")
    @body(uuid_list_validator)
    @requires_auth("user_write")
    def set_queue(self, request):
        """ set the songs in the queue """

        self.audio_service.setQueue(request.current_user, request.body)

        return Response(200, {}, {"result": "OK"})

    @get("/api/queue/populate")
    @requires_auth("user_write")
    @compressed
    def populate_queue(self, request):
        songs = self.audio_service.populateQueue(request.current_user)
        return Response(200, {}, {"result": songs})

    @get("/api/queue/create")
    @param("query", type_=String().default(None))
    @param("limit", type_=Integer().min(1).max(500).default(50))
    @requires_auth("user_write")
    @compressed
    def create_queue(self, request):
        """ create a new queue using a query, return the new song list """

        if request.query.query is None:
            request.query.query = self.audio_service.defaultQuery(request.current_user)

        songs = self.audio_service.search(request.current_user, request.query.query)

        # TODO: have role based limits on queue size
        songs = binshuffle(songs, lambda x: x['artist'])[:request.query.limit]

        song_ids = [song['id'] for song in songs]
        self.audio_service.setQueue(request.current_user, song_ids)

        return Response(200, {}, {"result": songs})

    @get("/api/queue/query")
    @requires_auth("user_read")
    def get_default_queue(self, request):
        qstr = self.audio_service.defaultQuery(request.current_user)
        return Response(200, {}, {"result": qstr})

    @post("/api/queue/query")
    @body(EmptyBodyOpenApiBody())
    @requires_auth("user_write")
    def set_default_queue(self, request):

        req = request.get_json()

        if 'query' not in req:
            return Response(400, {}, {"error": "invalid request: missing `query`"})

        self.audio_service.setDefaultQuery(request.current_user, req['query'])

        return Response(200, {}, {"result": "OK"})
