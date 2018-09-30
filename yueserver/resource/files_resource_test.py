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

        cls.storageDao = cls.app.filesys_service.storageDao
        cls.userDao = cls.app.filesys_service.userDao

        cls.USERNAME = "admin"
        cls.USER = cls.userDao.findUserByEmail(cls.USERNAME)

        cls.db = cls.app.db

    @classmethod
    def tearDownClass(cls):
        cls.app.tearDown()

    def setUp(self):
        super().setUp()

        self.db.delete(self.db.tables.FileSystemStorageTable)

    def tearDown(self):
        super().tearDown()

    def test_get_roots(self):

        username = "admin"
        with self.app.login(username, username) as app:
            data = app.get_json('/api/fs/roots')
            self.assertTrue("default" in data, data)

    def test_list_default(self):

        path1 = os.path.join(os.getcwd(), "yueserver/app.py")
        self.storageDao.insert(self.USER['id'], path1, 0, 0)

        path2 = os.path.join(os.getcwd(), "yueserver/framework/config.py")
        self.storageDao.insert(self.USER['id'], path2, 0, 0)

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

    def test_list_default_empty_root(self):
        # return information as if the directory was empty
        # when listing the root directory and it does not exist
        username = "admin"
        with self.app.login(username, username) as app:
            # demonstrate listing a directory and selecting various
            # directories to explore the system
            data = app.get_json('/api/fs/default/path/')
            self.assertEqual(data['name'], "default")
            self.assertEqual(data['parent'], "")
            self.assertEqual(data['path'], "")
            self.assertEqual(len(data['files']), 0)
            self.assertEqual(len(data['directories']), 0)

    def test_download_file(self):

        path1 = os.path.join(os.getcwd(), "yueserver/framework/config.py")
        self.storageDao.insert(self.USER['id'], path1, 0, 0)

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
            self.assertEqual(response.status_code, 200, response.status_code)
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
            self.assertEqual(response.status_code, 200, response.status_code)
            self.assertFalse(fs.exists("mem://test/test"))

    def test_get_index(self):
        username = "admin"
        with self.app.login(username, username) as app:
            dat0 = b"abc123"
            paths = []
            names = []
            for i in range(5):
                name = 'upload-%d.txt' % i
                names.append(name)
                path = 'test/%s' % name
                paths.append(path)
                url = '/api/fs/mem/path/' + path
                response = app.post(url, data=dat0)
                self.assertEqual(response.status_code, 200, response.status_code)

            # show that all files can be listed from the root directory
            url = '/api/fs/mem/index/'
            params = {'limit': 50, 'page': 0}
            response = app.get(url, query_string=params)
            self.assertEqual(response.status_code, 200, response.status_code)
            files = response.json()['result']
            self.assertEqual(len(paths), len(files))
            for obj in files:
                self.assertTrue(obj['path'] in paths)

            # show that listing a folder only lists the contents
            # relative to the requested folder

            url = '/api/fs/mem/index/test'
            params = {'limit': 50, 'page': 0}
            response = app.get(url, query_string=params)
            self.assertEqual(response.status_code, 200, response.status_code)
            files = response.json()['result']
            self.assertEqual(len(names), len(files))
            for obj in files:
                self.assertTrue(obj['path'] in names)

            # show that paging works
            url = '/api/fs/mem/index/test'
            for i in range(len(names)):
                name = 'upload-%d.txt' % i
                params = {'limit': 1, 'page': i}
                response = app.get(url, query_string=params)
                self.assertEqual(response.status_code, 200, response.status_code)
                path = response.json()['result'][0]['path']

                self.assertEqual(path, name, path)



if __name__ == '__main__':
    main_test(sys.argv, globals())
