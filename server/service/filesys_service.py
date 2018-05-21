
import os, sys

from stat import S_ISDIR, S_ISREG, S_IRGRP
from .util import FileSysServiceException, FFmpegEncoder

import logging

from unicodedata import normalize

# taken from werkzeug.util.secure_file
_windows_device_files = ('CON', 'AUX', 'COM1', 'COM2', 'COM3', 'COM4', 'LPT1',
                         'LPT2', 'LPT3', 'PRN', 'NUL')

class FileSysService(object):
    """docstring for FileSysService"""

    _instance = None

    def __init__(self, config, db, dbtables):
        super(FileSysService, self).__init__()
        self.config = config
        self.db = db
        self.dbtables = dbtables

    @staticmethod
    def init(config, db, dbtables):
        if not FileSysService._instance:
            FileSysService._instance = FileSysService(config, db, dbtables)
        return FileSysService._instance

    @staticmethod
    def instance():
        return FileSysService._instance

    def getRoots(self, user):
        roots = ["default"]
        for k in self.config.filesystem.other.keys():
            roots.append(k)
        return sorted(roots)

    def getRootPath(self, user, fs_name):

        if fs_name == "default":
            return self.config.filesystem.media_root
        elif fs_name in self.config.filesystem.other:
            return self.config.filesystem.other[fs_name]

        raise FileSysServiceException(user, "invalid name: `%s`" % fs_name)

    def getPath(self, user, fs_name, path):
        """
        returns a (possibly relative) file path given the name of a
        file system (which determines the base directory) and a path.
        the path is guaranteed to be a sub directory of the named fs.
        """

        os_root = self.getRootPath(user, fs_name)

        path = normalize('NFKD', path)

        if not path.strip():
            return os_root

        if os.path.isabs(path):
            raise FileSysServiceException(user, "path must not be absolute")

        parts = path.replace("\\", "/").split("/")
        if any([p in (".", "..") for p in parts]):
            # path must be relative to os_root...
            raise FileSysServiceException(user, "relative paths not allowed")

        if any([ (not p.strip()) for p in parts]):
            raise FileSysServiceException(user, "empty path component")

        if os.name == 'nt':
            if any([p in _windows_device_files for p in parts]):
                raise FileSysServiceException(user, "invalid windows path name")

        # todo: this does not provide the strong guarantee expected.
        # todo: this should always return an absolute path
        abs_path = os.path.abspath(os.path.join(os_root, path))

        #if not parent.startswith(os_root):
        #    parent = os_root

        return abs_path

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
            parent, _ = os.path.split(abs_path)

        files = []
        dirs = []
        for name in os.listdir(abs_path):
            pathname = os.path.join(abs_path, name)
            st = os.stat(pathname)
            mode = st.st_mode

            if not (mode & S_IRGRP):
                continue

            if S_ISDIR(mode):
                dirs.append(name)
            elif S_ISREG(mode):
                files.append({"name": name,
                              "size": st.st_size,
                              "mtime": int(st.st_mtime)})

        files.sort(key=lambda f: f['name'])
        dirs.sort()

        os_root_normalized = os_root.replace("\\", "/")
        def trim_path(p):
            p = p.replace("\\", "/")
            if p.startswith(os_root_normalized):
                p = p[len(os_root_normalized):]
            while p.startswith("/"):
                p = p[1:]
            return p

        result = {
            # name is the name of the file system, which
            # is used to determine the media root
            "name": fs_name,
            # return the relative path, suitable for the request url
            # that would reproduce this result
            "path": trim_path(path),
            # return the relative path to the parent, suitable to produce
            # a directory listing on the parent
            "parent": trim_path(parent),
            # return the list of files as a dictionary
            "files": files,
            # return the names of all sub directories
            "directories": dirs
        }

        return result

    def saveFile(self, user, fs_name, path, stream, mtime=None):

        path = self.getPath(user, fs_name, path)

        dirpath, _ = os.path.split(path)
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)

        with open(path, "wb") as wb:
            buf = stream.read(2048)
            while buf:
                wb.write(buf)
                buf = stream.read(2048)

        if mtime is not None:
            os.utime(path, (mtime, mtime))
