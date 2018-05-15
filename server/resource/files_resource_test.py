import os
import sys
import unittest
import json
import time

from ..dao.db import main_test
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
            self.assertTrue("server" in data['directories'])

            data = app.get_json('/api/fs/default/path/server')
            self.assertEqual(data['name'], "default")
            self.assertEqual(data['parent'], "")
            self.assertEqual(data['path'], "server")
            self.assertTrue("framework" in data['directories'])
            files = [f['name'] for f in data['files']]
            self.assertTrue("app.py" in files)

            data = app.get_json('/api/fs/default/path/server/framework')
            self.assertEqual(data['name'], "default")
            self.assertEqual(data['parent'], "server")
            self.assertEqual(data['path'], "server/framework")
            files = [f['name'] for f in data['files']]
            self.assertTrue("config.py" in files)

    def test_download_file(self):

        username = "admin"
        with self.app.login(username, username) as app:
            path = 'server/framework/config.py'
            response = app.get('/api/fs/default/path/' + path)
            # should stream the contents of the file
            dat0 = response.data
            self.assertTrue(len(dat0) > 0)
            dat1 = open(path, "rb").read()
            self.assertEqual(dat0, dat1)


if __name__ == '__main__':
    main_test(sys.argv, globals())
