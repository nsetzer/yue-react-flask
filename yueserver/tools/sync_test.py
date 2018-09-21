
import os
import sys
import unittest
import shutil
import posixpath
import logging

from ..dao.db import main_test
from ..dao.filesys.filesys import FileSystem, MemoryFileSystemImpl

from ..app import TestApp
from ..framework.client import FlaskAppClient
from ..framework.application import AppTestClientWrapper

from .sync import (_check, _pull, _push, _delete_remote, _delete_local,
    SyncManager,
    _sync, _copy, _list, _config, _list_config, _remove_config, parseArgs)

def setUpClass(cls):
    cls.app = TestApp(cls.__name__)

    cls.root = "mem"
    cls.remote_base = ""
    cls.local_base = "./test/sync"
    cls.remote_path = cls.app.env_cfg['filesystems']['mem']

    cls.local_path_file0 = os.path.join(cls.local_base, "file0")
    cls.local_path_file1 = os.path.join(cls.local_base, "dir0", "file1")
    cls.local_path_file2 = os.path.join(cls.local_base, "file2")
    cls.local_path_file3 = os.path.join(cls.local_base, "dir1", "file3")

    cls.local_path_dir0 = os.path.join(cls.local_base, "dir0")
    cls.local_path_dir1 = os.path.join(cls.local_base, "dir1")

    cls.remote_path_file0 = posixpath.join(cls.remote_path, "file0")
    cls.remote_path_file1 = posixpath.join(cls.remote_path, "dir0", "file1")
    cls.remote_path_file2 = posixpath.join(cls.remote_path, "file2")
    cls.remote_path_file3 = posixpath.join(cls.remote_path, "dir1", "file3")

    cls.remote_path_dir0 = posixpath.join(cls.remote_path, "dir0")
    cls.remote_path_dir1 = posixpath.join(cls.remote_path, "dir1")

class SyncTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        setUpClass(cls)

        if not os.path.exists(cls.local_path_dir0):
            os.makedirs(cls.local_path_dir0)
        open(cls.local_path_file0, "w").close()
        open(cls.local_path_file1, "w").close()

    @classmethod
    def tearDownClass(cls):
        cls.app.tearDown()

        shutil.rmtree(cls.local_base)

    def setUp(self):
        super().setUp()

        self.username = "admin"
        self.rest_client = self.app.login(self.username, self.username)
        self.client = FlaskAppClient(self.rest_client, self.app._registered_endpoints)

    def tearDown(self):
        super().tearDown()

    def test_001a_check(self):

        MemoryFileSystemImpl.clear()
        fs = FileSystem()
        fs.open(self.remote_path_file2, "wb").close()
        fs.open(self.remote_path_file3, "wb").close()

        dld, uld, dlf, ulf = _check(self.client, self.root,
            self.remote_base, self.local_base)

        # file system was carefully designed to have one entry in
        # each of these lists
        self.assertEqual(len(dld), 1)
        self.assertEqual(dld[0], 'dir1')

        self.assertEqual(len(uld), 1)
        self.assertEqual(uld[0], 'dir0')

        self.assertEqual(len(dlf), 1)
        self.assertEqual(dlf[0][0], 'file2')

        self.assertEqual(len(ulf), 1)
        self.assertEqual(ulf[0][0], 'file0')

    def test_001b_check(self):

        fs = FileSystem()

        with fs.open(self.remote_path_file0, "wb") as wb:
            pass

        # --------------------------------------------------
        # mtime and size are equal, do nothing

        fs.set_mtime(self.remote_path_file0, 1234567890)
        fs.set_mtime(self.local_path_file0, 1234567890)
        dld, uld, dlf, ulf = _check(self.client, self.root,
            self.remote_base, self.local_base)

        self.assertTrue('file0' not in [n for n, _, _ in ulf])
        self.assertTrue('file0' not in [n for n, _, _ in dlf])

        # --------------------------------------------------
        # make the remote file bigger
        with fs.open(self.remote_path_file0, "wb") as wb:
            wb.write(b"123")

        # --------------------------------------------------
        # remote is newer, download
        fs.set_mtime(self.remote_path_file0, 1234567890)
        fs.set_mtime(self.local_path_file0, 1234567890 - 20)
        dld, uld, dlf, ulf = _check(self.client, self.root,
            self.remote_base, self.local_base)

        self.assertTrue('file0' in [n for n, _, _ in dlf])

        # --------------------------------------------------
        # remote is older, upload
        fs.set_mtime(self.local_path_file0, 1234567890 + 20)
        dld, uld, dlf, ulf = _check(self.client, self.root,
            self.remote_base, self.local_base)

        self.assertTrue('file0' in [n for n, _, _ in ulf])

        # --------------------------------------------------
        # the result for when the times are the same and the
        # sizes are different is undefined.
        # for the moment neither an upload or download occurs
        fs.set_mtime(self.local_path_file0, 1234567890)
        dld, uld, dlf, ulf = _check(self.client, self.root,
            self.remote_base, self.local_base)

        self.assertTrue('file0' not in [n for n, _, _ in ulf])
        self.assertTrue('file0' not in [n for n, _, _ in dlf])

        # --------------------------------------------------
        # size is equal, times are different

        with fs.open(self.remote_path_file0, "wb") as wb:
            wb.write(b"123")
        with fs.open(self.local_path_file0, "wb") as wb:
            wb.write(b"123")

        fs.set_mtime(self.local_path_file0, 1234567890)
        fs.set_mtime(self.remote_path_file0, 1234567890 + 20)

        _, _, size_l, _ = fs.file_info(self.local_path_file0)
        _, _, size_r, _ = fs.file_info(self.remote_path_file0)

        dld, uld, dlf, ulf = _check(self.client, self.root,
            self.remote_base, self.local_base)

        self.assertEqual(size_l, size_r)
        self.assertTrue('file0' not in [n for n, _, _ in ulf])
        self.assertTrue('file0' not in [n for n, _, _ in dlf])


        # --------------------------------------------------
        # create a sub directory to upload
        #
        os.makedirs(self.local_path_dir1)

        dld, uld, dlf, ulf = _check(self.client, self.root,
            self.remote_base, self.local_base)

        self.assertTrue(len(dld) > 0)
        self.assertTrue(len(uld) > 0)

        self.assertTrue("dir0" in uld)
        self.assertTrue("dir1" in dld)

    def test_002a_push(self):
        # test uploading a file
        # first do a dryrun, which should not alter state
        # then upload the file
        MemoryFileSystemImpl.clear()
        fs = FileSystem()
        fs.open(self.local_path_file0, "wb").close()

        ulf = [("file0", 0, 0)]
        self.assertTrue(fs.exists(self.local_path_file0))
        self.assertFalse(fs.exists(self.remote_path_file0))
        _push(self.client, self.root, self.remote_base, self.local_base,
            ulf, True)
        self.assertFalse(fs.exists(self.remote_path_file0))
        _push(self.client, self.root, self.remote_base, self.local_base,
            ulf, False)
        self.assertTrue(fs.exists(self.remote_path_file0))

    def test_003a_pull(self):
        # test downloading a file
        # first do a dryrun, which should not alter state
        # then download the file
        MemoryFileSystemImpl.clear()
        fs = FileSystem()
        fs.open(self.remote_path_file0, "wb").close()

        dlf = [("file0", 0, 0)]
        os.remove(self.local_path_file0)
        self.assertFalse(fs.exists(self.local_path_file0))
        self.assertTrue(fs.exists(self.remote_path_file0))
        _pull(self.client, self.root, self.remote_base, self.local_base,
            dlf, True)
        self.assertFalse(fs.exists(self.local_path_file0))
        _pull(self.client, self.root, self.remote_base, self.local_base,
            dlf, False)
        self.assertTrue(fs.exists(self.local_path_file0))

    def test_004a_delete_remote(self):

        MemoryFileSystemImpl.clear()
        fs = FileSystem()
        fs.open(self.remote_path_file0, "wb").close()

        dlf = [("file0", 0, 0)]

        self.assertTrue(fs.exists(self.remote_path_file0))
        _delete_remote(self.client, self.root, self.remote_base,
            dlf, True)
        self.assertTrue(fs.exists(self.remote_path_file0))
        _delete_remote(self.client, self.root, self.remote_base,
            dlf, False)
        self.assertFalse(fs.exists(self.remote_path_file0))

    def test_004a_delete_local(self):

        fs = FileSystem()
        fs.open(self.local_path_file0, "wb").close()

        ulf = [("file0", 0, 0)]

        self.assertTrue(fs.exists(self.local_path_file0))
        _delete_local(self.local_base, ulf, True)
        self.assertTrue(fs.exists(self.local_path_file0))
        _delete_local(self.local_base, ulf, False)
        self.assertFalse(fs.exists(self.local_path_file0))

class SyncManagerTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        cls.app = TestApp(cls.__name__);

    @classmethod
    def tearDownClass(cls):
        cls.app.tearDown()

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

class SyncCLITestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        setUpClass(cls)

    @classmethod
    def tearDownClass(cls):
        cls.app.tearDown()

    def setUp(self):
        super().setUp()

        if not os.path.exists(self.local_path_dir0):
            os.makedirs(self.local_path_dir0)
        if not os.path.exists(self.local_path_dir1):
            os.makedirs(self.local_path_dir1)

        self.username = "admin"
        self.rest_client = self.app.login(self.username, self.username)
        self.client = FlaskAppClient(self.rest_client,
            self.app._registered_endpoints)

        for path in [
            self.local_path_file0,
            self.local_path_file1,
            self.local_path_file2,
            self.local_path_file3,
          ]:
            if os.path.exists(path):
                os.remove(path)

    def tearDown(self):
        super().tearDown()

        if os.path.exists(self.local_base):
            shutil.rmtree(self.local_base)

    def test_sync(self):

        MemoryFileSystemImpl.clear()
        fs = FileSystem()

        fs.open(self.local_path_file0, "wb").close()
        fs.open(self.local_path_file1, "wb").close()
        fs.open(self.local_path_file2, "wb").close()
        fs.open(self.local_path_file3, "wb").close()

        args = parseArgs([
            "sync",
            "--username", "admin",
            "--password", "admin",
            "--host", "",
            "--config", "./test",
            "config", self.root, self.local_base,
        ])

        args.client = self.client

        _config(args)

        args = parseArgs([
            "sync",
            "--config", "./test",
            "sync", "-r", self.local_base
        ])

        args.client = self.client

        # test upload

        self.assertFalse(fs.exists(self.remote_path_file0))
        self.assertFalse(fs.exists(self.remote_path_file1))
        self.assertFalse(fs.exists(self.remote_path_file2))
        self.assertFalse(fs.exists(self.remote_path_file3))

        _sync(args)

        self.assertTrue(fs.exists(self.remote_path_file0))
        self.assertTrue(fs.exists(self.remote_path_file1))
        self.assertTrue(fs.exists(self.remote_path_file2))
        self.assertTrue(fs.exists(self.remote_path_file3))

        # test download

        os.remove(self.local_path_file0)
        os.remove(self.local_path_file1)
        os.remove(self.local_path_file2)
        os.remove(self.local_path_file3)

        self.assertFalse(fs.exists(self.local_path_file0))
        self.assertFalse(fs.exists(self.local_path_file1))
        self.assertFalse(fs.exists(self.local_path_file2))
        self.assertFalse(fs.exists(self.local_path_file3))

        _sync(args)

        self.assertTrue(fs.exists(self.local_path_file0))
        self.assertTrue(fs.exists(self.local_path_file1))
        self.assertTrue(fs.exists(self.local_path_file2))
        self.assertTrue(fs.exists(self.local_path_file3))

    def test_sync_push(self):

        MemoryFileSystemImpl.clear()
        fs = FileSystem()

        fs.open(self.local_path_file0, "wb").close()
        fs.open(self.remote_path_file0, "wb").close()

        fs.open(self.local_path_file1, "wb").close()

        fs.open(self.remote_path_file2, "wb").close()

        args = parseArgs([
            "sync",
            "--username", "admin",
            "--password", "admin",
            "--host", "",
            "--config", "./test",
            "config", self.root, self.local_base,
        ])

        args.client = self.client

        _config(args)

        args = parseArgs([
            "sync",
            "--config", "./test",
            "push", "-r", "--delete", self.local_base
        ])

        args.client = self.client

        _sync(args)

        # this should copy local file 1 up,
        # and delete remote file 2
        self.assertTrue(fs.exists(self.local_path_file0))
        self.assertTrue(fs.exists(self.local_path_file1))
        self.assertFalse(fs.exists(self.local_path_file2))

        self.assertTrue(fs.exists(self.remote_path_file0))
        self.assertTrue(fs.exists(self.remote_path_file1))
        self.assertFalse(fs.exists(self.remote_path_file2))

    def test_sync_pull(self):

        MemoryFileSystemImpl.clear()
        fs = FileSystem()

        fs.open(self.local_path_file0, "wb").close()
        fs.open(self.remote_path_file0, "wb").close()

        fs.open(self.local_path_file1, "wb").close()

        fs.open(self.remote_path_file2, "wb").close()

        args = parseArgs([
            "sync",
            "--username", "admin",
            "--password", "admin",
            "--host", "",
            "--config", "./test",
            "config", self.root, self.local_base,
        ])

        args.client = self.client

        _config(args)

        args = parseArgs([
            "sync",
            "--config", "./test",
            "pull", "-r", "--delete", self.local_base
        ])

        args.client = self.client

        _sync(args)

        # this should copy local file 1 up,
        # and delete remote file 2
        self.assertTrue(fs.exists(self.local_path_file0))
        self.assertFalse(fs.exists(self.local_path_file1))
        self.assertTrue(fs.exists(self.local_path_file2))

        self.assertTrue(fs.exists(self.remote_path_file0))
        self.assertFalse(fs.exists(self.remote_path_file1))
        self.assertTrue(fs.exists(self.remote_path_file2))

    def test_copy_up(self):

        MemoryFileSystemImpl.clear()
        fs = FileSystem()

        fs.open(self.local_path_file0, "wb").close()

        args = parseArgs([
            "sync",
            "--username", "admin",
            "--password", "admin",
            "--host", "",
            "--config", "./test",
            "config", self.root, self.local_base,
        ])

        args.client = self.client

        _config(args)

        args = parseArgs([
            "sync",
            "--config", "./test",
            "copy", self.local_path_file0, "server://mem/foo"
        ])

        args.client = self.client

        _copy(args)

        self.assertTrue(fs.exists("mem://test/foo"))


    def test_copy_down(self):

        MemoryFileSystemImpl.clear()
        fs = FileSystem()

        fs.open(self.remote_path_file0, "wb").close()

        args = parseArgs([
            "sync",
            "--username", "admin",
            "--password", "admin",
            "--host", "",
            "--config", "./test",
            "config", self.root, self.local_base,
        ])

        args.client = self.client

        _config(args)

        args = parseArgs([
            "sync",
            "--config", "./test",
            "copy", "server://mem/foo", self.local_path_file0
        ])

        args.client = self.client

        _copy(args)

        self.assertTrue(fs.exists(self.local_path_file0))

if __name__ == '__main__':
    main_test(sys.argv, globals())


