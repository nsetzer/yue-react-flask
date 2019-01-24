import os
import sys
import unittest
import json
import time

from ..dao.db import main_test
from ..dao.filesys.filesys import FileSystem
from ..dao.filesys.crypt import FileDecryptorReader
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

        path1 = "yueserver/app.py"
        file_path1 = "/%s" % path1
        storage_path1 = os.path.join(os.getcwd(), path1)
        self.storageDao.insert(self.USER['id'],
            file_path1, storage_path1, 0, 0)

        path2 = "yueserver/framework/config.py"
        file_path2 = "/%s" % path2
        storage_path2 = os.path.join(os.getcwd(), path2)
        self.storageDao.insert(self.USER['id'],
            file_path2, storage_path2, 0, 0)

        username = "admin"
        with self.app.login(username, username) as app:
            # demonstrate listing a directory and selecting various
            # directories to explore the system
            data = app.get_json('/api/fs/default/path/')
            self.assertEqual(data['name'], "default")
            self.assertEqual(data['parent'], "")
            self.assertEqual(data['path'], "")
            self.assertTrue("yueserver" in data['directories'], data)

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

        path = "yueserver/framework/config.py"
        file_path = "/" + path
        storage_path = os.path.join(os.getcwd(), path)
        self.storageDao.insert(self.USER['id'], file_path, storage_path, 0, 0)

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

        file_path = "/test"
        storage_path = "mem://test/test"
        fs = FileSystem()
        fs.open(storage_path, "wb").close()
        self.storageDao.insert(self.USER['id'], file_path, storage_path, 0, 0)

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

    def test_upload_encrypt(self):

        fs = FileSystem()
        username = "admin"
        with self.app.login(username, username) as app:

            # create the password for encryption
            url = '/api/fs/change_password'
            response = app.put(url, data=b"password",
                headers={'X-YUE-PASSWORD': 'password'})
            self.assertEqual(response.status_code, 200, response.status_code)

            # POST a file, with the encryption header set
            # file should be written to memory FS in an encrypted state
            dat0 = b"abc123"
            path = 'test/upload_encrypt.txt'
            url = '/api/fs/mem/path/' + path
            response = app.post(url, data=dat0,
                headers={'X-YUE-PASSWORD': 'password'})
            self.assertEqual(response.status_code, 200, response.status_code)
            self.assertTrue(os.path.exists(path))
            dat1_enc = open(path, "rb").read()

            # get the key used for encryption
            key = self.storageDao.getEncryptionKey(self.USER['id'], 'password')

            # use the api to get the encrypted form of the key
            url2 = '/api/fs/user_key'
            response = app.get(url2)
            user_key = response.json()['result']['key']
            self.assertTrue(user_key.startswith("$2b$"))

            # we cant guess the storage path anymore, since it is
            # randomly generated
            info = self.storageDao.file_info(self.USER['id'],
                self.storageDao.absoluteFilePath(
                    self.USER['id'], self.USER['role_id'], path))

            # sanity check, the file path should be an absolute path
            # form of what the user gave for the file
            self.assertTrue(info.file_path.endswith(path))
            # the storage path should not contain the user given path
            self.assertTrue(path not in info.storage_path)
            print(info.file_path, info.storage_path)
            # read the file written to the memory FS, decrypt it
            with fs.open(info.storage_path, "rb") as rb:
                stream = FileDecryptorReader(rb, key)
                dat1 = stream.read()
            self.assertEqual(dat0, dat1)

            # a simple get on the data should return the encrypted file
            # TODO: maybe the request should fail?
            #       likely not, so that I can implement client side encryption
            response = app.get(url)
            dat2 = response.data
            self.assertEqual(b'EYUE', dat2[:4], dat2)

            # A get with the header set should return the unencrypted data
            response = app.get(url,
                headers={'X-YUE-PASSWORD': 'password'})
            self.assertEqual(response.status_code, 200, response.status_code)
            dat2 = response.data
            self.assertEqual(dat0, dat2)

            # TODO: add a app.get request to retrieve the decrypted file
            return

if __name__ == '__main__':
    main_test(sys.argv, globals())
