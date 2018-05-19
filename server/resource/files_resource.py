
import os, sys
import logging

from flask import jsonify, render_template, g, request, send_file

from ..dao.library import Song
from ..dao.util import parse_iso_format, pathCorrectCase


from ..framework.web_resource import WebResource, \
    get, post, put, delete, compressed, httpError

from .util import requires_auth

class FilesResource(WebResource):
    """QueueResource

    features:
        filesystem_read  - user can read files/dirs
        filesystem_write - user can upload files
    """
    def __init__(self, user_service, filesys_service):
        super(FilesResource, self).__init__("/api/fs")

        self.user_service = user_service
        self.filesys_service = filesys_service

    @get("<root>/path/")
    @requires_auth("filesystem_read")
    def get_path1(self, root):
        return self._list_path(root, "")

    @get("<root>/path/<path:resPath>")
    @requires_auth("filesystem_read")
    def get_path2(self, root, resPath):
        return self._list_path(root, resPath)

    @post("<root>/path/<path:resPath>")
    @requires_auth("filesystem_write")
    def upload(self, root, resPath):

        self.filesys_service.saveFile(root, resPath, request.stream)

        return jsonify(result="OK"), 200

    @get("roots")
    @requires_auth("filesystem_read")
    def get_roots(self):
        # todo this should be a list of names
        return jsonify(result=["default", ])

    def _list_path(self, root, path):

        if root != "default":
            return httpError(400, "invalid root `%s`" % root)

        # application config should define a number of valid roots
        # that can be listed.
        abs_path = self.filesys_service.getPath(root, path)

        if not os.path.exists(abs_path):
            return httpError(404, "path does not exist")

        if os.path.isfile(abs_path):
            return send_file(abs_path)

        result = self.filesys_service.listDirectory(root, path)
        return jsonify(result=result)




