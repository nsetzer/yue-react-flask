
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

from stat import S_ISDIR, S_ISREG, S_IRGRP

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
        st = os.stat(path)

        size = st.st_size
        permission = st.st_mode & 0o777
        mtime = int(st.st_mtime)

        _, name = self.split(path)

        if not (st.st_mode & S_IRGRP):
            return FileNotFoundError(path)

        is_dir = bool(S_ISDIR(st.st_mode))

        if is_dir or S_ISREG(st.st_mode):
            return FileRecord(name, is_dir, size, mtime, 0, permission)

        return FileNotFoundError(path)

    def remove(self, path):

        os.remove(path)

        dir, _ = self.split(path)
        if len(self.listdir(dir))==0:
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

    def exists(self, path):
        return path in MemoryFileSystemImpl._mem_store

    def open(self, path, mode):
        # supports {w,r,a}{b,}
        if 'w' in mode:
            f = io.BytesIO() if 'b' in mode else io.StringIO()
            f.close = lambda: f.seek(0)
            f.fileno = lambda: -1
            dt = datetime.datetime.now()
            mtime = int(time.mktime(dt.timetuple()))
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

        if path not in MemoryFileSystemImpl._mem_store:
            raise FileNotFoundError(path)

        f, mtime = MemoryFileSystemImpl._mem_store[path]
        _, name = self.split(path)

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
    default_fs = dict()

    def __init__(self):
        super(FileSystem, self).__init__()

        self._fs = dict(FileSystem.default_fs)

        self._fs[MemoryFileSystemImpl.scheme] = MemoryFileSystemImpl()

        self._fs_default = LocalFileSystemImpl()

    @staticmethod
    def register(scheme, fs):
        FileSystem.default_fs[scheme] = fs

    def getFileSystemForPath(self, path):
        for scheme, fs in self._fs.items():
            if path.startswith(scheme):
                return fs
        return self._fs_default

    def __getattr__(self, attr):
        return lambda path, *args, **kwargs: \
            getattr(self.getFileSystemForPath(path), attr)(
                path, *args, **kwargs)

def main():

    mode = sys.argv[1]
    path = sys.argv[2]

    fs = FileSystem()

    if mode == "scan":
        for name, is_dir, size, mtime in fs.scandir(path):
            print("%s %15d %15d %s" % (
                'd' if is_dir else 'f',
                mtime, size, name))
    elif mode == "exists":
        print("True" if fs.exists(path) else "False")
    elif mode == "list":
        for name in fs.listdir(path):
            print(name)
    elif mode == "stat":
        name, is_dir, size, mtime = fs.file_info(path)
        print("%s %15d %15d %s" % (
                'd' if is_dir else 'f',
                mtime, size, name))
    elif mode == "cat":
        # read a file form the path to stdout
        with fs.open(path, "rb") as rb:
            sys.stdout.buffer.write(rb.read())
    elif mode == "write":
        # write a file from stdin to the path
        with fs.open(path, "wb") as wb:
            wb.write(sys.stdin.buffer.read())
    elif mode == "remove":
        fs.remove(path)


if __name__ == '__main__':
    main()
