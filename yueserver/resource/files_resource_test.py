import os
import sys
import unittest
import json
import time

from ..dao.db import main_test
from ..dao.filesys.filesys import FileSystem
from ..dao.filesys.crypt import FileDecryptorReader, cryptkey
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

        user_id = cls.USER['id']
        role_id = cls.USER['role_id']
        cls.fs_default_id = cls.storageDao.getFilesystemId(
            user_id, role_id, "default")

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
        self.storageDao.insertFile(self.USER['id'], self.fs_default_id,
            file_path1, dict(storage_path=storage_path1))

        path2 = "yueserver/framework/config.py"
        file_path2 = "/%s" % path2
        storage_path2 = os.path.join(os.getcwd(), path2)
        self.storageDao.insertFile(self.USER['id'], self.fs_default_id,
            file_path2, dict(storage_path=storage_path2))

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
        self.storageDao.insertFile(self.USER['id'], self.fs_default_id,
            file_path, dict(storage_path=storage_path))

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
        self.storageDao.insertFile(self.USER['id'], self.fs_default_id,
            file_path, dict(storage_path=storage_path))

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
                headers={'X-YUE-PASSWORD': 'password'},
                query_string={'crypt': 'SERVER'})
            self.assertEqual(response.status_code, 200, response.status_code)
            self.assertTrue(os.path.exists(path))
            dat1_enc = open(path, "rb").read()

            # get the key used for encryption
            key = self.storageDao.getEncryptionKey(
                self.USER['id'], 'password', mode='server')

            # use the api to get the encrypted form of the key
            url2 = '/api/fs/user_key'
            response = app.get(url2, query_string={'mode': 'server'})
            user_key = response.json()['result']['key']
            self.assertTrue(user_key.startswith("01:$2b$"))

            # we cant guess the storage path anymore, since it is
            # randomly generated
            info = self.storageDao.file_info(self.USER['id'],
                self.fs_default_id,
                self.storageDao.absoluteFilePath(
                    self.USER['id'], self.USER['role_id'], path))

            # sanity check, the file path should be an absolute path
            # form of what the user gave for the file
            self.assertTrue(info.file_path.endswith(path))
            # the storage path should not contain the user given path
            self.assertTrue(path not in info.storage_path)
            # read the file written to the memory FS, decrypt it
            with fs.open(info.storage_path, "rb") as rb:
                print(info.storage_path)
                print(rb.read())
            with fs.open(info.storage_path, "rb") as rb:
                stream = FileDecryptorReader(rb, key)
                dat1 = stream.read()
            self.assertEqual(dat0, dat1)

            # A get with the header set should return the unencrypted data
            response = app.get(url,
                headers={'X-YUE-PASSWORD': 'password'})
            self.assertEqual(response.status_code, 200, response.status_code)
            dat2 = response.data
            self.assertEqual(dat0, dat2)

            # TODO: add a app.get request to retrieve the decrypted file
            return

    def test_download_public_file(self):

        username = "admin"
        with self.app.login(username, username) as app:

            ##################################################################
            # upload a file
            dat0 = b"abc123"
            path = 'test/upload.txt'
            url = '/api/fs/mem/path/' + path
            response = app.post(url, data=dat0)
            self.assertEqual(response.status_code, 200, response.status_code)

            ##################################################################
            # set a public url
            url = '/api/fs/public/mem/path/' + path
            response = app.put(url)
            self.assertEqual(response.status_code, 200, response.status_code)
            fileId = response.json()['result']['id']

            ##################################################################
            # retrieve the file
            url = '/api/fs/public/' + fileId
            response = app.get(url)
            self.assertEqual(response.status_code, 200, response.dat)
            self.assertEqual(dat0, response.data)

            ##################################################################
            # send a password -- 401
            url = '/api/fs/public/' + fileId
            response = app.get(url, headers={'X-YUE-PASSWORD': 'password'})
            self.assertEqual(response.status_code, 401, response.status_code)

            ##################################################################
            # revoke public url
            url = '/api/fs/public/mem/path/' + path
            response = app.put(url, query_string={'revoke': True})
            self.assertEqual(response.status_code, 200, response.status_code)
            self.assertEqual(response.json()['result']['id'], "")

            ##################################################################
            # can no longer retrieve the file after revoking
            url = '/api/fs/public/' + fileId
            response = app.get(url)
            self.assertEqual(response.status_code, 404, response.dat)

    def test_download_public_file_password(self):

        username = "admin"
        with self.app.login(username, username) as app:

            ##################################################################
            # upload a file
            dat0 = b"abc123"
            path = 'test/upload.txt'
            url = '/api/fs/mem/path/' + path
            response = app.post(url, data=dat0)
            self.assertEqual(response.status_code, 200, response.status_code)

            ##################################################################
            # set a public url
            url = '/api/fs/public/mem/path/' + path
            response = app.put(url, headers={'X-YUE-PASSWORD': 'password'})
            self.assertEqual(response.status_code, 200, response.status_code)
            fileId = response.json()['result']['id']

            ##################################################################
            # retrieve the file
            url = '/api/fs/public/' + fileId
            response = app.get(url)
            self.assertEqual(response.status_code, 401, response.status_code)

            ##################################################################
            # send a password -- 401
            url = '/api/fs/public/' + fileId
            response = app.get(url, headers={'X-YUE-PASSWORD': 'password'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(dat0, response.data)

    def test_set_client_key(self):

        username = "admin"
        with self.app.login(username, username) as app:
            url = '/api/fs/user_key'

            # there should be no keys available
            response = app.get(url, query_string={'mode': 'server'})
            self.assertEqual(response.status_code, 404, response.status_code)

            response = app.get(url, query_string={'mode': 'client'})
            self.assertEqual(response.status_code, 404, response.status_code)

            # allow the user to set an encryption key
            key = cryptkey('password')
            response = app.put(url, data=key)
            self.assertEqual(response.status_code, 200, response.status_code)

            # show we can get the key we just set
            response = app.get(url, query_string={'mode': 'client'})
            self.assertEqual(response.status_code, 200, response.status_code)
            self.assertEqual(response.json()['result']['key'], key)

    def test_set_client_key_invalid(self):

        username = "admin"
        with self.app.login(username, username) as app:

            url = '/api/fs/user_key'
            response = app.put(url, data="abc")
            self.assertEqual(response.status_code, 400, response.status_code)

if __name__ == '__main__':
    main_test(sys.argv, globals())
