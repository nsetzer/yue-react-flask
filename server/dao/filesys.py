
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
import posixpath
import datetime
import time
import subprocess
import logging

try:
    import boto3
    import botocore
except ImportError:
    boto3 = None
    botocore = None

from stat import S_ISDIR, S_ISREG, S_IRGRP

class AbstractFileSystem(object):
    """docstring for AbstractFileSystem"""
    scheme = None
    impl = posixpath

    def __init__(self):
        super(AbstractFileSystem, self).__init__()

    def islocal(self, path):
        return False

    def isabs(self, path):
        return self.impl.isabs(path)

    def join(self, path, *args):
        return self.impl.join(path, *args)

    def split(self, path):
        return self.impl.split(path)

    def splitext(self, path):
        return self.impl.splitext(path)

    def samefile(self, patha, pathb):
        return self.impl.samefile(patha, pathb)

    def parts(self, path):
        """
        N.B. the following will print a valid URI:
            scheme, parts = fs.parts(path)
            path == fs.join(*parts))
        this API requires the scheme to be prefixed to the path
        for all operations, except for local files.
        """
        scheme = "file://localhost/"
        i = path.find("://")
        if "://" in path:
            i += len("://")
            scheme = path[:i]
            path = path[i:]
        if self.impl.altsep is not None:
            path = path.replace(self.impl.altsep, self.impl.sep)
        parts = path.split(self.impl.sep)
        if parts and not parts[0]:
            parts[0] = self.impl.sep
        return scheme, parts

    def isfile(self, path):
        return self.impl.isfile(path)

    def isdir(self, path):
        return self.imple.isdir(path)

    def exists(self, path):
        return self.impl.exists(path)

    def open(self, path, mode):
        pass

    def listdir(self, path):
        pass

    def scandir(self, path):
        """ yields: name, size, date in seconds"""
        pass

    def makedirs(self, path):
        # this is a no-op for file systems which do
        # not have a directory structure.
        # unlike os.makedirs, does not throw an exception
        # if the directory exists.
        pass

    def set_mtime(self, path, mtime):
        pass

    def file_info(self, path):
        """ a stat-like interface for querying information about a file

        returns name, is_dir, file_size, mtime
        """
        pass

    def remove(self, path):
        raise NotImplementedError(path)

class LocalFileSystemImpl(AbstractFileSystem):
    """docstring for LocalFileSystemImpl"""
    scheme = "file://"
    impl = os.path

    def __init__(self):
        super(LocalFileSystemImpl, self).__init__()

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

        _, name = self.split(path)

        if not (st.st_mode & S_IRGRP):
            return FileNotFoundError(path)

        is_dir = bool(S_ISDIR(st.st_mode))

        if is_dir or S_ISREG(st.st_mode):
            return (name, is_dir, st.st_size, int(st.st_mtime))

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
                raise FileNotFoundError(path)
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
                    yield (name, True, 0, 0)
                else:
                    yield (name, False, len(f.getvalue()), mtime)

    def listdir(self, path):
        return [name for name, _, _, _ in self._scandir_impl(path)]

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

        return (name, False, len(f.getvalue()), mtime)

    def remove(self, path):
        if path not in MemoryFileSystemImpl._mem_store:
            raise FileNotFoundError(path)

        del MemoryFileSystemImpl._mem_store[path]

    @staticmethod
    def clear():
        MemoryFileSystemImpl._mem_store = {}

def sh_escape(args):
    """
    print an argument list so that it can be copy and pasted to a terminal

    python 2 does not have a shlex.quote
    """
    args = args[:]
    for i, arg in enumerate(args):
        #  check the string for special characters
        for c in "\"\\ ":
            if c in arg:
                arg = '"' + arg.replace('"', '\\"') + '"'
                args[i] = arg
                continue
    return ' '.join(args)

class _ProcFile(object):
    """A file-like object which writes to a process

    Used to read and write files to s3

    does not support seeking
    """
    def __init__(self, cmd, mode):
        super(_ProcFile, self).__init__()

        _stdin = subprocess.PIPE if 'w' in mode else None
        _stdout = subprocess.PIPE if 'r' in mode else subprocess.DEVNULL

        logging.info("execute: %s" % sh_escape(cmd))

        self.proc = subprocess.Popen(cmd, stdin=_stdin, stdout=_stdout,
            stderr=subprocess.DEVNULL)

        if 'w' in mode:
            self.write = self.proc.stdin.write

        if 'r' in mode:
            self.read = self.proc.stdout.read

        self.returncode = -1
        self.mode = mode
        self.cmd = cmd

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        self.close()

    def close(self):

        if 'r' in self.mode:
            self.proc.stdout.close()

        if 'w' in self.mode:
            self.proc.stdin.close()

        self.proc.wait()

        self.returncode = self.proc.returncode

class S3FileSystemImpl(AbstractFileSystem):
    """docstring for S3FileSystemImpl"""
    scheme = "s3://"

    def __init__(self):
        super(S3FileSystemImpl, self).__init__()
        self.pfile = _ProcFile

    def samefile(self, patha, pathb):
        return self.exists(patha) and patha == pathb

    def isfile(self, path):
        _, is_dir, _, _ = self.file_info(path)
        return not is_dir

    def isdir(self, path):
        _, is_dir, _, _ = self.file_info(path)
        return is_dir

    def exists(self, path):
        try:
            self.file_info(path)
            return True
        except FileNotFoundError:
            return False

    def open(self, path, mode):
        if 'b' not in mode:
            raise ValueError("text mode not supported for open()")

        if 'r' in mode:
            cmd = ["aws", "s3", "cp", path, "-"]
            mode = "r"
        elif 'w' in mode:
            cmd = ["aws", "s3", "cp", "-", path]
            mode = "w"
        else:
            raise ValueError("mode not supported")

        return self.pfile(cmd, mode)

    def _parse_line(self, line):
        fmt = "%Y-%m-%d %H:%M:%S"

        items = line.split(None, 3)
        if len(items) == 4:
            fdate, ftime, size, name = items
            dt = datetime.datetime.strptime(fdate + " " + ftime, fmt)
            epoch = int(time.mktime(dt.timetuple()))
            return (name, False, int(size), epoch)
        elif len(items) > 0 and items[0] == 'PRE':
            # re-split, in case the directory name contains a space
            items = line.split(None, 1)
            name = items[-1].rstrip(self.impl.sep)
            return (name, True, 0, 0)

        raise Exception("Invalid Line: `%s`" % line)

    def _scandir_impl(self, path):

        if not path.endswith("/"):
            path += "/"

        entries = []
        cmd = ["aws", "s3", "ls", path]
        with self.pfile(cmd, "rb") as rb:
            data = rb.read()
            for line in data.decode("utf-8").splitlines():
                if line.strip():
                    yield self._parse_line(line)

    def listdir(self, path):
        return [name for name, _, _, _ in self._scandir_impl(path)]

    def scandir(self, path):
        return [entry for entry in self._scandir_impl(path)]

    def set_mtime(self, path, mtime):
        # this is a no-op, I'm not sure it *can* be implemented at this time
        pass

    def file_info(self, path):
        cmd = ["aws", "s3", "ls", path]
        with self.pfile(cmd, "rb") as rb:
            for line in rb.read().decode("utf-8").splitlines():
                if line.strip():
                    return self._parse_line(line)
        raise FileNotFoundError(path)

    def remove(self, path):
        cmd = ["aws", "s3", "rm", path]
        with self.pfile(cmd, "rb") as rb:
            rb.read()

class FileSystem(object):
    """Generic FileSystem Interface

    all paths must be absolute file file paths, the correct
    implementation of open depends on the path scheme
    """
    def __init__(self):
        super(FileSystem, self).__init__()

        self._fs = {
            S3FileSystemImpl.scheme: S3FileSystemImpl(),
            MemoryFileSystemImpl.scheme: MemoryFileSystemImpl(),
        }

        self._fs_default = LocalFileSystemImpl()

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
