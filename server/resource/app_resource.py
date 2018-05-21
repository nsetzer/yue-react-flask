
import os
import logging

from flask import jsonify, render_template, g, request, send_file, send_from_directory

from ..dao.library import Song
from ..dao.util import parse_iso_format, pathCorrectCase

from ..framework.web_resource import WebResource, \
    get, post, put, delete, compressed, httpError

from .util import requires_auth

class AppResource(WebResource):
    """docstring for AppResource
    """

    def __init__(self, config):
        super(AppResource, self).__init__()
        self.config = config

    @get("/")
    def index1(self):
        path = os.path.join(self.config.build_dir, 'index.html')
        return open(path).read()

    @get("/<path:path>")
    def index2(self, path):
        # return an error for malformed api requests, instead
        # of returning the bundle
        if path.startswith("api/"):
            return httpError(400, "unknown path")
        path = os.path.join(self.config.build_dir, 'index.html')
        return open(path).read()

    @get("/static/<path:path>")
    def static(self, path):
        return send_from_directory(self.config.static_dir, path)

    @get("/health")
    def health(self):
        return jsonify(result="OK")

    @get("/.well-known/<path:path>")
    def webroot(self, path):
        base = os.path.join(os.getcwd(), ".well-known")
        return send_from_directory(base, path)