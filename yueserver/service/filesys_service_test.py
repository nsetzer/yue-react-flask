import os
import sys
import unittest
import json
import time

from ..dao.db import main_test
from ..dao.library import Song
from ..dao.storage import StorageNotFoundException
from ..app import TestApp

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

        root = "default"
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
        root = "default"
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
        root = "default"
        path = "test/test.txt"

        print("----index")
        result =self.service.listIndex(self.app.USER, root, "", limit=10, offset=0)
        print(result)
        result =self.service.listIndex(self.app.USER, root, "test", limit=10, offset=0)
        print(result)

    def test_001d_deleteFiles(self):

        # same test as 001a, but increment the version (upsert->update)
        root = "default"
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

if __name__ == '__main__':
    main_test(sys.argv, globals())

