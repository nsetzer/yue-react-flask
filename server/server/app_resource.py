

import logging

from flask import jsonify, render_template, g, request, send_file

from ..dao.library import Song
from ..dao.util import parse_iso_format, pathCorrectCase

from ..framework.web_resource import WebResource, \
    get, post, put, delete, compressed

from .util import httpError, requires_auth

class AppResource(WebResource):
    """docstring for AppResource
    """

    def __init__(self):
        super(AppResource, self).__init__()
        #self.register('/', self.index1, ['GET'])
        #self.register('/<path:path>', self.index2, ['GET'])
        #self.register('/health', self.health, ['GET'])
        #self.register('/.well-known/<path:path>', self.webroot, ['GET'])

    @get("/")
    def index1(self, app):
        return render_template('index.html')

    @get("/<path:path>")
    def index2(self, app, path):
        return render_template('index.html')

    @get("/health")
    def health(self, app):
        return jsonify(result="OK")

    @get("/.well-known/<path:path>")
    def webroot(self, app, path):
        base = os.path.join(os.getcwd(), ".well-known")
        return send_from_directory(base, path)