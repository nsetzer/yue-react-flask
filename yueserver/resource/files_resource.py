
"""
A resource for browsing parts of the file system, and uploading files
"""
import os, sys
import logging

from flask import jsonify, render_template, g, request, send_file

from ..dao.library import Song
from ..dao.util import parse_iso_format, pathCorrectCase
from ..dao.storage import StorageNotFoundException, CryptMode
from ..dao.filesys.filesys import MemoryFileSystemImpl
from ..dao.filesys.crypt import validatekey, FileDecryptorReader, decryptkey
from ..service.exception import FileSysServiceException
from ..dao.settings import Settings, SettingsDao
from ..dao.image import ImageScale, scale_image_stream

from ..framework.web_resource import WebResource, \
    get, post, put, delete, body, header, compressed, param, httpError, \
    int_range, int_min, send_generator, null_validator, boolean, timed

from .util import requires_auth, files_generator, files_generator_v2

def validate_mode(s):
    s = s.lower()
    if s in [CryptMode.none, CryptMode.client,
      CryptMode.server, CryptMode.system]:
        return s
    raise Exception("invalid encryption mode")

def validate_key(body):
    """read the response body and decode the encryption key
    validate that the key is well formed
    """
    content = request.headers.get('content-type')
    if content and content != "text/plain":
        # must be not given, or text/plain
        raise Exception("invalid content type")
    text = body.read().decode('utf-8')
    return validatekey(text)

def image_scale_type(name):

    if name.lower() in ('null', 'none'):
        return None

    index = ImageScale.fromName(name)
    if index == 0:
        raise Exception("invalid: %s" % name)
    return index

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
    @header("X-YUE-PASSWORD")
    @requires_auth("filesystem_read")
    @timed(100)
    def get_path_root(self, root):
        password = g.headers.get('X-YUE-PASSWORD', None)
        return self._list_path(root, "", password=password, preview=None)

    @get("<root>/path/<path:resPath>")
    @param("list", type_=boolean, default=False,
        doc="do not retrieve contents for files if true")
    @param("preview", type_=image_scale_type, default=None,
        doc="return a preview picture of the resource")
    @header("X-YUE-PASSWORD")
    @requires_auth("filesystem_read")
    @param("dl", type_=boolean, default=True)
    @timed(100)
    def get_path(self, root, resPath):
        password = g.headers.get('X-YUE-PASSWORD', None)
        return self._list_path(root, resPath, g.args.list,
            password=password, preview=g.args.preview, dl=g.args.dl)

    @get("public/<fileId>")
    @param("dl", type_=boolean, default=True)
    @header("X-YUE-PASSWORD")
    def get_public_file(self, fileId):
        """
        return a file that has a public access file identifier.
        authentication is not required.
        the file must not be encrypted
        a password is optional. if the file requires a password it the password
        will be used to validate the download can continue
        """

        try:

            password = g.headers.get('X-YUE-PASSWORD', None)
            info, stream = self.filesys_service.loadPublicFile(
                fileId, password)
            go = files_generator_v2(stream)
            return send_generator(go, info.name,
                file_size=info.size, attachment=g.args.dl)

        except FileSysServiceException:
            return httpError(401, "invalid file id or password")
        except StorageNotFoundException:
            return httpError(404, "invalid file id or password")

    @put("public/<root>/path/<path:resPath>")
    @header("X-YUE-PASSWORD")
    @param("revoke", type_=boolean, default=False)
    @requires_auth("filesystem_write")
    def make_public(self, root, resPath):
        """

        a password is optional, if set the password will be used to validate
        downloads

        the file must exist in the given root, with the given path.
        """

        password = g.headers.get('X-YUE-PASSWORD', None)
        fileId = self.filesys_service.setFilePublic(g.current_user,
            root, resPath, password=password, revoke=g.args.revoke)

        if fileId is None:
            fileId = ""

        return jsonify({
            "result": {"id": fileId},
        })

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
    @param("version", type_=int, doc="file version", default=0)
    @param("crypt", type_=validate_mode, doc="encryption mode",
        default=None)
    @header("X-YUE-PASSWORD")
    @body(null_validator, content_type="application/octet-stream")
    @requires_auth("filesystem_write")
    @timed(100)
    def upload(self, root, resPath):
        """
        mtime: on a successful upload, set the modified time to mtime,
               unix epoch time in seconds
        versiom: if greater than 1, validate version

        error codes:
            409: file already exists and is a newer version
        """

        stream = None
        # support multi part form uploads that
        # have exactly one file in the payload
        # TODO: should we fail otherwise for uploads with more than 1 file
        if request.files and len(request.files) == 1:
            for key in request.files.keys():
                stream = request.files.get(key)
        else:
            stream = g.body

        if g.args.crypt in (CryptMode.server, CryptMode.system):
            password = g.headers.get('X-YUE-PASSWORD', None)
            stream = self.filesys_service.encryptStream(g.current_user,
                password, stream, "r", g.args.crypt)

        self.filesys_service.saveFile(
            g.current_user, root, resPath, stream,
            mtime=g.args.mtime, version=g.args.version,
            permission=g.args.permission, encryption=g.args.crypt)

        return jsonify(result="OK"), 200

    @delete("<root>/path/<path:resPath>")
    @requires_auth("filesystem_delete")
    def remove_file(self, root, resPath):

        self.filesys_service.remove(g.current_user, root, resPath)

        return jsonify(result="OK")

    @get("roots")
    @requires_auth("filesystem_read")
    def get_roots(self):
        # todo this should be a list of names
        roots = self.filesys_service.getRoots(g.current_user)
        return jsonify(result=roots)

    @get("quota")
    @requires_auth("filesystem_read")
    def quota(self):
        obj = self.filesys_service.getUserQuota(g.current_user)
        return jsonify(result=obj)

    @put("change_password")
    @header("X-YUE-PASSWORD")
    @requires_auth("filesystem_write")
    @body(null_validator, content_type="application/octet-stream")
    def change_password(self):
        """
        change the 'server' encryption key

        Note: use set_user_key to change the 'client' encryption key
        the 'system' encryption key can never be changed
        """

        password = g.headers.get('X-YUE-PASSWORD', None)
        new_password = g.body.read().decode("utf-8").strip()

        if not password:
            return httpError(400, "Invalid password 1")
        if not new_password:
            return httpError(400, "Invalid password 2")

        self.filesys_service.changePassword(g.current_user,
            password, new_password)

        return jsonify(result="OK"), 200

    @get("user_key")
    @param("mode", type_=validate_mode, default=CryptMode.client)
    @requires_auth("filesystem_write")
    def user_key(self):
        """
        return the encrypted form of the current file encryption key.

        by default return the client key,
        """
        key = self.filesys_service.getUserKey(
            g.current_user, g.args.mode)

        return jsonify(result={"key": key}), 200

    @put("user_key")
    @requires_auth("filesystem_write")
    @body(validate_key, content_type="text/plain")
    def set_user_key(self):
        """
        set the 'client' encryption key

        only the client key can be set in this way.
        the system keys cannot be changed and the server key
        can be changed via change password api
        """
        self.filesys_service.setUserClientKey(g.current_user, g.body)
        return jsonify(result="OK"), 200

    @get("notes")
    @param("root", type_=str, default='default')
    @param("base", type_=str, default='public/notes')
    @requires_auth("filesystem_read")
    def getUserNotes(self):
        notes = self.filesys_service.getUserNotes(
            g.current_user, g.args.root, dir_path=g.args.base)
        # return note_id => note_info
        payload = {note['file_name']: note for note in notes}
        return jsonify(result=payload)

    @get("notes/<note_id>")
    @param("root", type_=str, default='default')
    @param("base", type_=str, default='public/notes')
    @header("X-YUE-PASSWORD")
    @requires_auth("filesystem_read")
    def getUserNoteContent(self, note_id):
        password = g.headers.get('X-YUE-PASSWORD', None)
        resPath = self.filesys_service.fs.join(g.args.base, note_id)
        return self._list_path(g.args.root, resPath, False,
            password=password, preview=None)

    @post("notes/<note_id>")
    @param("root", type_=str, default='default')
    @param("base", type_=str, default='public/notes')
    @param("crypt", type_=validate_mode, doc="encryption mode",
        default='system')
    @header("X-YUE-PASSWORD")
    @body(null_validator, content_type='text/plain')
    @requires_auth("filesystem_write")
    def setUserNoteContent(self, note_id):
        """convenience function wrapping file upload"""
        resPath = self.filesys_service.fs.join(g.args.base, note_id)

        stream = g.body
        if g.args.crypt in (CryptMode.server, CryptMode.system):
            password = g.headers.get('X-YUE-PASSWORD', None)
            stream = self.filesys_service.encryptStream(g.current_user,
                password, stream, "r", g.args.crypt)
        self.filesys_service.saveFile(
            g.current_user, g.args.root, resPath, stream,
            encryption=g.args.crypt)

        return jsonify(result="OK"), 200

    @delete("notes/<note_id>")
    @param("root", type_=str, default='default')
    @param("base", type_=str, default='public/notes')
    @requires_auth("filesystem_write")
    def deleteUserNote(self, note_id):
        """convenience function wrapping file delete"""
        #resPath = self.filesys_service.fs.join(g.args.base, note_id)
        #self.filesys_service.remove(g.current_user, g.args.root, resPath)
        print("delete: " + note_id)
        return jsonify(result="OK")

    def _list_path(self, root, path, list_=False, password=None, preview=None, dl=True):
        # TODO: move this into the service layer

        # TODO: check for the header X-YUE-ENCRYPTION
        # it should contain the base64 encoded password for the user
        # use this to decrypt the file

        fs = self.filesys_service.fs

        abs_path = self.filesys_service.getFilePath(g.current_user, root, path)

        isFile = False
        try:
            fs_id = self.filesys_service.storageDao.getFilesystemId(
                g.current_user['id'], g.current_user['role_id'], root)
            info = self.filesys_service.storageDao.file_info(
                g.current_user['id'], fs_id, abs_path)
            isFile = not info.isDir
        except StorageNotFoundException as e:
            pass

        if isFile:

            if list_:
                result = self.filesys_service.listSingleFile(g.current_user, root, path)
                return jsonify(result=result)
            elif preview:

                # cache control for preview files
                # check the incoming request to see if the file has changed
                ETag = "%s:%s" % (path, str(info.version))
                if 'If-None-Match' in request.headers:
                    if request.headers['If-None-Match'] == ETag:
                        return b"", 304

                _, name = self.filesys_service.fs.split(info.file_path)
                # todo: return a object containing size and path?
                # table: file_id, preview_mode, preview_url, preview_size
                # TODO: investigate this method, previewFile
                # it is causing a significant amount of request latency
                # even when the preview already exists
                url = self.filesys_service.previewFile(g.current_user,
                    root, path, preview, password)

                stream = self.filesys_service.fs.open(url, "rb")
                if info.encryption in (CryptMode.server, CryptMode.system):
                    if not password and info.encryption == CryptMode.server:
                        return httpError(400, "Invalid Password")
                    stream = self.filesys_service.decryptStream(g.current_user,
                            password, stream, "r", info.encryption)
                go = files_generator_v2(stream)
                headers = {
                    'Cache-Control': 'max-age=31536000',
                    'ETag': ETag,
                }

                return send_generator(go, '%s.%s.png' % (name, preview),
                    file_size=None, headers=headers, attachment=dl)
            else:
                ETag = "%s:%s" % (path, str(info.version))
                if 'If-None-Match' in request.headers:
                    if request.headers['If-None-Match'] == ETag:
                        return b"", 304

                _, name = self.filesys_service.fs.split(info.file_path)
                stream = self.filesys_service.fs.open(info.storage_path, "rb")
                if info.encryption in (CryptMode.server, CryptMode.system):
                    if not password and info.encryption == CryptMode.server:
                        return httpError(400, "Invalid Password")
                    stream = self.filesys_service.decryptStream(g.current_user,
                        password, stream, "r", info.encryption)
                go = files_generator_v2(stream)
                headers = {
                    "X-YUE-VERSION": info.version,
                    "X-YUE-PERMISSION": info.permission,
                    "X-YUE-MTIME": info.mtime,
                    'Cache-Control': 'max-age=31536000',
                    'ETag': ETag,
                }
                return send_generator(go, name,
                    file_size=None, headers=headers, attachment=dl)

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

