
"""
The File System Service exposes sand boxed parts of the file systems.

A directory mapping is used to map a common name to a location on the
file system. The location can either be local, an s3 path, or an in-memory
file system.

"""
import os, sys


from .exception import FileSysServiceException
from ..dao.filesys.filesys import FileSystem
from ..dao.storage import StorageDao
from ..dao.user import UserDao

import logging

from unicodedata import normalize

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

    def getPath(self, user, fs_name, path):
        """
        returns an absolute file path given the name of a
        file system (which determines the base directory) and a path.
        the path is guaranteed to be a sub directory of the named fs.
        """

        return self.storageDao.absolutePath(user['id'], user['role_id'], \
            fs_name, path)

    def listSingleFile(self, user, fs_name, path):

        os_root = self.getRootPath(user, fs_name)
        abs_path = self.getPath(user, fs_name, path)

        if abs_path == os_root:
            parent = os_root
        else:
            parent, _ = self.fs.split(abs_path)

        name, is_dir, size, mtime = self.fs.file_info(abs_path)

        files = []
        dirs = []

        if is_dir:
            dirs.append(name)
        else:
            files.append({"name": name, "size": size, "mtime": mtime})

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

        os_root = self.getRootPath(user, fs_name)
        abs_path = self.getPath(user, fs_name, path)

        if abs_path == os_root:
            parent = os_root
        else:
            parent, _ = self.fs.split(abs_path)

        files = []
        dirs = []

        for name, is_dir, size, mtime in self.fs.scandir(abs_path):
            pathname = self.fs.join(abs_path, name)

            if is_dir:
                dirs.append(name)
            else:
                files.append({"name": name, "size": size, "mtime": mtime})

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

    def saveFile(self, user, fs_name, path, stream, mtime=None):

        path = self.getPath(user, fs_name, path)

        logging.info("saving: %s" % path)
        dirpath, _ = self.fs.split(path)
        self.fs.makedirs(dirpath)

        with self.fs.open(path, "wb") as wb:
            buf = stream.read(2048)
            while buf:
                wb.write(buf)
                buf = stream.read(2048)

        if mtime is not None:
            self.fs.set_mtime(path, mtime)

    def remove(self, user, fs_name, path):

        path = self.getPath(user, fs_name, path)

        try:
            return self.fs.remove(path)
        except FileNotFoundError as e:
            raise e
        except Exception as e:
            logging.exception("unable to delete: %s" % path)

        raise FileSysServiceException(path)
