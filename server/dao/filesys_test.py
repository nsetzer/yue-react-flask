
import unittest
import json
import io

from .filesys import FileSystem, S3FileSystemImpl, sh_escape

head_object = b"""
{
    "AcceptRanges": "bytes",
    "LastModified": "Thu, 31 May 2018 19:58:03 GMT",
    "ContentLength": 39,
    "ETag": "\"7b44db95e1d680754f1427725f7ba991\"",
    "VersionId": "3Y8zbBadnMBS7Nd1g5kzLHPgVJl3vlFS",
    "ContentType": "binary/octet-stream",
    "Metadata": {},
    "ReplicationStatus": "COMPLETED"
}
"""

class _ProcFileTest(object):
    """an implementation of _ProcFile for testing"""

    data_0 = b"                           PRE New Folder\n" + \
             b"                           PRE test\n" + \
             b"2018-05-31 15:57:50          0 file0\n" + \
             b"2018-05-31 15:57:50       1474 New File\n"
    data_1 = b"                           PRE New Folder\n"
    data_2 = b"2018-05-31 15:57:50       1474 New File\n"

    data_map = {
        "New Folder": (True, 0, 0),
        "test": (True, 0, 0),
        "New File": (False, 1474, 1527796670),
        "file0": (False, 0, 1527796670),
    }

    exitstatus = 0

    def __init__(self, cmd, mode):
        super(_ProcFileTest, self).__init__()

        if 'w' in mode:
            self.buffer = io.BytesIO()
            self.write = self.buffer.write

        if 'r' in mode:
            self.buffer = io.BytesIO(self.data)
            self.read = self.buffer.read

        self.returncode = -1
        self.mode = mode
        self.cmd = cmd

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        self.close()

    def close(self):
        self.returncode = _ProcFileTest.exitstatus

# example return value from s3api head_object


class FileSystemTestCase(unittest.TestCase):

    def test_sh_escape(self):
        args = ['cat', '/tmp/file']
        out = sh_escape(args)
        self.assertEqual(out, "cat /tmp/file")

        args = ['echo', 'hello world']
        out = sh_escape(args)
        self.assertEqual(out, "echo \"hello world\"")

    def test_memfs(self):

        fs = FileSystem()

        path = "mem:///test/file.txt"
        msg = b"hello world\n"

        self.assertFalse(fs.exists(path))

        with fs.open(path, "wb") as wb:
            wb.write(msg)

        self.assertTrue(fs.exists(path))

        with fs.open(path, "rb") as rb:
            self.assertEqual(msg, rb.read())

        scheme, parts = fs.parts(path)
        parent = scheme + fs.join(*parts[:-1])
        items = fs.listdir(parent)
        self.assertEqual(len(items), 1)
        self.assertTrue(fs.samefile(fs.join(parent, items[0]), path))

        self.assertTrue(fs.isfile(path))
        self.assertFalse(fs.isfile(parent))

        self.assertFalse(fs.isdir(path))
        self.assertTrue(fs.isdir(parent))

        for name, is_dir, size, mtime in fs.scandir(parent):
            self.assertEqual(size, len(msg))

    # the following s3 tests check that the parsing of the
    # aws cli tool is done correctly. no attempt is made
    # to connect to an actual s3 bucket

    def test_s3fs_isfile(self):

        fs = S3FileSystemImpl()
        fs.pfile = _ProcFileTest

        _ProcFileTest.data = _ProcFileTest.data_1
        _ProcFileTest.exitstatus = 0

        self.assertFalse(fs.isfile("s3://bucket/New Folder"))
        self.assertTrue(fs.isdir("s3://bucket/New Folder"))

        _ProcFileTest.data = _ProcFileTest.data_2
        _ProcFileTest.exitstatus = 0

        self.assertTrue(fs.isfile("s3://bucket/New File"))
        self.assertFalse(fs.isdir("s3://bucket/New File"))

    def test_s3fs_listdir(self):

        fs = S3FileSystemImpl()
        fs.pfile = _ProcFileTest

        _ProcFileTest.data = _ProcFileTest.data_0
        _ProcFileTest.exitstatus = 0

        items = fs.listdir("s3://bucket/")

        self.assertEqual(len(items), 4)
        self.assertTrue("New Folder" in items)
        self.assertTrue("New File" in items)
        self.assertTrue("file0" in items)
        self.assertTrue("test" in items)

    def test_s3fs_scandir(self):

        fs = S3FileSystemImpl()
        fs.pfile = _ProcFileTest

        _ProcFileTest.data = _ProcFileTest.data_0
        _ProcFileTest.exitstatus = 0

        items = fs.scandir("s3://bucket/")

        self.assertEqual(len(items), 4)
        for name, is_dir, size, mtime in items:
            _is_dir, _size, _mtime = _ProcFileTest.data_map[name]
            self.assertEqual(is_dir, _is_dir)
            self.assertEqual(size, _size)
            self.assertEqual(mtime, _mtime)

    def test_s3fs_exists(self):
        fs = S3FileSystemImpl()
        fs.pfile = _ProcFileTest

        # check for a directory existing
        _ProcFileTest.data = _ProcFileTest.data_1
        _ProcFileTest.exitstatus = 0

        self.assertTrue(fs.exists("s3://bucket/test"))

        # check for a file existing
        _ProcFileTest.data = _ProcFileTest.data_2
        _ProcFileTest.exitstatus = 0

        self.assertTrue(fs.exists("s3://bucket/file0"))

        # check for a file or directory that does not exist
        _ProcFileTest.data = b""
        _ProcFileTest.exitstatus = -1

        self.assertFalse(fs.exists("s3://bucket/dne"))

    def test_s3fs_open_write(self):
        fs = S3FileSystemImpl()
        fs.pfile = _ProcFileTest

        _ProcFileTest.data = b""
        _ProcFileTest.exitstatus = 0

        with fs.open("s3://bucket/file0", "wb") as wb:
            wb.write(b"abc123")

        self.assertEqual(wb.returncode, 0)

    def test_s3fs_open_read(self):
        fs = S3FileSystemImpl()
        fs.pfile = _ProcFileTest

        _ProcFileTest.data = b"abc123"
        _ProcFileTest.exitstatus = 0

        with fs.open("s3://bucket/file0", "rb") as rb:
            self.assertEqual(rb.read(), b"abc123")
        self.assertEqual(rb.returncode, 0)

def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(FileSystemTestCase)
    unittest.TextTestRunner().run(suite)

if __name__ == '__main__':
    main()