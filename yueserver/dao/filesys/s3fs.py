
import io
import os
import sys
import datetime
import time
from threading import Thread, Lock
try:
    import boto3
    import botocore
except ImportError:
    boto3 = None
    botocore = None

from .util import sh_escape, AbstractFileSystem, _ProcFile, \
    BytesFIFO, BytesFIFOWriter, BytesFIFOReader, FileRecord

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

class BotoReaderThread(Thread):
    """docstring for BotoReaderThread"""
    def __init__(self, fifo, bucket, key):
        super(BotoReaderThread, self).__init__()
        self.bucket = bucket
        self.key = key
        self.fifo = fifo

    def run(self):
        writer = BytesFIFOWriter(self.fifo)
        try:
            self.bucket.download_fileobj(self.key, writer)
        finally:
            writer.close()

class BotoReaderFile(object):
    """docstring for BotoReaderFile"""
    def __init__(self, bucket, key):
        super(BotoReaderFile, self).__init__()

        if not key:
            raise Exception("%s: invalid key" % bucket)

        self.lock = Lock()
        self.fifo = BytesFIFO(lock=self.lock)
        self.reader = BytesFIFOReader(self.fifo)

        self.thread = BotoReaderThread(self.fifo, bucket, key)
        self.thread.start()

    def read(self, size=-1):
        return self.reader.read(size)

    def close(self):
        self.thread.join()
        self.reader.close()

    def flush(self):
        self.reader.flush()

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        self.close()

class BotoWriterThread(Thread):
    """docstring for BotoWriterThread"""
    def __init__(self, fifo, bucket, key):
        super(BotoWriterThread, self).__init__()
        self.bucket = bucket
        self.key = key
        self.fifo = fifo

    def run(self):
        reader = BytesFIFOReader(self.fifo)
        sys.stderr.write("boto write: reader opened\n")
        try:
            self.bucket.upload_fileobj(reader, self.key)
        except Exception as e:
            sys.stderr.write("boto write: reader error:\n")
            sys.stderr.write("%s\n" % e)
        finally:
            sys.stderr.write("boto write: reader closed\n")
            reader.close()

class BotoWriterFile(object):
    """docstring for BotoWriterFile"""

    def __init__(self, bucket, key):
        super(BotoWriterFile, self).__init__()

        if not key:
            raise Exception("%s: invalid key" % bucket)

        self.lock = Lock()
        self.fifo = BytesFIFO(lock=self.lock)
        self.writer = BytesFIFOWriter(self.fifo)

        self.thread = BotoWriterThread(self.fifo, bucket, key)
        self.thread.start()

    def write(self, data):
        return self.writer.write(data)

    def close(self):
        sys.stderr.write("boto write: writer closed\n")
        self.writer.close()  # order matters
        self.thread.join()

    def flush(self):
        self.writer.flush()

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        self.close()

class BotoFileSystemImpl(AbstractFileSystem):
    """docstring for S3FileSystemImpl"""
    scheme = "s3://"

    def __init__(self, endpoint_url, region, access_key, secret_key):
        super(BotoFileSystemImpl, self).__init__()

        # -----------
        # TODO: there should be a global registry of
        # bucket names to s3 instances, to allow for multiple regions/secrets
        # note: buckets are unique to a region...
        self.session = boto3.session.Session()
        self.s3 = self.session.resource('s3',
            region_name=region,
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key)
        self.client = self.session.client('s3',
            region_name=region,
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key)

    def _parse_path(self, path):
        """extract bucket name and key from the path"""
        if not path.startswith(self.scheme):
            raise Exception(path)
        path = path[len(self.scheme):]
        if '/' not in path:
            return path, ""
        bucket_name, key = path.split("/", 1)
        return bucket_name, key

    def samefile(self, patha, pathb):
        """ returns true if the path exists and are the same object"""
        return self.exists(patha) and patha == pathb

    def isfile(self, path):
        """ returns true if the path exists"""
        bucket_name, key = self._parse_path(path)
        return key and self.exists(path)

    def isdir(self, path):
        """returns true if the prefix path exists"""
        bucket_name, key = self._parse_path(path)
        bucket = self.s3.Bucket(bucket_name)

        if key == "/":
            key = ""
        elif key and not key.endswith("/"):
            key += "/"

        for obj in bucket.objects.filter(Prefix=key, Delimiter="/"):
            return True
        return False

    def exists(self, path):
        """ returns true if the key exists """
        bucket_name, key = self._parse_path(path)
        bucket = self.s3.Bucket(bucket_name)
        for obj in bucket.objects.filter(Prefix=key, Delimiter="/"):
            sys.stderr.write(">%s>\n" % obj)
            if not obj.key.endswith("/"):
                return True
        return False

    def open(self, path, mode):
        """ returns a file-like object for reading or writing

        Writing mode (wb) returns a writable object which will
        stream data up to s3. The caller must call close when
        writing is complete to persist the file.

        Reading mode (rb) returns a readble object which will
        stream data down from s3.
        """
        if 'b' not in mode:
            raise Exception(mode)

        bucket_name, key = self._parse_path(path)
        bucket = self.s3.Bucket(bucket_name)

        if 'w' in mode:
            return BotoWriterFile(bucket, key)
        else:
            return BotoReaderFile(bucket, key)

    def listdir(self, path):
        """ returns all sub-names for the given key
        this includes both 'directories' and files.

        see scandir for more information
        """
        bucket_name, key = self._parse_path(path)
        return [entry.name for entry in self._scandir_impl(bucket_name, key)]

    def scandir(self, path):
        """ returns a FileRecord describing every file and directory
        under a given subkey

        The file record is a tuple (name, isDir, size, epoch)

        S3 is an object store, and as such 'directories' do not exist
        Instead the Delimiter '/' is used to determine boundary in key names
        This method returns all names which do not contain the delimiter and
        have the prefix -- that is all files in a given directory. It also
        returns all unique names which do contain the delimiter in an
        efficient fashion -- that is all sub directories

        """
        bucket_name, key = self._parse_path(path)
        return [entry for entry in self._scandir_impl(bucket_name, key)]

    def set_mtime(self, path, mtime):
        """ no-op. setting mtime is not supported at this time.

        """
        pass

    def file_info(self, path):
        """ returns a FileRecord for a given path

        note: directories must end in a '/' or a FileNotFoundError
        exception will be returned. use isdir to avoid this limitation
        when trying to determine validity of the path.

        """
        bucket_name, key = self._parse_path(path)
        bucket = self.s3.Bucket(bucket_name)

        if key == "":
            return FileRecord("", True, 0, 0)

        for obj in bucket.objects.filter(Prefix=key, Delimiter="/"):
            dt = obj.last_modified
            epoch = int(time.mktime(dt.timetuple()))
            print(">>> `%s` `%s`" % (key, obj.key))
            return FileRecord(obj.key, False, obj.size, epoch)
        raise FileNotFoundError(path)

    def remove(self, path):
        """ remove a key from the bucket

        FileNotFoundError is thrown if the file does not exist
        """
        bucket_name, key = self._parse_path(path)
        obj = self.s3.Object(bucket_name, key)
        response = obj.delete()
        status_code = response['ResponseMetadata']['HTTPStatusCode']
        if status_code == 204:  # no content
            raise FileNotFoundError(path)

    def _scandir_impl(self, bucket_name, key):

        if key == "/":
            key = ""
        elif key and not key.endswith("/"):
            key += "/"

        paginator = self.client.get_paginator('list_objects')
        items = []
        iterator = paginator.paginate(Bucket=bucket_name, Prefix=key,
            Delimiter='/', PaginationConfig={'PageSize': None})

        for response_data in iterator:
            prefixes = response_data.get('CommonPrefixes', [])
            for prefix in prefixes:
                prefix_name = prefix['Prefix']
                if prefix_name.endswith('/'):
                    name = prefix_name.rstrip('/')
                    name = name[len(key):]
                    yield FileRecord(name, True, 0, 0)

            contents = response_data.get('Contents', [])
            for content in contents:
                name = content['Key']
                name = name[len(key):]
                size = content['Size']
                epoch = int(time.mktime(content['LastModified'].timetuple()))
                if name:
                    yield FileRecord(name, False, size, epoch)