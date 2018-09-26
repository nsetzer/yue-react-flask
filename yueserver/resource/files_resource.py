
"""
A resource for browsing parts of the file system, and uploading files
"""
import os, sys
import logging

from flask import jsonify, render_template, g, request, send_file

from ..dao.library import Song
from ..dao.util import parse_iso_format, pathCorrectCase
from ..dao.storage import StorageNotFoundException
from ..dao.filesys.filesys import MemoryFileSystemImpl

from ..framework.web_resource import WebResource, \
    get, post, put, delete, body, compressed, param, httpError, \
    int_range, int_min, send_generator, null_validator

from .util import requires_auth, files_generator

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
    def get_path_root(self, root):
        return self._list_path(root, "")

    @get("<root>/path/<path:resPath>")
    @param("list", type_=bool, default=False,
        doc="do not retrieve contents for files if true")
    @requires_auth("filesystem_read")
    def get_path(self, root, resPath):
        return self._list_path(root, resPath, g.args.list)

    @get("<root>/index/")
    @param("limit", type_=int_range(0, 500), default=50)
    @param("page", type_=int_min(0), default=0)
    @requires_auth("filesystem_read")
    @compressed
    def get_index_root(self, root):
        """ return files owned by a user """

        offset = g.args.limit * g.args.page

        files = self.filesys_service.listIndex(g.current_user,
            root, "", limit=g.args.limit, offset=offset)

        return jsonify({
            "result": files,
            "page": g.args.page,
            "page_size": g.args.limit,
        })

    @get("<root>/index/<path:resPath>")
    @param("limit", type_=int_range(0, 500), default=50)
    @param("page", type_=int_min(0), default=0)
    @requires_auth("filesystem_read")
    @compressed
    def get_index(self, root, resPath):
        """ return files owned by a user """

        offset = g.args.limit * g.args.page

        files = self.filesys_service.listIndex(g.current_user,
            root, resPath, limit=g.args.limit, offset=offset)

        return jsonify({
            "result": files,
            "page": g.args.page,
            "page_size": g.args.limit,
        })

    @post("<root>/path/<path:resPath>")
    @param("mtime", type_=int, doc="set file modified time")
    @param("permission", type_=int, doc="unix file permissions", default=0o644)
    @body(null_validator, content_type="application/octet-stream")
    @requires_auth("filesystem_write")
    def upload(self, root, resPath):
        """
        mtime: on a successful upload, set the modified time to mtime,
               unix epoch time in seconds
        """

        self.filesys_service.saveFile(
            g.current_user, root, resPath, g.body,
            mtime=g.args.mtime, permission=g.args.permission)

        return jsonify(result="OK"), 200

    @delete("<root>/path/<path:resPath>")
    @requires_auth("filesystem_delete")
    def delete(self, root, resPath):

        self.filesys_service.remove(g.current_user, root, resPath)

        return jsonify(result="OK")

    @get("roots")
    @requires_auth("filesystem_read")
    def get_roots(self):
        # todo this should be a list of names
        roots = self.filesys_service.getRoots(g.current_user)
        return jsonify(result=roots)

    def _list_path(self, root, path, list_=False):
        # TODO: move this into the service layer

        fs = self.filesys_service.fs
        # application config should define a number of valid roots
        # that can be listed.
        abs_path = self.filesys_service.getPath(g.current_user, root, path)

        isFile = False
        try:
            info = self.filesys_service.storageDao.file_info(g.current_user['id'], abs_path)
            isFile = not info.isDir
        except StorageNotFoundException as e:

            pass

        if isFile:

            if list_:
                result = self.filesys_service.listSingleFile(g.current_user, root, path)
                return jsonify(result=result)
            else:
                _, name = self.filesys_service.fs.split(abs_path)
                go = files_generator(self.filesys_service.fs, abs_path)
                return send_generator(go, name, file_size=None)

        try:
            result = self.filesys_service.listDirectory(g.current_user, root, path)
            return jsonify(result=result)
        except StorageNotFoundException as e:
            if path == "":
                return jsonify(result={"name": root,
                    "path": "", "parent": "",
                    "files": [], "directories": []})

            return httpError(404, "not found: root: `%s` path: `%s`" % (
                root, path))




