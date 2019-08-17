
"""
An Abstract File System API

A subset of os and os.path are wrapped into an interface layer allowing
for file systems to be accessed in a transparent way. This allows
for writing and reading files in memory or in s3 buckets.

every function takes a file path as the first argument. this is used to
determine the correct file system handler to use. local files should not
have a scheme prefix, while remote files must always have a scheme prefix.

the path is assumed to always be an absolute path
"""
import os
import sys
import io
import datetime
import time
import subprocess
import logging
from ..util import epoch_time
from stat import S_ISDIR, S_ISREG, S_IRGRP, S_ISLNK

from .util import sh_escape, AbstractFileSystem, FileRecord

class LocalFileSystemImpl(AbstractFileSystem):
    """docstring for LocalFileSystemImpl"""
    scheme = "file://"
    impl = os.path

    def __init__(self):
        super(LocalFileSystemImpl, self).__init__()

    def islocal(self, path):
        return True

    def open(self, path, mode):
        return open(path, mode)

    def listdir(self, path):
        return os.listdir(path)

    def relpath(self, path, root):
        return os.path.relpath(path, root)

    def scandir(self, path):

        entries = []
        for name in os.listdir(path):
            fullpath = os.path.join(path, name)

            try:
                entries.append(self.file_info(fullpath))
            except FileNotFoundError:
                pass

        return entries

    def makedirs(self, path):
        if not os.path.exists(path):
            os.makedirs(path)

    def set_mtime(self, path, mtime):
        os.utime(path, (mtime, mtime))

    def file_info(self, path):

        _, name = self.split(path)

        st = os.stat(path)  # throws OSError

        size = st.st_size
        permission = st.st_mode & 0o777
        mtime = int(st.st_mtime)

        # TODO check if current user has read access
        #if not (st.st_mode & S_IRGRP):
        #    raise FileNotFoundError("grp access: %s" % path)

        # todo fix the mistake of FileRecord
        # replace isDir with an enum:
        #   FS_UNK=0, FS_DIR=1, FS_REG=2
        #   isLink = true|false
        # use lstat, and if it is a link, use os.stat
        # to figure out the kind of link

        is_dir = bool(S_ISDIR(st.st_mode))

        if is_dir or S_ISREG(st.st_mode):
            return FileRecord(name, is_dir, size, mtime, 0, permission)

        raise FileNotFoundError(path)

    def remove(self, path):

        os.remove(path)

        dir, _ = self.split(path)
        if len(self.listdir(dir)) == 0:
            os.rmdir(dir)

class MemoryFileSystemImpl(AbstractFileSystem):
    """An In-Memory filesystem

    The memory file system attempts to mimic the behavior of s3
    """
    scheme = "mem://"
    _mem_store = {}

    def __init__(self):
        super(MemoryFileSystemImpl, self).__init__()

    def samefile(self, patha, pathb):
        return self.exists(patha) and patha == pathb

    def isfile(self, path):
        return path in MemoryFileSystemImpl._mem_store

    def isdir(self, path):
        return path not in MemoryFileSystemImpl._mem_store

    def relpath(self, path, root):
        return posixpath.relpath(path, root)

    def exists(self, path):
        return path in MemoryFileSystemImpl._mem_store

    def open(self, path, mode):
        # supports {w,r,a}{b,}
        if 'w' in mode:
            f = io.BytesIO() if 'b' in mode else io.StringIO()
            f.close = lambda: f.seek(0)
            f.fileno = lambda: -1
            mtime = epoch_time()
            MemoryFileSystemImpl._mem_store[path] = [f, mtime]
            return f
        else:
            if path not in MemoryFileSystemImpl._mem_store:
                raise FileNotFoundError("(%s) %s" % (mode, path))
            t = io.BytesIO if 'b' in mode else io.StringIO
            f, mtime = MemoryFileSystemImpl._mem_store[path]
            if not isinstance(f, t):
                raise TypeError("expected: %s" % t.__name__)
            if 'a' in mode:
                f.seek(0, os.SEEK_END)
            return f
        raise ValueError("Invalid mode: %s" % mode)

    def _scandir_impl(self, path):
        if not path.endswith("/"):
            path += self.impl.sep
        for fpath, (f, mtime) in MemoryFileSystemImpl._mem_store.items():
            if fpath.startswith(path):
                name = fpath.replace(path, "")
                if '/' in name:
                    name = name.split('/')[0]
                    yield FileRecord(name, True, 0, 0)
                else:
                    yield FileRecord(name, False, len(f.getvalue()), mtime)

    def listdir(self, path):
        return [rec.name for rec in self._scandir_impl(path)]

    def scandir(self, path):
        return [entry for entry in self._scandir_impl(path)]

    def set_mtime(self, path, mtime):
        if path not in MemoryFileSystemImpl._mem_store:
            raise FileNotFoundError(path)
        MemoryFileSystemImpl._mem_store[path][1] = mtime

    def file_info(self, path):

        _, name = self.split(path)

        if path not in MemoryFileSystemImpl._mem_store:
            # guess tha
            temp = path
            if not temp.endswith("/"):
                temp += "/"
            for f in MemoryFileSystemImpl._mem_store.keys():
                if f.startswith(temp):
                    return FileRecord(name, True, 0, 0)
            raise FileNotFoundError(path)

        f, mtime = MemoryFileSystemImpl._mem_store[path]

        return FileRecord(name, False, len(f.getvalue()), mtime)

    def remove(self, path):
        if path not in MemoryFileSystemImpl._mem_store:
            raise FileNotFoundError(path)

        del MemoryFileSystemImpl._mem_store[path]

    @staticmethod
    def clear():
        MemoryFileSystemImpl._mem_store = {}

class FileSystem(object):
    """Generic FileSystem Interface

    all paths must be absolute file file paths, the correct
    implementation of open depends on the path scheme
    """

    # by default s3 paths should fail, until registed
    default_fs = {"s3://": None}

    def __init__(self):
        super(FileSystem, self).__init__()

        self._fs = dict(FileSystem.default_fs)

        self._fs[MemoryFileSystemImpl.scheme] = MemoryFileSystemImpl()

        self._fs_default = LocalFileSystemImpl()

    @staticmethod
    def register(scheme, fs):
        """
        register a new filesystem implementation

        scheme: prefix used to match urls
        fs: an implementation or None to invalidate
        """
        FileSystem.default_fs[scheme] = fs

    def getFileSystemForPath(self, path):
        for scheme, fs in self._fs.items():
            if path.startswith(scheme):
                if fs is None:
                    raise Exception("Invalid Scheme '%s'" % scheme)
                return fs
        return self._fs_default

    def __getattr__(self, attr):
        return lambda path, *args, **kwargs: \
            getattr(self.getFileSystemForPath(path), attr)(
                path, *args, **kwargs)

    def _mem(self):
        return self._fs[MemoryFileSystemImpl.scheme]._mem_store

