
"""
The File System Service exposes sand boxed parts of the file systems.

A directory mapping is used to map a common name to a location on the
file system. The location can either be local, an s3 path, or an in-memory
file system.

"""
import os, sys

from .exception import FileSysServiceException
from ..dao.filesys.filesys import FileSystem
from ..dao.filesys.crypt import FileEncryptorWriter, FileEncryptorReader, \
    FileDecryptorReader, FileDecryptorWriter, decryptkey
from ..dao.storage import StorageDao, \
    StorageNotFoundException, StorageException, CryptMode
from ..dao.user import UserDao
from ..dao.settings import Settings, SettingsDao

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
        record = self.storageDao.file_info(user['id'], abs_path)
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

        record = self.storageDao.file_info(user['id'], abs_path)

        files = []
        dirs = []

        if record.isDir:
            dirs.append(record.name)
        else:
            files.append({"name": record.name,
                          "size": record.size,
                          "mtime": record.mtime,
                          "permission": record.permission,
                          "version": record.version})

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

        records = self.storageDao.listdir(user['id'], abs_path)

        for record in records:
            #pathname = self.fs.join(abs_path, record.name)

            if record.isDir:
                dirs.append(record.name)
            else:
                files.append({"name": record.name,
                              "size": record.size,
                              "mtime": record.mtime,
                              "permission": record.permission,
                              "version": record.version})

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

        files = list(self.storageDao.listall(user['id'], abs_path,
            limit=limit, offset=offset))

        return files

    def saveFile(self, user, fs_name, path, stream,
      mtime=None, version=0, permission=0, encryption=None):

        # TODO: support an encryption mode (client / server / sytem / None)
        if self.fs.isabs(path):
            raise FileSysServiceException(path)

        os_root = '/'

        storage_path = self._getNewStoragePath(user, fs_name, path)
        file_path = self.getFilePath(user, fs_name, path)

        dirpath, _ = self.fs.split(storage_path)
        self.fs.makedirs(dirpath)

        # the sync tool depends on an up-to-date local database
        # when uploading, the client knows what the next version of a file
        # will be. If the expected version is lower than reality (because
        # fetch needs to be run) reject the file. running a fetch
        # will likely reveal this file is in a conflict state
        if version > 0:
            try:
                info = self.storageDao.file_info(user['id'], file_path)
                if info.version >= version:
                    raise FileSysServiceException("invalid version", 409)
            except StorageNotFoundException as e:
                pass
        else:
            # dao layer expects None, or a valid version
            version = None

        size = 0
        with self.fs.open(storage_path, "wb") as wb:
            for buf in iter(lambda: stream.read(2048), b""):
                wb.write(buf)
                size += len(buf)

        # if the file is wrapped by an encryptor, subtract the size
        # of the header information. This allows the user to stat
        # the file later on, and see the expected file size
        # TODO: should this be conditioned off encryption mode?
        # if isinstance(stream, FileEncryptorReader):
        if encryption is not None:
            size -= FileEncryptorReader.HEADER_SIZE

        if mtime is None:
            mtime = int(time.time())

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

        self.storageDao.upsertFile(user['id'], file_path, data)

    def remove(self, user, fs_name, path):

        if self.fs.isabs(path):
            raise FileSysServiceException("unexpected absolute path: %s" % path)

        file_path = self.getFilePath(user, fs_name, path)

        # remote by storage path, by selecting by user_id and path
        # then remove by user_id and path
        try:
            # TODO: either both succeed or neither...
            record = self.storageDao.file_info(user['id'], file_path)
            self.storageDao.removeFile(user['id'], file_path)
            result = self.fs.remove(record.storage_path)
            return result
        except FileNotFoundError as e:
            raise e
        except Exception as e:
            logging.exception("unable to delete: %s" % path)

        raise FileSysServiceException(path)

    def getUserQuota(self, user):

        nfiles, nbytes = self.storageDao.userDiskUsage(user['id'])
        quota = self.storageDao.userDiskQuota(user['id'])

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
        raise FileSysServiceException("key not found")

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

        if mode == "r":
            # encrypt the contents as the file is read
            return FileEncryptorReader(stream, key)
        elif mode == "w":
            # encrypt the contents as they are written to the file
            return FileEncryptorWriter(stream, key)
        else:
            raise FileSysServiceException("invalid mode: '%s'" % mode)

    def decryptStream(self, user, password, stream, mode, crypt_mode):
        """
        returns a file-like object wrapping stream
        contents are decrypted as they are read from the stream
        """
        print(password, mode, crypt_mode)
        if crypt_mode == CryptMode.server:
            key = self.storageDao.getEncryptionKey(
                user['id'], password, crypt_mode)
        elif crypt_mode == CryptMode.system:
            key = self.getUserSystemPassword(user)
        else:
            raise FileSysServiceException("invalid mode: '%s'" % crypt_mode)

        if mode == "r":
            # decrypt the contents as the file is read
            return FileDecryptorReader(stream, key)
        elif mode == "w":
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

    def verifyPublicPassword(self, public_id, password):

        if not self.storageDao.verifyPublicPassword(public_id, password):
            raise FileSysServiceException("invalid password")
        return

    def publicFileInfo(self, public_id):
        return self.storageDao.publicFileInfo(public_id)

