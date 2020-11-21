

# head -c $[1024*1024*25] /dev/urandom > tmp
# head -c $[1024*1024*100] /dev/urandom > tmp

# time curl -v -k -L -u admin:admin localhost/.speedtest/50/2048'?token=foo' -o tmp
# time curl -v -k -L -X POST -u admin:admin -H "Content-Type: application/octet-stream" --upload-file tmp https://localhost/.speedtest
# time curl -v -k -L -X POST -u admin:admin -H "Content-Type: application/octet-stream" --upload-file tmp https://localhost/.speedtest


# time curl -v -k -L -u admin:admin -X GET tmp https://localhost/api/fs/default/search'?terms=x&terms=y'
# time curl -v -k -L --compressed -u admin:admin -X GET https://localhost/api/fs/default/search'?terms=x&terms=y&limit=5'
# time curl -v -k -L -u admin:admin -X PUT --data-binary "new_password" -H "X-YUE-PASSWORD: old_password" https://localhost/api/fs/change_password

#
import os
import time
import mimetypes
import json
import logging

from yueserver.framework2.server_core import Response, send_file, send_generator

from yueserver.framework2.openapi import Resource, \
    get, put, post, delete, \
    header, param, body, timed, returns, compressed, \
    String, Integer, Boolean, URI, \
    BinaryStreamOpenApiBody, JsonOpenApiBody, OpenApiParameter, \
    EmptyBodyOpenApiBody, BinaryStreamResponseOpenApiBody, StringOpenApiBody, \
    TextStreamOpenApiBody, \
    int_range

from yueserver.framework2.security import requires_no_auth, requires_auth, \
    register_handler, register_security, ExceptionHandler

from .util import files_generator, files_generator_v2, ImageScaleType

from ..dao.library import Song
from ..dao.util import parse_iso_format, pathCorrectCase
from ..dao.storage import StorageNotFoundException, CryptMode
from ..dao.filesys.filesys import MemoryFileSystemImpl
from ..dao.filesys.crypt import validatekey, FileDecryptorReader, decryptkey
from ..service.exception import FileSysServiceException
from ..dao.settings import Settings, SettingsDao
from ..dao.image import ImageScale, scale_image_stream

validate_mode = String() \
                    .enum((CryptMode.none, CryptMode.client,
                           CryptMode.server, CryptMode.system),
                          case_sensitive=False) \
                    .default(None) \
                    .description("encryption mode")

validate_mode_client = String() \
                    .enum((CryptMode.none, CryptMode.client,
                           CryptMode.server, CryptMode.system),
                          case_sensitive=False) \
                    .default(CryptMode.client) \
                    .description("encryption mode")

validate_mode_system = String() \
                    .enum((CryptMode.none, CryptMode.client,
                           CryptMode.server, CryptMode.system),
                          case_sensitive=False) \
                    .default(CryptMode.system) \
                    .description("encryption mode")


def speedtest_gen(count, size):
    data = b"\x2B\xAD" + (b"\x00" * (size - 2))
    for i in range(count):
        yield data

class EncryptionKeyOpenApiBody(object):

    def __init__(self):
        super()
        self.__name__ = self.__class__.__name__

    def __call__(self, body):
        """read the response body and decode the encryption key
        validate that the key is well formed
        """
        content = request.headers.get('content-type')
        if content and content != "text/plain":
            # must be not given, or text/plain
            raise Exception("invalid content type")
        text = body.read().decode('utf-8')
        return validatekey(text)

    def name(self):
        return self.__class__.__name__.replace("OpenApiBody", "")

    def mimetype(self):
        return "text/plain"

    def type(self):
        return "string"

class MoveFileOpenApiBody(JsonOpenApiBody):

    def model(self):

        model = {
            "src": {"type": "string"},
            "dst": {"type": "string"},
        }

        return model

class NotesOpenApiBody(JsonOpenApiBody):

    def model(self):

        model = {
        }

        return model


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

def _list_path(request, service, root, path, list_=False, password=None, preview=None, dl=True):
    # TODO: move this into the service layer
    #       the argument against is it still depends on some flask features

    # TODO: check for the header X-YUE-ENCRYPTION
    # it should contain the base64 encoded password for the user
    # use this to decrypt the file

    abs_path = service.getFilePath(request.current_user, root, path)

    isFile = False
    try:
        fs_id = service.storageDao.getFilesystemId(
            request.current_user['id'], request.current_user['role_id'], root)
        info = service.storageDao.file_info(
            request.current_user['id'], fs_id, abs_path)
        isFile = not info.isDir
    except StorageNotFoundException as e:
        pass

    if isFile:

        if list_:
            result = service.listSingleFile(request.current_user, root, path)
            return Response(200, {}, {"result": result})
        elif preview:

            # cache control for preview files
            # check the incoming request to see if the file has changed
            ETag = "%s:%s" % (path, str(info.version))
            if 'If-None-Match' in request.headers:
                if request.headers['If-None-Match'] == ETag:
                    return Response(304)

            _, name = service.fs.split(info.file_path)
            # todo: return a object containing size and path?
            # table: file_id, preview_mode, preview_url, preview_size
            # TODO: investigate this method, previewFile
            # it is causing a significant amount of request latency
            # even when the preview already exists
            previewInfo = service.previewFile(request.current_user,
                root, path, preview, password)

            if previewInfo is None:
                return Response(422, {}, {"error": "Transcode Error"})

            #stream = service.fs.open(url, "rb")
            #if info.encryption in (CryptMode.server, CryptMode.system):
            #    if not password and info.encryption == CryptMode.server:
            #        return Response(400, {}, {"error": "Invalid Password"})
            #    stream = service.decryptStream(request.current_user,
            #            password, stream, "r", info.encryption)
            #go = files_generator_v2(stream)
            headers = {
                'Cache-Control': 'max-age=31536000',
                'ETag': ETag,
                'X-YUE-ROOT': root,
                'X-YUE-PATH': path,
            }
            name = '%s.%s.png' % (name, preview)

            if info.encryption in (CryptMode.server, CryptMode.system):
                if not password and info.encryption == CryptMode.server:
                    return Response(400, {}, {"error": "Invalid Password"})

            info.storage_path = previewInfo.path

            callback = service.downloadFileFromInfo(request.current_user, info, password)
            #headers['Transfer-Encoding'] = "chunked"
            headers['Content-Length'] = str(previewInfo.size)

            mimetype, encoding = mimetypes.guess_type(name)
            if not mimetype:
                mimetype = 'application/octet-stream'
            headers['Content-Type'] = mimetype
            if encoding:
                headers['Content-Encoding'] = encoding

            mode = "attachment" if dl else "inline"
            mode += "; filename=%s" % (json.dumps(name))
            headers['Content-Disposition'] = mode

            return Response(200, headers, callback)

            #return send_generator(go, name,
            #    file_size=None, headers=headers, attachment=dl)
        else:
            ETag = "%s:%s" % (path, str(info.version))
            if 'If-None-Match' in request.headers:
                if request.headers['If-None-Match'] == ETag:
                    return Response(304)

            _, name = service.fs.split(info.file_path)
            #stream = service.fs.open(info.storage_path, "rb")
            #if info.encryption in (CryptMode.server, CryptMode.system):
            #    if not password and info.encryption == CryptMode.server:
            #        return Response(400, {}, {"error": "Invalid Password"})
            #    stream = service.decryptStream(request.current_user,
            #        password, stream, "r", info.encryption)
            #go = files_generator_v2(stream)

            headers = {
                "X-YUE-VERSION": info.version,
                "X-YUE-PERMISSION": info.permission,
                "X-YUE-MTIME": info.mtime,
                'Cache-Control': 'max-age=31536000',
                'ETag': ETag,
                'X-YUE-ROOT': root,
                'X-YUE-PATH': path,
                'X-YUE-NAME': name,
            }

            if info.encryption in (CryptMode.server, CryptMode.system):
                if not password and info.encryption == CryptMode.server:
                    return Response(400, {}, {"error": "Invalid Password"})

            callback = service.downloadFileFromInfo(request.current_user, info, password)
            #headers['Transfer-Encoding'] = "chunked"
            headers['Content-Length'] = str(info.size)

            mimetype, encoding = mimetypes.guess_type(name)
            if not mimetype:
                mimetype = 'application/octet-stream'
            headers['Content-Type'] = mimetype
            if encoding:
                headers['Content-Encoding'] = encoding

            mode = "attachment" if dl else "inline"
            mode += "; filename=%s" % (json.dumps(name))
            headers['Content-Disposition'] = mode

            return Response(200, headers, callback)
            #return send_generator(go, name,
            #    file_size=None, headers=headers, attachment=dl)

    try:
        result = service.listDirectory(request.current_user, root, path)
        return Response(200, {}, {"result": result})
    except StorageNotFoundException as e:
        if path == "":
            obj = {
                "name": root,
                "path": "",
                "parent": "",
                "files": [],
                "directories": []
            }
            return Response(200, {}, {result: obj})

        error = "not found: root: `%s` path: `%s`" % (root, path)
        return Response(404, {}, {"error": error})

class FileSysResource(Resource):
    def __init__(self):
        super(FileSysResource, self).__init__()

        self.user_service = None
        self.filesys_service = None

    # "/api/fs"

    @get("/api/fs/:root/path/")
    @header("X-YUE-PASSWORD")
    @requires_auth("filesystem_read")
    @timed(100)
    def get_path_root(self, request):
        password = request.headers.get('X-YUE-PASSWORD', None)
        return _list_path(request, self.filesys_service,
            request.args.root, "",
            password=password, preview=None)

    @get("/api/fs/:root/path/:path*")
    @param("list", type_=Boolean().default(False).description(
        "do not retrieve contents for files if true"))
    @param("preview", type_=ImageScaleType().description(
        "return a preview picture of the resource"))
    @header("X-YUE-PASSWORD")
    @requires_auth("filesystem_read")
    @param("dl", type_=Boolean().default(True))
    @returns({200: BinaryStreamResponseOpenApiBody()})
    @timed(100)
    def get_path(self, request):
        password = request.headers.get('X-YUE-PASSWORD', None)
        return _list_path(
            request,
            self.filesys_service,
            request.args.root,
            request.args.path,
            request.query.list,
            password=password,
            preview=request.query.preview,
            dl=request.query.dl)

    @get("/api/fs/public/:fileId/:name")
    @param("dl", type_=Boolean().default(True))
    @param("info", type_=Boolean().default(False))
    @header("X-YUE-PASSWORD")
    @requires_no_auth
    def get_public_named_file(self, request):
        """
        including a file name in the url is a browser hack to download
        the file with the correct file name.
        the name is not required for any other reason

        it also allows for generating permanent links with meaningful urls
        """
        return self.get_public_file_impl(request, request.args.fileId, request.args.name)

    @get("/api/fs/public/:fileId")
    @param("dl", type_=Boolean().default(True))
    @param("info", type_=Boolean().default(False))
    @header("X-YUE-PASSWORD")
    @requires_no_auth
    def get_public_file(self, request):
        """
        return a file that has a public access file identifier.
        authentication is not required.
        the file must not be encrypted
        a password is optional. if the file requires a password it the password
        will be used to validate the download can continue
        """
        return self.get_public_file_impl(request, request.args.fileId, None)

    def get_public_file_impl(self, request, fileId, name):

        try:

            if request.query.info:
                info = self.filesys_service.publicFileInfo(fileId)
                if name is not None:
                    info['name'] = name
                return Response(200, {}, {"result": {'file': info}})
            else:
                password = request.headers.get('X-YUE-PASSWORD', None)
                info, stream = self.filesys_service.loadPublicFile(
                    fileId, password)
                go = files_generator_v2(stream)
                if name is None:
                    name = info.name
                return send_generator(go, name,
                    file_size=info.size, attachment=request.query.dl)

        except FileSysServiceException:
            return Response(401, {}, {"error": "invalid file id"})
        except StorageNotFoundException:
            return Response(404, {}, {"error": "invalid file id"})

    @put("/api/fs/public/:root/path/:path*")
    @header("X-YUE-PASSWORD")
    @param("revoke", type_=Boolean().default(False))
    @body(EmptyBodyOpenApiBody())
    @requires_auth("filesystem_write")
    def make_public(self, request):
        """

        a password is optional, if set the password will be used to validate
        downloads

        the file must exist in the given root, with the given path.
        """

        password = request.headers.get('X-YUE-PASSWORD', None)
        fileId = self.filesys_service.setFilePublic(request.current_user,
            request.args.root, request.args.path,
            password=password, revoke=request.query.revoke)

        if fileId is None:
            fileId = ""

        return Response(200, {}, {"result": {"id": fileId}})

    @get("/api/fs/:root/index")
    @param("limit", type_=Integer().min(0).max(2500).default(50))
    @param("page", type_=Integer().min(0).default(0))
    @requires_auth("filesystem_read")
    @compressed
    def get_index_root(self, request):
        """ return files owned by a user """

        offset = request.query.limit * request.query.page

        files = self.filesys_service.listIndex(request.current_user,
            request.args.root, "", limit=request.query.limit, offset=offset)

        obj = {
            "result": files,
            "page": request.query.page,
            "page_size": request.query.limit,
        }
        return Response(200, {}, obj)

    @get("/api/fs/:root/index/:resPath*")
    @param("limit", type_=Integer().min(0).max(2500).default(50))
    @param("page", type_=Integer().min(0).default(0))
    @requires_auth("filesystem_read")
    @compressed
    def get_index(self, request):
        """ return files owned by a user """

        offset = request.query.limit * request.query.page

        files = self.filesys_service.listIndex(request.current_user,
            request.args.root, request.args.resPath, limit=request.query.limit, offset=offset)

        obj = {
            "result": files,
            "page": request.query.page,
            "page_size": request.query.limit,
        }
        return Response(200, {}, obj)

    @post("/api/fs/:root/path/:resPath*")
    @param("mtime", type_=Integer().description("set file modified time"))
    @param("permission", type_=Integer().default(0o644).description("unix file permissions"))
    @param("version", type_=Integer().default(0).description("file version"))
    @param("crypt", type_=validate_mode)
    @header("X-YUE-PASSWORD")
    @body(BinaryStreamOpenApiBody())
    @requires_auth("filesystem_write")
    @timed(100)
    @returns([200, 400, 401, 409])
    def upload(self, request):
        """
        mtime: on a successful upload, set the modified time to mtime,
               unix epoch time in seconds
        version: if greater than 1, validate version

        error codes:
            409: file already exists and is a newer version
        """

        stream = request.body

        request.raw_socket.setblocking(True)

        if request.query.crypt in (CryptMode.server, CryptMode.system):
            password = request.headers.get('X-YUE-PASSWORD', None)
            stream = self.filesys_service.encryptStream(request.current_user,
                password, stream, "r", request.query.crypt)

        data = self.filesys_service.saveFile(
            request.current_user,
            request.args.root,
            request.args.resPath,
            stream,
            mtime=request.query.mtime,
            version=request.query.version,
            permission=request.query.permission,
            encryption=request.query.crypt)

        obj = {
            "result": "OK",
            "file_info": data,
        }
        return Response(200, {}, obj)

    @delete("/api/fs/:root/path/:resPath*")
    @requires_auth("filesystem_delete")
    def remove_file(self, request):
        logging.info("received delete")

        self.filesys_service.remove(request.current_user,
            request.args.root, request.args.resPath)

        return Response(200, {}, {"result": "OK"})

    @post("/api/fs/:root/move")
    @body(MoveFileOpenApiBody())
    @requires_auth("filesystem_write")
    def move_file(self, request):
        """
        move or rename a file
        """

        self.filesys_service.moveFile(request.current_user,
            request.args.root, request.body['src'], request.body['dst'])

        return Response(200, {}, {"result": "OK"})

    @get("/api/fs/:root/search")
    @param("path", type_=String().default(None))
    @param("terms", type_=String().default("").repeated())
    @param("limit", type_=Integer().min(0).max(2500).default(50))
    @param("page", type_=Integer().min(0).default(0))
    @requires_auth("filesystem_read")
    @compressed
    def search(self, request):

        limit = request.query.limit
        offset = request.query.limit * request.query.page

        records = self.filesys_service.search(
            request.current_user,
            request.args.root,
            request.query.path,
            request.query.terms,
            limit,
            offset)

        return Response(200, {}, {"result": {'files': records}})

    @get("/api/fs/roots")
    @requires_auth("filesystem_read")
    def get_roots(self, request):
        # todo this should be a list of names
        roots = self.filesys_service.getRoots(request.current_user)
        return Response(200, {}, {"result": roots})

    @get("/api/fs/quota")
    @requires_auth("filesystem_read")
    def quota(self, request):
        obj = self.filesys_service.getUserQuota(request.current_user)
        return Response(200, {}, {"result": obj})

    @put("/api/fs/change_password")
    @header("X-YUE-PASSWORD")
    @requires_auth("filesystem_write")
    @body(StringOpenApiBody(mimetype="application/octet-stream"))
    def change_password(self, request):
        """
        change the 'server' encryption key

        Note: use set_user_key to change the 'client' encryption key
        the 'system' encryption key can never be changed
        """

        password = request.headers.get('X-YUE-PASSWORD', None)
        new_password = request.body

        if not password:
            return httpError(400, "Invalid password 1")
        if not new_password:
            return httpError(400, "Invalid password 2")

        self.filesys_service.changePassword(request.current_user,
            password, new_password)

        return Response(200, {}, {"result": "OK"})

    @get("/api/fs/user_key")
    @param("mode", type_=validate_mode_client)
    @requires_auth("filesystem_write")
    def user_key(self):
        """
        return the encrypted form of the current file encryption key.

        by default return the client key,
        """
        key = self.filesys_service.getUserKey(
            request.current_user, request.query.mode)

        return Response(200, {}, {"result": {"key": key}})

    @put("/api/fs/user_key")
    @requires_auth("filesystem_write")
    @body(EncryptionKeyOpenApiBody())
    def set_user_key(self):
        """
        set the 'client' encryption key

        only the client key can be set in this way.
        the system keys cannot be changed and the server key
        can be changed via change password api
        """
        self.filesys_service.setUserClientKey(request.current_user, request.body)
        return Response(200, {}, {"result": "OK"})

    @get("/api/fs/notes")
    @param("root", type_=String().default("default"))
    @param("base", type_=String().default('public/notes'))
    @returns({200: NotesOpenApiBody()})
    @requires_auth("filesystem_read")
    def get_user_notes(self, request):
        notes = self.filesys_service.getUserNotes(
            request.current_user, request.query.root, dir_path=request.query.base)
        # return note_id => note_info
        print(notes)
        payload = {note['file_name']: note for note in notes}
        return Response(200, {}, {"result": payload})

    @post("/api/fs/notes")
    @param("root", type_=String().default("default"))
    @param("base", type_=String().default('public/notes'))
    @param("title", type_=String().required())
    @param("crypt", type_=validate_mode_system)
    @header("X-YUE-PASSWORD")
    @body(TextStreamOpenApiBody())
    @requires_auth("filesystem_write")
    def create_user_note(self, request):

        # todo return the note id / file id after saving the note

        file_name = request.query.title.replace(" ", "_") + '.txt'
        resPath = self.filesys_service.fs.join(request.query.base, file_name)

        stream = request.body
        if request.query.crypt in (CryptMode.server, CryptMode.system):
            password = request.headers.get('X-YUE-PASSWORD', None)
            stream = self.filesys_service.encryptStream(request.current_user,
                password, stream, "r", request.query.crypt)
        self.filesys_service.saveFile(
            request.current_user, request.query.root, resPath, stream,
            encryption=request.query.crypt)

        return Response(200, {}, {"result": "OK"})

    @get("/api/fs/notes/:note_id")
    @param("root", type_=String().default("default"))
    @param("base", type_=String().default('public/notes'))
    @header("X-YUE-PASSWORD")
    @requires_auth("filesystem_read")
    def get_user_note_content(self, request):
        password = request.headers.get('X-YUE-PASSWORD', None)
        resPath = self.filesys_service.fs.join(request.query.base, note_id)
        return _list_path(request, self.filesys_service, request.query.root, resPath,
            False, password=password, preview=None)


    @post("/api/fs/notes/:note_id")
    @param("root", type_=String().default("default"))
    @param("base", type_=String().default('public/notes'))
    @param("crypt", type_=validate_mode_system)
    @header("X-YUE-PASSWORD")
    @body(TextStreamOpenApiBody())
    @requires_auth("filesystem_write")
    def set_user_note_content(self, request):
        """convenience function wrapping file upload"""
        resPath = self.filesys_service.fs.join(request.query.base, note_id)

        stream = request.body
        if request.query.crypt in (CryptMode.server, CryptMode.system):
            password = request.headers.get('X-YUE-PASSWORD', None)
            stream = self.filesys_service.encryptStream(request.current_user,
                password, stream, "r", request.query.crypt)
        self.filesys_service.saveFile(
            request.current_user, request.query.root, resPath, stream,
            encryption=request.query.crypt)

        return Response(200, {}, {"result": "OK"})

    @delete("/api/fs/notes/:note_id")
    @param("root", type_=String().default("default"))
    @param("base", type_=String().default('public/notes'))
    @requires_auth("filesystem_write")
    def delete_user_note(self, note_id):
        """convenience function wrapping file delete"""
        resPath = self.filesys_service.fs.join(request.query.base, note_id)
        self.filesys_service.remove(request.current_user, request.query.root, resPath)
        return Response(200, {}, {"result": "OK"})

    @post("/.speedtest")
    @body(BinaryStreamOpenApiBody())
    @requires_auth()
    @returns([200, 400, 401, 409])
    @timed(100)
    def speedtest_upload(self, request):
        stream = None

        total_size = 0
        t0 = time.time()
        buf = request.body.read(2048)
        while buf:
            total_size += len(buf)
            buf = request.body.read(2048)
        t1 = time.time()

        duration = (t1-t0)
        res = {
            "result": "OK",
            "total_size": total_size,
            "duration": duration,
            "rate": 0 if duration == 0 else total_size / duration
        }
        return Response(200, {}, res)

    @get("/.speedtest/:count/:size")
    @requires_auth()
    def speedtest_download(self, request):

        count = int_range(1, 2**8)(request.args.count)
        size  = int_range(2, 2**16)(request.args.size)
        total_size = int_range(2, 2**20)(count * size)
        mimetype = "application/octect-stream"

        go = speedtest_gen(count, size)

        headers = {
            'Content-Length': total_size,
            'Content-Type': "application/octect-stream",
        }

        return Response(200, headers, go)


