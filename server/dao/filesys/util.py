
import io
import os
import sys
import posixpath

from collections import namedtuple
from threading import Thread, Condition, Lock

FileRecord = namedtuple('FileRecord', ['name', 'isDir', 'size', 'mtime'])

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

class BytesFIFO(object):
    """
    A FIFO that can store a fixed number of bytes.
    """
    def __init__(self, init_size=1024, incr_size=1204, lock=None):
        """ Create a FIFO of ``init_size`` bytes. """
        self._buffer = io.BytesIO(b"\x00" * init_size)
        self._size = init_size
        self._filled = 0
        self._read_ptr = 0
        self._write_ptr = 0
        self._writer_closed = False
        self._reader_closed = False

        self._capacity_increase = incr_size

        self._lock = lock or Lock()
        self._cond = Condition(self._lock)

    def read(self, request_size=-1):
        """
        Read at most ``size`` bytes from the FIFO.

        If less than ``size`` bytes are available, or ``size`` is negative,
        return all remaining bytes.
        """

        # TODO: reads should block if the writer is not closed and the
        #       filled size is empty

        with self._lock:
            sys.stderr.write("read : enter\n")

            # Figure out how many bytes we can really read
            if request_size < 0:
                size = self._filled
            else:
                size = min(request_size, self._filled)
            contig = self._size - self._read_ptr
            contig_read = min(contig, size)

            # block until some bytes are avilable
            # do not block if some bytes are available
            while not self._writer_closed and contig_read == 0:
                sys.stderr.write("read : wait\n")
                self._cond.wait()
                sys.stderr.write("read : wake\n")

                if request_size < 0:
                    size = self._filled
                else:
                    size = min(request_size, self._filled)
                contig = self._size - self._read_ptr
                contig_read = min(contig, size)

            # Go to read pointer
            self._buffer.seek(self._read_ptr)

            ret = self._buffer.read(contig_read)
            self._read_ptr += contig_read
            if contig_read < size:
                leftover_size = size - contig_read
                self._buffer.seek(0)
                ret += self._buffer.read(leftover_size)
                self._read_ptr = leftover_size

            self._filled -= size
            sys.stderr.write("read : exit\n")
            return ret

    def write(self, data):
        """
        Write as many bytes of ``data`` as are free in the FIFO.

        If less than ``len(data)`` bytes are free, write as many as can be written.
        Returns the number of bytes written.
        """

        with self._lock:
            sys.stderr.write("write: enter %d\n" % len(data))
            write_size = len(data)

            if self._size < self._filled + write_size:
                self.resize(self.filled + write_size + self._capacity_increase)
                sys.stderr.write("write: resize\n")

            if write_size:
                sys.stderr.write("write: writing\n")
                contig = self._size - self._write_ptr
                contig_write = min(contig, write_size)
                # TODO: avoid 0 write
                # TODO: avoid copy
                # TODO: test performance of above
                self._buffer.seek(self._write_ptr)
                self._buffer.write(data[:contig_write])
                self._write_ptr += contig_write
                sys.stderr.write("write: writing\n")

                if contig < write_size:
                    self._buffer.seek(0)
                    self._buffer.write(data[contig_write:write_size])
                    #self._buffer.write(buffer(data, contig_write, write_size - contig_write))
                    self._write_ptr = write_size - contig_write
                sys.stderr.write("write: writing\n")

            self._filled += write_size

            sys.stderr.write("write: notify\n")
            self._cond.notify()

            sys.stderr.write("write: exit %s\n" % write_size)
            return write_size

    def close(self):
        sys.stdout.write("close\n")

    def flush(self):
        pass

    def empty(self):
        with self._lock:
            return self._filled == 0

    def full(self):
        with self._lock:
            return self._filled == self._size

    def capacity(self):
        with self._lock:
            return self._size

    def __len__(self):
        with self._lock:
            return self._filled

    def __nonzero__(self):
        with self._lock:
            return self._filled > 0

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        self.close()

    def resize(self, new_size):
        """
        Resize FIFO to contain ``new_size`` bytes. If FIFO currently has
        more than ``new_size`` bytes filled, :exc:`ValueError` is raised.
        If ``new_size`` is less than 1, :exc:`ValueError` is raised.
        If ``new_size`` is smaller than the current size, the internal
        buffer is not contracted (yet).
        """
        if new_size < 1:
            raise ValueError("Cannot resize to zero or less bytes.")

        if new_size < self._filled:
            raise ValueError("Cannot contract FIFO to less than {} bytes, "
                             "or data will be lost.".format(self._filled))

        # original data is non-contiguous. we need to copy old data,
        # re-write to the beginning of the buffer, and re-sync
        # the read and write pointers.
        if self._read_ptr >= self._write_ptr:
            old_data = self.read(self._filled)
            self._buffer.seek(0)
            self._buffer.write(old_data)
            self._filled = len(old_data)
            self._read_ptr = 0
            self._write_ptr = self._filled
        self._size = new_size

class BytesFIFOWriter(object):
    """docstring for BytesFIFOWriter"""

    def __init__(self, fifo):
        super(BytesFIFOWriter, self).__init__()
        self.fifo = fifo

    def write(self, data):
        return self.fifo.write(data)

    def close(self):
        with self.fifo._lock:
            self.fifo._writer_closed = True
            self.fifo._cond.notify()
            self.fifo.close()
            sys.stdout.write("writer closed\n")

    def flush(self):
        self.fifo.flush()

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        self.close()

class BytesFIFOReader(object):
    """docstring for BytesFIFOReader"""

    def __init__(self, fifo):
        super(BytesFIFOReader, self).__init__()
        self.fifo = fifo

    def read(self, size=-1):
        return self.fifo.read(size)

    def close(self):
        with self.fifo._lock:
            self.fifo._reader_closed = True
            self.fifo._cond.notify()
            self.fifo.close()

    def flush(self):
        self.fifo.flush()

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        self.close()

