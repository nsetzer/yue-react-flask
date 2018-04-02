

import logging

from flask import jsonify, render_template, g, request, send_file

from ..dao.library import Song
from ..dao.util import parse_iso_format, pathCorrectCase

from ..framework.web_resource import WebResource, \
    get, post, put, delete, compressed

from .util import httpError, requires_auth

class QueueResource(WebResource):
    """QueueResource

    features:
        library_read   - can view information about the domain library
        library_write  - can update information in this domain library
        library_read_song  - can stream music
        library_write_song  - can upload music
    """
    def __init__(self, user_service, audio_service):
        super(QueueResource, self).__init__("/api/queue")

        self.user_service = user_service
        self.audio_service = audio_service


        self.QUERY_LIMIT_MAX = 200

    @get("")
    @requires_auth("user_read")
    @compressed
    def get_queue(self, app):
        songs = self.audio_service.getQueue(g.current_user)
        return jsonify(result=songs)

    @post("")
    @requires_auth("user_write")
    def set_queue(self, app):
        """ set the songs in the queue """

        records = request.get_json()
        if records is None or len(records) == 0:
            return httpError(400, "no data sent")

        self.audio_service.setQueue(g.current_user, song_ids)

        return jsonify(result="OK")

    @get("populate")
    @requires_auth("user_write")
    def populate_queue(self, app):
        songs = self.audio_service.populateQueue(g.current_user)
        return jsonify(result=songs)


    @get("create")
    @requires_auth("user_write")
    def create_queue(self, app):
        """ create a new queue using a query, return the new song list """

        def_query = self.audio_service.defaultQuery(g.current_user)
        query = request.args.get('query', def_query)
        limit = int(request.args.get('limit', 50))
        limit = max(1, min(self.QUERY_LIMIT_MAX, limit))
        page = max(0, int(request.args.get('page', 0)))

        orderby = request.args.get('orderby', 'artist')
        offset = limit * page

        songs = self.audio_service.search(g.current_user,
            query, limit=limit, orderby=orderby, offset=offset)

        song_ids = [song['id'] for song in songs]
        self.audio_service.setQueue(g.current_user, song_ids)

        # set the default query to the last query used by the user
        # if the query used to create the playlist did not produce
        # more results than the limit, default to an empty query.
        if len(songs) < limit:
            query = ""
        self.audio_service.setDefaultQuery(g.current_user, query)

        qstr = self.audio_service.defaultQuery(g.current_user)
        return jsonify(result=songs)

    @get("query")
    @requires_auth("user_read")
    def create_queue(self, app):
        qstr = self.audio_service.defaultQuery(g.current_user)
        return jsonify(result=qstr)

    @post("query")
    @requires_auth("user_write")
    def create_queue(self, app):

        req = request.get_json()

        if 'query' not in req:
            return httpError(400, "invalid request: missing `query`")

        self.audio_service.setDefaultQuery(g.current_user, req['query'])

        return jsonify(result="OK")
