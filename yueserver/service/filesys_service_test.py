import os
import sys
import unittest
import json
import time

from ..dao.db import main_test
from ..dao.library import Song
from ..dao.storage import StorageNotFoundException
from ..dao.image import ImageScale
from ..app import TestApp
from .exception import FileSysServiceException, FileSysKeyNotFound

from io import BytesIO
from .transcode_service import ImageScale

from PIL import Image

class FileServiceTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = TestApp(cls.__name__)

        cls.service = cls.app.filesys_service

    @classmethod
    def tearDownClass(cls):
        cls.app.tearDown()

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_001a_saveFile(self):

        root = "mem"
        path = "test/test.txt"

        self.service.saveFile(self.app.USER, root, path, BytesIO(b"abc123"))

        result = self.service.listSingleFile(self.app.USER, root, path)

        print(result)

        self.assertEqual(result['files'][0]['version'], 1)
        self.assertEqual(result['path'], path)

        result = self.service.listDirectory(self.app.USER, root, "test")
        print(result)

    def test_001b_updateFile(self):

        # same test as 001a, but increment the version (upsert->update)
        root = "mem"
        path = "test/test.txt"

        self.service.saveFile(self.app.USER, root, path, BytesIO(b"def456"))

        result = self.service.listSingleFile(self.app.USER, root, path)

        print(result)

        self.assertEqual(result['files'][0]['version'], 2)
        self.assertEqual(result['path'], path)

        result = self.service.listDirectory(self.app.USER, root, "test")
        print(result)

    def test_001c_index(self):

        # same test as 001a, but increment the version (upsert->update)
        root = "mem"
        path = "test/test.txt"

        result = self.service.listIndex(self.app.USER, root, "", limit=10, offset=0)
        print(result)
        result = self.service.listIndex(self.app.USER, root, "test", limit=10, offset=0)
        print(result)

    def test_001d_deleteFiles(self):

        # same test as 001a, but increment the version (upsert->update)
        root = "mem"
        path = "test/test.txt"

        result = self.service.remove(self.app.USER, root, path)

        with self.assertRaises(StorageNotFoundException):
            self.service.listSingleFile(self.app.USER, root, path)

        with self.assertRaises(StorageNotFoundException):
            self.service.listDirectory(self.app.USER, root, "test")

    def test_002a_system(self):

        key1 = self.service.getUserSystemPassword(self.app.USER)
        key2 = self.service.getUserSystemPassword(self.app.USER)
        print("system")
        print("system", key1)
        print("system", key2)
        print("system", len(key2))

    def test_003_user_notes(self):

        root = "mem"
        path = "public/notes/test_note.txt"
        self.service.saveFile(self.app.USER, root, path, BytesIO(b"hello"))

        root = "mem"
        path = "public/notes/subfolder/nope.txt"
        self.service.saveFile(self.app.USER, root, path, BytesIO(b"hello"))

        root = "mem"
        path = "public/notes/nope.png"
        self.service.saveFile(self.app.USER, root, path, BytesIO(b"hello"))

        files = self.service.getUserNotes(self.app.USER, root, "public/notes")

        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]['file_name'], 'test_note.txt')

    def test_004_remove_file_and_previews(self):
        """
        removing a file should remove all meta data along with that file
        """

        root = "mem"
        path = "test/test.png"

        data = open("./res/icon.png", "rb")

        self.service.saveFile(self.app.USER, root, path, data)
        # generate a thumbnail and show it exists
        url = self.service.previewFile(self.app.USER, root, path,
            ImageScale.THUMB)
        self.assertTrue(self.service.fs.exists(url))

        # delete the file, and thumbnails
        self.service.remove(self.app.USER, root, path)
        self.assertFalse(self.service.fs.exists(url))

    def test_005_remove_all_files(self):
        # prepare for next test

        for f in self.service.listIndex(self.app.USER, "mem", ""):
            print(f)
            self.service.remove(self.app.USER, "mem", f['path'])

    def test_005a_quota(self):

        user_id = self.app.USER['id']

        dao = self.service.storageDao

        # start with no files and 2KB quota
        dao.setUserDiskQuota(user_id, 2**11)
        count, usage, quota = dao.userDiskUsage(user_id)
        self.assertEqual(count, 0)
        self.assertEqual(usage, 0)
        self.assertEqual(quota, 2048)

        self.service.saveFile(self.app.USER, "mem", "a", BytesIO(b"0" * 1024))
        self.service.saveFile(self.app.USER, "mem", "b", BytesIO(b"0" * 512))
        print("\n\n***")

        count, usage, quota = dao.userDiskUsage(user_id)
        self.assertEqual(count, 2)
        self.assertEqual(usage, 1536)
        self.assertEqual(quota, 2048)

        with self.assertRaises(FileSysServiceException):
            self.service.saveFile(self.app.USER, "mem", "c", BytesIO(b"0" * 1024))

        count, usage, quota = dao.userDiskUsage(user_id)
        self.assertEqual(count, 2)
        self.assertEqual(usage, 1536)
        self.assertEqual(quota, 2048)

        # lowering the quota below the current usage level
        # will prevent additional writes
        dao.setUserDiskQuota(user_id, 2**10)
        with self.assertRaises(FileSysServiceException):
            self.service.saveFile(self.app.USER, "mem", "c", BytesIO(b"0" * 1024))

        # _internalSave(user_id, storage_path, inputStream, chunk_size)
        # _internalCheckQuota(user_id, size, byte_index, uid)



if __name__ == '__main__':
    main_test(sys.argv, globals())

