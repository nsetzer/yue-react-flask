import os
import sys
import unittest
import json
import time

from ..dao.db import main_test
from ..dao.library import Song
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

    def test_001a_saveFiles(self):

        root = "default"
        path = "test/test.txt"

        self.service.saveFile(self.app.USER, root, path, BytesIO(b"abc123"))

        result = self.service.listSingleFile(self.app.USER, root, path)

        print(result)

        self.assertEqual(result['files'][0]['version'], 1)
        self.assertEqual(result['path'], path)

    def test_001b_saveFiles(self):

        # same test as 001a, but increment the version (upsert->update)
        root = "default"
        path = "test/test.txt"

        self.service.saveFile(self.app.USER, root, path, BytesIO(b"abc123"))

        result = self.service.listSingleFile(self.app.USER, root, path)

        print(result)

        self.assertEqual(result['files'][0]['version'], 2)
        self.assertEqual(result['path'], path)


if __name__ == '__main__':
    main_test(sys.argv, globals())

