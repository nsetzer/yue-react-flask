import os
import sys
import unittest
import json
import time

from ..dao.db import main_test
from ..dao.filesys.filesys import FileSystem
from ..app import TestApp

class FilesResourceTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = TestApp(cls.__name__)

    @classmethod
    def tearDownClass(cls):
        cls.app.tearDown()

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_get_roots(self):

        username = "admin"
        with self.app.login(username, username) as app:
            data = app.get_json('/api/fs/roots')
            self.assertTrue("default" in data, data)

    def test_list_default(self):

        username = "admin"
        with self.app.login(username, username) as app:
            # demonstrate listing a directory and selecting various
            # directories to explore the system
            data = app.get_json('/api/fs/default/path/')
            self.assertEqual(data['name'], "default")
            self.assertEqual(data['parent'], "")
            self.assertEqual(data['path'], "")
            self.assertTrue("yueserver" in data['directories'])

            data = app.get_json('/api/fs/default/path/yueserver')
            self.assertEqual(data['name'], "default")
            self.assertEqual(data['parent'], "")
            self.assertEqual(data['path'], "yueserver")
            self.assertTrue("framework" in data['directories'])
            files = [f['name'] for f in data['files']]
            self.assertTrue("app.py" in files)

            data = app.get_json('/api/fs/default/path/yueserver/framework')
            self.assertEqual(data['name'], "default")
            self.assertEqual(data['parent'], "yueserver")
            self.assertEqual(data['path'], "yueserver/framework")
            files = [f['name'] for f in data['files']]
            self.assertTrue("config.py" in files)

    def test_download_file(self):

        username = "admin"
        with self.app.login(username, username) as app:
            path = 'yueserver/framework/config.py'
            response = app.get('/api/fs/default/path/' + path)
            # should stream the contents of the file
            dat0 = response.data
            self.assertTrue(len(dat0) > 0)
            dat1 = open(path, "rb").read()
            self.assertEqual(dat0, dat1)

    def test_list_file_not_found(self):

        username = "admin"
        with self.app.login(username, username) as app:
            path = 'test/dne'
            response = app.get('/api/fs/default/path/' + path)
            self.assertEqual(response.status_code, 404)

    def test_upload_file(self):
        """test file upload

        show that a file can be uploaded to a pre-defined sub directory
        """
        username = "admin"
        with self.app.login(username, username) as app:
            dat0 = b"abc123"
            path = 'test/upload.txt'
            url = '/api/fs/default/path/' + path
            response = app.post(url, data=dat0)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(os.path.exists(path))
            dat1 = open(path, "rb").read()
            self.assertEqual(dat0, dat1)

    def test_delete_file(self):
        """ test remove file

        create an in-memory file, then use the file system end
        point to delete it
        """
        fs = FileSystem()
        fs.open("mem://test/test", "wb").close()

        username = "admin"
        with self.app.login(username, username) as app:
            url = '/api/fs/mem/path/test'
            self.assertTrue(fs.exists("mem://test/test"))
            response = app.delete(url)
            self.assertEqual(response.status_code, 200)
            self.assertFalse(fs.exists("mem://test/test"))

if __name__ == '__main__':
    main_test(sys.argv, globals())
