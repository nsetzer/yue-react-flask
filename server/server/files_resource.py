

import logging

from flask import jsonify, render_template, g, request, send_file

from ..dao.library import Song
from ..dao.util import parse_iso_format, pathCorrectCase

from ..framework.web_resource import WebResource, \
    get, post, put, delete, compressed

from .util import httpError, requires_auth

class FilesResource(WebResource):
    """QueueResource

    features:
        filesystem_read  - user can read files/dirs
        filesystem_write - user can upload files
    """
    def __init__(self, user_service):
        super(FilesResource, self).__init__("/api/fs")

        self.user_service = user_service

    @get("<root>/path/")
    @requires_auth("filesystem_read")
    def get_path1(self, app, root):
        return self._list_path(root, "")

    @get("<root>/path/<path:path>")
    @requires_auth("filesystem_read")
    def get_path2(self, app, root, path):
        return self._list_path(root, path)

    @post("<root>/path/<path:path>")
    @requires_auth("filesystem_write")
    def upload(self, app, root, path):
        return jsonify(result="NOT OK"), 501

    @get("roots")
    @requires_auth("filesystem_read")
    def get_roots(self, app):
        # todo this should be a list of names
        return jsonify(result=["default", ])

    def _list_path(self, root, path):


        if root != "default":
            return httpError(400, "invalid root `%s`" % root)

        # application config should define a number of valid roots
        # that can be listed.
        os_root = Config.instance().filesystem.media_root
        path = os.path.join(os_root, path)


        if not os.path.exists(path):
            return httpError(404, "path does not exist")

        if os.path.isfile(path):
            return send_file(path)

        return list_directory(root, os_root, path)




