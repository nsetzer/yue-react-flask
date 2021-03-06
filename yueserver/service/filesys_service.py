
"""
The File System Service exposes sand boxed parts of the file systems.

A directory mapping is used to map a common name to a location on the
file system. The location can either be local, an s3 path, or an in-memory
file system.

"""
import os, sys

from .exception import FileSysServiceException, FileSysKeyNotFound
from ..dao.filesys.filesys import FileSystem
from ..dao.filesys.crypt import FileEncryptorWriter, FileEncryptorReader, \
    FileDecryptorReader, FileDecryptorWriter, decryptkey
from ..dao.storage import StorageDao, \
    StorageNotFoundException, StorageException, CryptMode
from ..dao.user import UserDao
from ..dao.settings import Settings, SettingsDao
from ..dao.image import ImageScale, scale_image_stream
from .transcode_service import TranscodeService, ImageScale
from ..dao.util import format_bytes
from ..dao.transcode import FFmpeg

from datetime import datetime

import logging
import time
import base64
import uuid

# TODO: validate fs_name and path since those values come from a user
#       use the same validation as storage path,
#       but path should return a relative path instead

def trim_path(p, root):
    # todo, this seems problematic, and I think I have several
    # implementations throughout the source code. unify the implementations
    # under the file system api.
    p = p.replace("\\", "/")
    if p.startswith(root):
        p = p[len(root):]
    while p.startswith("/"):
        p = p[1:]
    return p

class FileSysService(object):
    """docstring for FileSysService"""

    _instance = None

    def __init__(self, config, db, dbtables):
        super(FileSysService, self).__init__()
        self.config = config
        self.db = db
        self.dbtables = dbtables
        self.storageDao = StorageDao(db, dbtables)
        self.userDao = UserDao(db, dbtables)
        self.settingsDao = SettingsDao(db, dbtables)

        self.fs = FileSystem()

        # tuning parameter controlling how often the
        # db is accessed during file upload
        # 2**20 : 1 MB
        # 2**26 : 64 MB
        self.byte_threshold = 2**26

        path = config.transcode.audio.bin_path

        if path and not os.path.exists(path):
            raise FileNotFoundError(path)

        self.transcoder = FFmpeg(path)

    @staticmethod
    def init(config, db, dbtables):
        if not FileSysService._instance:
            FileSysService._instance = FileSysService(config, db, dbtables)
        return FileSysService._instance

    @staticmethod
    def instance():
        return FileSysService._instance

    def getRoots(self, user):
        return [f.name for f in self.userDao.listAllFileSystemsForRole(user['role_id'])]

    def getRootPath(self, user, fs_name):
        return self.storageDao.rootPath(user['id'], user['role_id'], fs_name)

    def _getNewStoragePath(self, user, fs_name, path):
        """
        user: the current user
        fs_name: name for the file system root to use
        path: a relative path

        returns an absolute file path given the name of a
        file system (which determines the base directory) and a path.
        the path is guaranteed to be a sub directory of the named fs.
        """

        part1 = datetime.now().strftime("%Y/%m/%d")
        # create a unique alpha-numerix name for this file
        part2 = base64.b64encode(uuid.uuid4().bytes, b"-_") \
            .replace(b"=", b"") \
            .replace(b"-", b"AA") \
            .replace(b"_", b"AB") \
            .decode("utf-8")
        rel_path = "%s/%s" % (part1, part2)

        # get the unique absolute path

        return self.storageDao.absolutePath(user['id'], user['role_id'],
            fs_name, rel_path)

    def getFilePath(self, user, fs_name, path):
        return self.storageDao.absoluteFilePath(user['id'], user['role_id'],
            path)

    def getStoragePath(self, user, fs_name, path):
        abs_path = self.getFilePath(user, fs_name, path)
        fs_id = self.storageDao.getFilesystemId(
            user['id'], user['role_id'], fs_name)
        record = self.storageDao.file_info(user['id'], fs_id, abs_path)
        return record.storage_path

    def listSingleFile(self, user, fs_name, path):

        if self.fs.isabs(path):
            raise FileSysServiceException(path)

        os_root = '/'
        abs_path = self.getFilePath(user, fs_name, path)

        if abs_path == os_root:
            parent = os_root
        else:
            parent, _ = self.fs.split(abs_path)

        fs_id = self.storageDao.getFilesystemId(
            user['id'], user['role_id'], fs_name)

        record = self.storageDao.file_info(user['id'], fs_id, abs_path)

        files = []
        dirs = []

        if record.isDir:
            dirs.append(record.name)
        else:
            files.append({"name": record.name,
                          "size": record.size,
                          "mtime": record.mtime,
                          "permission": record.permission,
                          "version": record.version,
                          "public": record.public,
                          "encryption": record.encryption})

        os_root_normalized = os_root.replace("\\", "/")

        result = {
            # name is the name of the file system, which
            # is used to determine the media root
            "name": fs_name,
            # return the relative path, suitable for the request url
            # that would reproduce this result
            "path": trim_path(path, os_root_normalized),
            # return the relative path to the parent, suitable to produce
            # a directory listing on the parent
            "parent": trim_path(parent, os_root_normalized),
            # return the list of files as a dictionary
            "files": files,
            # return the names of all sub directories
            "directories": dirs
        }

        return result

    def listDirectory(self, user, fs_name, path):
        """
        todo: check for .yueignore in the root, or in the given path
        use to load filters to remove elements from the response
        """

        if self.fs.isabs(path):
            raise FileSysServiceException(path)

        os_root = '/'
        abs_path = self.getFilePath(user, fs_name, path)

        if abs_path == os_root:
            parent = os_root
        else:
            parent, _ = self.fs.split(abs_path)

        if not abs_path.endswith("/"):
            abs_path += "/"

        files = []
        dirs = []

        # TODO: there is a bug here related to fs roots
        # this will list all files across all roots
        # migrate: add column to storage table 'root' name
        fs_id = self.storageDao.getFilesystemId(
            user['id'], user['role_id'], fs_name)

        records = self.storageDao.listdir(user['id'], fs_id, abs_path)

        for record in records:
            #pathname = self.fs.join(abs_path, record.name)

            if record.isDir:
                dirs.append(record.name)
            else:
                files.append({"name": record.name,
                              "size": record.size,
                              "mtime": record.mtime,
                              "permission": record.permission,
                              "version": record.version,
                              "public": record.public,
                              "encryption": record.encryption})

        files.sort(key=lambda f: f['name'])
        dirs.sort()

        os_root_normalized = os_root.replace("\\", "/")

        result = {
            # name is the name of the file system, which
            # is used to determine the media root
            "name": fs_name,
            # return the relative path, suitable for the request url
            # that would reproduce this result
            "path": trim_path(path, os_root_normalized),
            # return the relative path to the parent, suitable to produce
            # a directory listing on the parent
            "parent": trim_path(parent, os_root_normalized),
            # return the list of files as a dictionary
            "files": files,
            # return the names of all sub directories
            "directories": dirs
        }

        return result

    def listIndex(self, user, fs_name, path, limit=None, offset=None):

        """
        list all files, including files in a subdirectory, owned by a user
        """

        if self.fs.isabs(path):
            raise FileSysServiceException(path)

        if path:
            abs_path = "/%s/" % path
        else:
            abs_path = "/"

        fs_id = self.storageDao.getFilesystemId(
            user['id'], user['role_id'], fs_name)

        files = list(self.storageDao.listall(user['id'], fs_id, abs_path,
            limit=limit, offset=offset))

        return files

    def loadFile(self, user, fs_name, path, password=None):

        abs_path = self.getFilePath(user, fs_name, path)
        fs_id = self.storageDao.getFilesystemId(
            user['id'], user['role_id'], fs_name)
        info = self.storageDao.file_info(user['id'], fs_id, abs_path)
        return self.loadFileFromInfo(user, info, password)

    def loadFileFromInfo(self, user, info, password=None):

        stream = self.fs.open(info.storage_path, "rb")

        if info.encryption is not None:
            stream = self.decryptStream(user, password,
                stream, "rb", info.encryption)

        return stream

    def downloadFileFromInfo(self, user, info, password=None):

        #abs_path = self.getFilePath(user, fs_name, path)
        #fs_id = self.storageDao.getFilesystemId(
        #    user['id'], user['role_id'], fs_name)
        #info = self.storageDao.file_info(user['id'], fs_id, abs_path)

        def downloadCallback(writer):

            if info.encryption is not None:
                writer = self.decryptStream(user, password,
                    writer, "wb", info.encryption)

            self.fs.download(info.storage_path, writer)

        return downloadCallback

    def publicFileInfo(self, fileId):
        record = self.storageDao.publicFileInfo(fileId)

        obj = {
            "name": record.name,
            "size": record.size,
            "mtime": record.mtime,
            "permission": record.permission,
            "version": record.version,
            "public": record.public,
            "encryption": record.encryption
        }

        return obj

    def loadPublicFile(self, fileId, password=None):

        # validate that the given password is correct
        # authenticating that the download can continue
        if not self.storageDao.verifyPublicPassword(fileId, password):
            raise FileSysServiceException("invalid password")

        # look up the storage path by id, open the file
        info = self.storageDao.publicFileInfo(fileId)
        stream = self.fs.open(info.storage_path, "rb")

        # decrypt the file using the file owner's system key
        # server and client encryption modes are not possible
        if info.encryption == CryptMode.system:
            password = self.settingsDao.get(
                Settings.storage_system_key)
            key = self.storageDao.getUserKey(
                info.user_id, CryptMode.system)
            key = decryptkey(password, key)
            stream = FileDecryptorReader(stream, key)

        return info, stream

    # TODO: version defaulting to 0 may be a bug, change to None
    def saveFile(self, user, fs_name, path, stream,
      mtime=None, version=None, permission=0, encryption=None):

        if self.fs.isabs(path):
            raise FileSysServiceException(path)

        fs_id = self.storageDao.getFilesystemId(
            user['id'], user['role_id'], fs_name)

        os_root = '/'

        file_path = self.getFilePath(user, fs_name, path)

        # the sync tool depends on an up-to-date local database
        # when uploading, the client knows what the next version of a file
        # will be. If the expected version is lower than reality (because
        # fetch needs to be run) reject the file. running a fetch
        # will likely reveal this file is in a conflict state

        info = None
        storage_path = None

        try:
            info = self.storageDao.file_info(user['id'], fs_id, file_path)
            storage_path = info.storage_path
        except StorageNotFoundException as e:
            pass


        # the new logic here avoids letting the dao layer decide
        if info is not None:
            # if the incoming version is lower than or equal to the
            # current version, reject the upload, otherwise take the
            # highest version number, and increment if necessary
            if not version:
                version = info.version + 1

            elif version <= info.version:
                raise FileSysServiceException(
                    "Version out of date (%d < %d)" % (version, info.version), 409)


        elif not version:
            # this is the first version
            version = 1

        if storage_path is None:
            storage_path = self._getNewStoragePath(user, fs_name, path)
            dirpath, _ = self.fs.split(storage_path)
            self.fs.makedirs(dirpath)
            logging.warning("creating new storage path: %s", storage_path)

        if mtime is None:
            mtime = int(time.time())

        size = self._internalSave(user['id'], storage_path, stream, 4096)

        # if the file is wrapped by an encryptor, subtract the size
        # of the header information. This allows the user to stat
        # the file later on, and see the expected file size

        if encryption is not None:
            size -= FileEncryptorReader.HEADER_SIZE

        # todo: in the future, the logical file path, and the actual
        # storage path will be different for security reasons.
        data = dict(
            storage_path=storage_path,
            preview_path=None,
            permission=permission,
            version=version,
            size=size,
            mtime=mtime,
            encryption=encryption
        )

        file_id = self.storageDao.upsertFile(
            user['id'], fs_id, file_path, data)
        # existing thumbnails need to be recomputed
        self.storageDao.previewInvalidate(user['id'], file_id)

        # TODO: is it possible to return the new version ?
        #       it is either info.version+1 or version or 1
        file_info = dict(
            size=size,
            mtime=mtime,
            encryption=encryption,
            permission=permission,
            version=version,
        )

        return file_info

    def _internalSave(self, user_id, storage_path, inputStream, chunk_size):

        # QUOTA upload strategy
        # don't check the quota at the start.
        # every N bytes (N= 50MB or 100MB) check the usage + transfered
        # compared to the quota. if over, abandon upload delete file.
        # on error return http 413 Request To Large
        # note: parallel uploads can allow going over the quota
        #       create a locked structure, a dictionary
        #           user_id => storage_path => transfered bytes
        #       update this structure then sum transfered bytes and
        #       compare to the quota. and fail the current upload if need be
        #       create a per user lock?

        uid = str(uuid.uuid4())

        quota_enabled = False

        if quota_enabled:

            _, usage, quota = self.storageDao.userDiskUsage(user_id)

            if usage > quota:
                raise FileSysServiceException("quota exceeded", 413)

        byte_index = 0
        size = 0


        try:
            # inputStream -> setNonBlocking(True) ? where?

            size = self.fs.upload(inputStream, storage_path)
            #with self.fs.open(storage_path, "wb") as outputStream:
            #    _iter = iter(lambda: inputStream.read(chunk_size), b"")
            #    cont = True;
            #    while cont:
            #        data = b""
            #        try:
            #            # load X megabytes before attempting to write
            #            # to the output file
            #            for i in range(1000):
            #                data += next(_iter)
            #        except StopIteration as e:
            #            cont = False
            #        if data:
            #            outputStream.write(data)
            #            size += len(data)
            #            if quota_enabled:
            #                byte_index = self._internalCheckQuota(
            #                    user_id, size, byte_index, uid)

            if quota_enabled:
                self._internalCheckQuota(
                    user_id, size, -1, uid)

        except Exception as e:
            logging.exception("upload failed. removing failed file at location: %s", storage_path)
            self.fs.remove(storage_path)
            raise e
        finally:
            if quota_enabled:
                logging.info("removing temp file. size: %d", size)
                self.storageDao.tempFileRemove(user_id, uid)


        return size

    def _internalCheckQuota(self, user_id, size, byte_index, uid):

        # TODO: one minor bug related to upload and quota
        # replacing a large file, with a smaller version could
        # trip the quota, and delete the original
        # its overwriting anyway, so any failed request would have
        # meant data loss.

        index = size // self.byte_threshold
        if byte_index == -1 or index > byte_index:
            self.storageDao.tempFileUpdate(user_id, uid, size)
            _, temp_usage = self.storageDao.tempFileUsage(user_id)
            _, usage, quota = self.storageDao.userDiskUsage(user_id)

            #print("%s + %s = %s > %s : %s" % (
            #    format_bytes(usage), format_bytes(temp_usage),
            #    format_bytes(temp_usage + usage), format_bytes(quota),
            #    (temp_usage + usage) > quota))

            if (temp_usage + usage) > quota:
                raise FileSysServiceException("quota exceeded", 413)

            byte_index += 1

        return byte_index

    def remove(self, user, fs_name, path):

        logging.warning("remove: is abs %s %s", fs_name, path)
        if self.fs.isabs(path):
            raise FileSysServiceException("unexpected absolute path: %s" % path)

        logging.warning("remove: get path")
        file_path = self.getFilePath(user, fs_name, path)
        logging.warning("remove: get path %s", file_path)

        fs_id = self.storageDao.getFilesystemId(
            user['id'], user['role_id'], fs_name)
        logging.warning("remove: fs_id %s", fs_id)

        # remote by storage path, by selecting by user_id and path
        # then remove by user_id and path
        try:
            # TODO: FS remove first, then if it fails
            #   404: remove from db anyway
            #   remove failed: ???
            logging.warning("remove: get info")
            record = self.storageDao.file_info(user['id'], fs_id, file_path)
            logging.warning("remove: remove preview")
            self._removePreviewFiles(user['id'], fs_id, file_path)
            logging.warning("remove: remove fs entry")
            result = self.fs.remove(record.storage_path)
            logging.warning("remove: remove dao entry")
            self.storageDao.removeFile(user['id'], fs_id, file_path)
            return result
        except FileNotFoundError as e:
            logging.warning("remove failed: file not found")
            raise e
        except Exception as e:
            logging.exception("unable to delete: %s" % path)

        raise FileSysServiceException(path)

    def moveFile(self, user, fs_name, srcPath, dstPath):
        """
        move a file from src to dst
        dst cannot exist
        dst cannot be a partial path of an existing file

        if /abc/def/123 exists
            /abc/def      -- invalid
            /abc/de       -- valid
            /abc/de/123   -- valid
        """
        fs_id = self.storageDao.getFilesystemId(
            user['id'], user['role_id'], fs_name)

        src = self.getFilePath(user, fs_name, srcPath.lstrip('/'))
        dst = self.getFilePath(user, fs_name, dstPath.lstrip('/'))
        return self.storageDao.moveFileLocation(user['id'], fs_id, src, dst)

    def search(self, user, fs_name, fs_path, terms, limit=None, offset=None):
        """
        fs_name: the file system root to search
        fs_path: path prefix or None
        name_parts: a list of file names or partial file names to search for
        """

        fs_id = self.storageDao.getFilesystemId(
            user['id'], user['role_id'], fs_name)

        if fs_path:
            os_root = '/'
            abs_path = self.getFilePath(user, fs_name, fs_path)

            if abs_path == os_root:
                parent = os_root
            else:
                parent, _ = self.fs.split(abs_path)

            if not abs_path.endswith("/"):
                abs_path += "/"
        else:
            abs_path = ""

        records = self.storageDao.search(
            user['id'], fs_id, abs_path, terms, limit, offset)

        files = []
        for record in records:
            files.append({"name": record.name,
                          "file_path": record.file_path[1:],
                          "size": record.size,
                          "mtime": record.mtime,
                          "permission": record.permission,
                          "version": record.version,
                          "public": record.public,
                          "encryption": record.encryption})

        return files

    def getUserQuota(self, user):

        nfiles, nbytes, quota = self.storageDao.userDiskUsage(user['id'])

        obj = {
            "nfiles": nfiles,
            "nbytes": nbytes,
            "quota": quota,
        }
        return obj

    def changePassword(self, user, password, new_password):
        """
        change the password used for file encryption

        the only password that can be changed using this method
        is the 'server' encryption key
        """

        self.storageDao.changePassword(user['id'], password, new_password)

    def getUserSystemPassword(self, user):
        password = self.settingsDao.get(Settings.storage_system_key)

        try:
            # get the system key if it exists
            key = self.storageDao.getUserKey(user['id'], CryptMode.system)
        except StorageException as e:
            # create the system key if it does not exist
            key = self.storageDao.changePassword(
                user['id'], password, password, CryptMode.system)

        # decrypt the key
        return decryptkey(password, key)

    def getUserKey(self, user, mode):
        try:
            return self.storageDao.getUserKey(user['id'], mode)
        except StorageException as e:
            pass
        raise FileSysKeyNotFound("key not found")

    def setUserClientKey(self, user, key):
        self.storageDao.setUserKey(user['id'], key, CryptMode.client)

    def encryptStream(self, user, password, stream, mode, crypt_mode):
        """
        returns a file-like object wrapping stream
        contents are encrypted as they are written to the stream
        """

        if crypt_mode == CryptMode.server:
            key = self.storageDao.getEncryptionKey(
                user['id'], password, crypt_mode)
        elif crypt_mode == CryptMode.system:
            key = self.getUserSystemPassword(user)
        else:
            raise FileSysServiceException("invalid mode: '%s'" % crypt_mode)

        if mode.startswith("r"):
            # encrypt the contents as the file is read
            return FileEncryptorReader(stream, key)
        elif mode.startswith("w"):
            # encrypt the contents as they are written to the file
            return FileEncryptorWriter(stream, key)
        else:
            raise FileSysServiceException("invalid mode: '%s'" % mode)

    def decryptStream(self, user, password, stream, mode, crypt_mode):
        """
        returns a file-like object wrapping stream
        contents are decrypted as they are read from the stream
        """
        if crypt_mode == CryptMode.server:
            key = self.storageDao.getEncryptionKey(
                user['id'], password, crypt_mode)
        elif crypt_mode == CryptMode.system:
            key = self.getUserSystemPassword(user)
        else:
            raise FileSysServiceException("invalid mode: '%s'" % crypt_mode)

        if mode.startswith("r"):
            # decrypt the contents as the file is read
            return FileDecryptorReader(stream, key)
        elif mode.startswith("w"):
            # decrypt the contents as the file is being written
            return FileDecryptorWriter(stream, key)
        else:
            raise FileSysServiceException("invalid mode: '%s'" % mode)

        # todo: consider the option of password protected files
        # which are publicly available, require a password to download
        # but are also not encrypted.

    def setFilePublic(self, user, fs_name, path, password=None, revoke=False):

        abs_path = self.getFilePath(user, fs_name, path)
        return self.storageDao.setFilePublic(
            user['id'], abs_path, password=password, revoke=revoke)

    def getUserNotes(self, user, fs_name, dir_path="public/notes"):
        """
        return the list of public notes

        Notes are text files which can be edited using the gui.
        They are stored on the file system, so can be synced between devices.
        By default they are stored in the public directory, so can be shared.
        """

        abs_path = self.getFilePath(user, fs_name, dir_path)
        if not abs_path.endswith("/"):
            abs_path += "/"
        fs_id = self.storageDao.getFilesystemId(
            user['id'], user['role_id'], fs_name)

        try:
            records = self.storageDao.listdir(user['id'], fs_id, abs_path)

            files = []
            for record in records:
                if not record.isDir:
                    if record.name.endswith('.txt'):
                        # TODO: add the file id as a uid for the note
                        #       allow renaming notes by uid
                        #       add endpoint for creating note
                        files.append({
                            "file_name": record.name,
                            "title": record.name[:-4].replace("_", " "),
                            "file_path": "%s/%s" % (dir_path, record.name),
                            "size": record.size,
                            "mtime": record.mtime,
                            "encryption": record.encryption,
                        })

        except StorageNotFoundException as e:
            return []

        return files

    def previewFile(self, user, fs_name, path, scale, password=None):

        abs_path = self.getFilePath(user, fs_name, path)
        ext1 = abs_path.split('.')[-1].lower()
        if ext1 not in {"jpg", "jpeg", "png", "gif", 'bmp', "webm", "mp4"}:
            return None

        fs_id = self.storageDao.getFilesystemId(
            user['id'], user['role_id'], fs_name)
        fileItem = self.storageDao.file_info(user['id'], fs_id, abs_path)
        ext = fileItem.file_path.split('.')[-1].lower()

        name = ImageScale.name(scale)

        previewItem = self.storageDao.previewFind(
            user['id'], fileItem.file_id, name)

        if previewItem and previewItem.path.startswith("err://"):
            return None

        elif previewItem is None or previewItem.valid == 0 or not self.fs.exists(previewItem.path):
            inputStream = self.loadFileFromInfo(user, fileItem, password)
            # look for a preview file that already exists
            # check a database table, not the file system
            # if it exists return the table entry

            # generate a new file path for the preview file.
            # other than possibly a similar date, there is no relationship
            # to the preview image file and source file found in the storage
            # area. this may help to avoid revealing the type of
            # an encrypted file
            dst = self._getNewStoragePath(user, fs_name, path)

            try:
                logging.info("creating preview %s %s" % (name, dst))
                if fileItem.encryption in (CryptMode.server, CryptMode.client):
                    raise FileSysServiceException("file is encrypted")
                elif ext in {"jpg", "jpeg", "png", "gif", 'bmp'}:

                    with self.fs.open(dst, "wb") as outputStream:
                        if fileItem.encryption is not None:
                            outputStream = self.encryptStream(user,
                                password, outputStream, "w", fileItem.encryption)
                        w, h, s = scale_image_stream(inputStream, outputStream, scale)

                        info = {
                            'width': w,
                            'height': h,
                            'filesystem_id': fs_id,
                            'size': s,
                            'path': dst,
                            'valid': 1
                        }

                        self.storageDao.previewUpsert(
                            user['id'], fileItem.file_id, name, info)
                elif ext in {"ogg", "mp3", "wav"}:

                    raise FileSysServiceException("not implemented")
                elif ext in {"webm", "mp4"}:
                    with self.fs.open(dst, "wb") as outputStream:
                        if fileItem.encryption is not None:
                            outputStream = self.encryptStream(user,
                                password, outputStream, "w", fileItem.encryption)
                        args = self.transcoder.get_thumb_args()
                        w, h, s = self.transcoder.thumb(inputStream, outputStream, args, scale)

                        info = {
                            'width': w,
                            'height': h,
                            'filesystem_id': fs_id,
                            'size': s,
                            'path': dst,
                            'valid': 1
                        }

                        self.storageDao.previewUpsert(
                            user['id'], fileItem.file_id, name, info)
                elif ext in ("pdf", "swf"):

                    raise FileSysServiceException("not implemented")
                else:
                    raise FileSysServiceException("not implemented")

                # the resource path that is returned should be resource
                # dependant. all audio files should have the same url
                #
                return dst
            except Exception as e:

                info = {
                    'width': 0,
                    'height': 0,
                    'filesystem_id': fs_id,
                    'size': 0,
                    'path': "err://transcode",
                    'valid': 1
                }

                self.storageDao.previewUpsert(
                    user['id'], fileItem.file_id, name, info)

                logging.error("Failed to generate preview for %s `%s`" % (fs_name, abs_path))
                return None

        else:
            return previewItem

    def _removePreviewFiles(self, user_id, fs_id, file_path):
        # TODO: exception handling, eventual consistency
        fileItem = self.storageDao.file_info(user_id, fs_id, file_path)
        file_id = fileItem.file_id
        self.storageDao.previewInvalidate(user_id, file_id)
        for item in self.storageDao.previewFind(user_id, file_id, None):
            self.fs.remove(item.path)
        self.storageDao.previewRemove(user_id, file_id)