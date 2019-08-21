#! cd ../../.. && python3 -m yueserver.dao.filesys.filesys
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
import posixpath
from ..util import epoch_time
from stat import S_ISDIR, S_ISREG, S_IRGRP, S_ISLNK

from .util import sh_escape, AbstractFileSystem, FileRecord

class FileSystemError(Exception):
    pass

class FileSystemExistsError(FileSystemError):
    pass


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

    def drive(self, patha):
        """ returns a meaningless but unique drive identifier (str or int) """

        if os.name == 'nt':
            # todo: support for UNC paths
            return patha[:2].upper()
        else:
            return os.stat(patha).st_dev


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

    FS_UNK = 0
    FS_REG = 1
    FS_DIR = 2
    FS_LNK = 3

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

    def samedrive(self, patha, pathb):
        sta = self.drive(patha)
        stb = self.drive(pathb)
        return sta == stb

    def find(self, dir):
        """
        yield items starting at dir
        let the caller decide how to filter and display results
        """

        dirs = [dir]

        while len(dirs) > 0:
            dir = dirs.pop(0)

            yield (FileSystem.FS_DIR, dir, 0)

            for rec in self.scandir(dir):
                path = self.join(dir, rec.name)
                # todo: handle links, etc
                if rec.isDir:
                    dirs.append(path)
                else:
                    yield (FileSystem.FS_REG, path, rec.size)

    def _copy_impl(self, src, dst_dir, move, followLinks):

        """
        yield pairs of (src,dst) names moving src into dst

        a simple move across file systems may result in a complicated copy

        yield directories before contants so that directories can be created
        """

        _, name = self.split(src)
        tgt = self.join(dst_dir, name)

        if move and self.exists(tgt) and self.samefile(src, tgt):
            # a copy operation should result in duplicating the file
            pass
        elif not self.isdir(src):
            rec = self.file_info(src)
            yield (FileSystem.FS_REG, src, tgt, rec.size)
        elif move and self.samedrive(src, dst_dir):
            # if just moving, between the same drive
            # a simple rename should suffice
            # if the move fails, the user can always just copy files instead
            yield (FileSystem.FS_REG, src, tgt, 0)
        else:

            dirs = [(src, tgt)]
            while len(dirs) > 0:
                dir, dst = dirs.pop(0)

                yield (FileSystem.FS_DIR, dir, dst, 0)

                for rec in self.scandir(dir):
                    path = self.join(dir, rec.name)
                    tgt = self.join(dst, rec.name)
                    # todo: handle links, etc
                    if rec.isDir:
                        dirs.append((path, tgt))
                    else:
                        yield (FileSystem.FS_REG, path, tgt, rec.size)

    def copy(self, src, dst_dir):
        return self._copy_impl(src, dst_dir, False, False)

    def copy_multiple(self, urls, dst_dir):

        for url in urls:
            yield from self.copy(url, dst_dir)

    def move(self, src, dst_dir):
        return self._copy_impl(src, dst_dir, True, False)

    def move_multiple(self, urls, dst_dir):

        for url in urls:
            yield from self.move(url, dst_dir)

    def _remove_recursive(self, dir):

        """
        yield paths from a directory in an order such
        that the content is returned first followed by
        the directory, so that directories may be
        deleted as they are emptied

        """
        for rec in self.scandir(dir):
            path = self.join(dir, rec.name)
            try:
                rec = self.file_info(path)
                # todo: handle links, etc
                if rec.isDir:
                    yield from self._remove_recursive(path)
                else:
                    yield (FileSystem.FS_REG, path, rec.size)

            except FileNotFoundError as e:
                yield (FileSystem.FS_UNK, src, 0)
                continue

        yield (FileSystem.FS_DIR, dir, 0)

    def delete(self, src):

        """
        """
        _, name = self.split(src)
        tgt = self.join(src, name)

        if not self.isdir(src):
            try:
                rec = self.file_info(src)
                yield (FileSystem.FS_REG, src, rec.size)
            except FileNotFoundError as e:
                yield (FileSystem.FS_UNK, src, 0)

        else:
            yield from self._remove_recursive(src)

    def delete_multiple(self, urls):

        for url in urls:
            yield from self.remove(url)





def main():

    fs = FileSystem()

    for kind, src, dst, size in fs.copy(r"D:\Storage\secure", "C:\\followme"):
        print("%d % 8d %s => %s" % (kind, size, src, dst))
    print("--")
    for kind, src, dst, size in fs.move(r"D:\Storage\secure", "D:\\followme"):
        print("%d % 8d %s => %s" % (kind, size, src, dst))
    print("--")
    for kind, src, dst, size in fs.copy(r"D:\Storage\secure\.yueattr", "C:\\followme"):
        print("%d % 8d %s => %s" % (kind, size, src, dst))

if __name__ == '__main__':
    main()