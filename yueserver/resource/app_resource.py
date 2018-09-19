
"""
A resource for serving the application bundle
"""
import os
import logging

from flask import jsonify, render_template, g, request, send_file, send_from_directory

from ..dao.library import Song
from ..dao.util import parse_iso_format, pathCorrectCase

from ..framework.web_resource import WebResource, \
    get, post, put, delete, compressed, httpError

from .util import requires_auth

class AppResource(WebResource):
    """
    The AppResource defines a set of generic endpoints for the web application
    """

    def __init__(self, config):
        super(AppResource, self).__init__()
        self.config = config

    @get("/")
    def index_root(self):
        """ return the application bundle when no url path is given
        """
        path = os.path.join(self.config.build_dir, 'index.html')
        return open(path).read()

    @get("/<path:path>")
    def index_path(self, path):
        """ return the application bundle when no other url path matches
        """
        # return an error for malformed api requests, instead
        # of returning the bundle
        if path.startswith("api/"):
            return httpError(400, "unknown path")
        path = os.path.join(self.config.build_dir, 'index.html')
        return open(path).read()

    @get("/static/<path:path>")
    def static(self, path):
        """ retrieve static files
        """
        return send_from_directory(self.config.static_dir, path)

    @get("/health")
    def health(self):
        """ return status information about the application
        """
        return jsonify(result="OK")

    @get("/.well-known/<path:path>")
    def webroot(self, path):
        """ return files from a well known directory

        support for Lets Encrypt certificates
        """
        base = os.path.join(os.getcwd(), ".well-known")
        return send_from_directory(base, path)

