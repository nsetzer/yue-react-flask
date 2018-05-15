
import os, sys

from stat import S_ISDIR, S_ISREG, S_IRGRP
from .util import FileSysServiceException, FFmpegEncoder


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

    def getPath(self, fs_name, path):
        """
        returns a (possibly relative) file path given the name of a
        file system (which determines the base directory) and a path.
        the path is guaranteed to be a sub directory of the named fs.
        """

        if fs_name != "default":
            raise FileSysServiceException("invalid name: %s" % fs_name)

        os_root = self.config.filesystem.media_root
        # todo: this does not provide the strong guarantee expected.
        # todo: this should always return an absolute path
        return os.path.join(os_root, path)

    def listDirectory(self, fs_name, path):
        """

        todo: check for .yueignore in the root, or in the given path
        use to load filters to remove elements from the response
        """

        if fs_name != "default":
            raise FileSysServiceException("invalid name: %s" % fs_name)

        os_root = self.config.filesystem.media_root
        abs_path = self.getPath(fs_name, path)

        parent, _ = os.path.split(abs_path)
        if not parent.startswith(os_root):
            parent = os_root

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
                files.append({"name": name, "size": st.st_size})

        files.sort(key=lambda f: f['name'])
        dirs.sort()

        def trim_path(p):
            p = p.replace("\\", "/")
            if p.startswith(os_root):
                p = p[len(os_root):]
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
