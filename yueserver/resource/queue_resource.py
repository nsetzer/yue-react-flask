
"""
A resource for manipulating the users song queue.
"""
import os
import sys
import logging

from flask import jsonify, render_template, g, request, send_file

from ..dao.library import Song
from ..dao.util import parse_iso_format, pathCorrectCase
from ..dao.shuffle import binshuffle

from ..framework.web_resource import WebResource, \
    get, post, put, delete, compressed, httpError, param, body, \
    int_range, int_min, String, Integer, EmptyBodyOpenApiBody

from .util import requires_auth, search_order_validator, \
    uuid_validator, uuid_list_validator

class QueueResource(WebResource):
    """QueueResource

    """
    def __init__(self, user_service, audio_service):
        super(QueueResource, self).__init__("/api/queue")

        self.user_service = user_service
        self.audio_service = audio_service

    @get("")
    @requires_auth("user_read")
    @compressed
    def get_queue(self):
        songs = self.audio_service.getQueue(g.current_user)
        return jsonify(result=songs)

    @post("")
    @body(uuid_list_validator)
    @requires_auth("user_write")
    def set_queue(self):
        """ set the songs in the queue """

        self.audio_service.setQueue(g.current_user, g.body)

        return jsonify(result="OK")

    @get("populate")
    @requires_auth("user_write")
    def populate_queue(self):
        songs = self.audio_service.populateQueue(g.current_user)
        return jsonify(result=songs)

    @get("create")
    @param("query", type_=String().default(None))
    @param("limit", type_=Integer().min(1).max(500).default(50))
    @requires_auth("user_write")
    def create_queue(self):
        """ create a new queue using a query, return the new song list """

        if g.args.query is None:
            g.args.query = self.audio_service.defaultQuery(g.current_user)

        songs = self.audio_service.search(g.current_user, g.args.query)

        # TODO: have role based limits on queue size
        songs = binshuffle(songs, lambda x: x['artist'])[:g.args.limit]

        song_ids = [song['id'] for song in songs]
        self.audio_service.setQueue(g.current_user, song_ids)

        return jsonify(result=songs)

    @get("query")
    @requires_auth("user_read")
    def get_default_queue(self):
        qstr = self.audio_service.defaultQuery(g.current_user)
        return jsonify(result=qstr)

    @post("query")
    @body(EmptyBodyOpenApiBody())
    @requires_auth("user_write")
    def set_default_queue(self):

        req = request.get_json()

        if 'query' not in req:
            return httpError(400, "invalid request: missing `query`")

        self.audio_service.setDefaultQuery(g.current_user, req['query'])

        return jsonify(result="OK")
