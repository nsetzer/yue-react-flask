
"""
A resource for serving the application bundle
"""
import os
import time
import logging

from flask import jsonify, render_template, g, request, \
    send_file, send_from_directory, Response, make_response

from ..dao.library import Song
from ..dao.util import parse_iso_format, pathCorrectCase
#  server_health

from ..framework.web_resource import WebResource, \
    get, post, put, delete, header, body, compressed, httpError, \
    send_generator, int_range

class AppResource(WebResource):
    """
    The AppResource defines a set of generic endpoints for the web application
    """

    def __init__(self, config, db, dbtables):
        super(AppResource, self).__init__()
        self.config = config
        self.db = db
        self.dbtables = dbtables

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

        if path.startswith("precache-manifest") and path.endswith(".js"):
            # return service worker script, but do not cache
            # the script name changes on every build
            name = path
            response = make_response(send_from_directory(self.config.build_dir, name))
            response.headers['Cache-Control'] = 'max-age=0'
            return response
        else:
            name = "index.html"
            return send_from_directory(self.config.build_dir, name)


    # TODO: create @compressed_if(ContentType)
    # allow compression for a white list of file extensions / content types
    # only compress text files
    @get("/static/<path:path>")
    @compressed
    def static(self, path):
        """ retrieve static files
        """
        logging.info("get static path: %s" % path)
        response = make_response(send_from_directory(
            self.config.static_dir, path))
        response.headers['Cache-Control'] = 'max-age=31536000'
        return response

    @get("/robots.txt")
    def robots(self):
        robots = "User-agent: *\nDisallow: /\n"
        return Response(robots, mimetype='text/plain')

    @get("/manifest.json")
    def manifest(self):
        keys = {
            "manifest_version": 2,
            "version": "0.0.0",
            "name": "yueapp",
        }
        return jsonify(**keys)

    @get("/service-worker.js")
    def service_worker(self):
        response = make_response(send_from_directory(
            self.config.build_dir, "service-worker.js"))
        response.headers['Cache-Control'] = 'max-age=0'
        return response

    @get("/health")
    def health(self):
        """ return status information about the application
        """

        # showing stats on an un-authenticated endpoint seems risky
        health = self.db.health()
        del health['stats']

        result = {
            "status": "OK",
            "database": health,
            "server": server_health()
        }

        return jsonify(result=result)

    @get("/.well-known/<path:path>")
    def webroot(self, path):
        """ return files from a well known directory

        support for Lets Encrypt certificates
        """
        base = os.path.join(os.getcwd(), ".well-known")
        return send_from_directory(base, path)



