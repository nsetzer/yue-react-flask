

import os
import unittest
import tempfile
import json
import time

from .db import db_init_main, db_connect
from .user import UserDao
from .storage import StorageDao, StorageException, StorageNotFoundException

from sqlalchemy.exc import IntegrityError

class StorageTestCase(unittest.TestCase):

    db_name = "StorageTestCase"

    @classmethod
    def setUpClass(cls):
        # build a test database, with a minimal configuration
        cls.db_path = "database.test.%s.sqlite" % cls.db_name

        db = db_connect(None)

        env_cfg = {
            'features': ['test', ],
            'domains': ['test'],
            'roles': [
                {'test': {'features': ['all']}},
            ],
            'users': [
                {'email': 'user000',
                 'password': 'user000',
                 'domains': ['test'],
                 'roles': ['test']},
            ]
        }

        db_init_main(db, db.tables, env_cfg)

        cls.userDao = UserDao(db, db.tables)

        cls.USERNAME = "user000"
        cls.USER = cls.userDao.findUserByEmail(cls.USERNAME)

        cls.storageDao = StorageDao(db, db.tables)

        cls.db = db

    def setUp(self):

        # todo: delete all records before each test
        #self.db.tables.FileSystemStorageTable.drop(self.db.engine, checkfirst=True)
        #self.db.tables.FileSystemTable.drop(self.db.engine, checkfirst=True)
        #self.db.tables.FileSystemPermissionTable.drop(self.db.engine, checkfirst=True)
        pass

    def test_001a_filesystem(self):

        name = "test"
        path = "file:///opt/yueserver"
        file_id = self.storageDao.createFileSystem(name, path)

        with self.assertRaises(IntegrityError):
            self.storageDao.createFileSystem(name, path)

        role = self.storageDao.findFileSystemByName(name)
        self.assertEqual(role['id'], file_id)

        self.storageDao.removeFileSystem(file_id)

        role = self.storageDao.findFileSystemByName(name)
        self.assertIsNone(role)

    def test_001b_filesystem_permission(self):

        name = "test"
        path = "file:///opt/yueserver"
        file_id = self.storageDao.createFileSystem(name, path)

        role = self.userDao.findRoleByName('test')

        self.userDao.addFileSystemToRole(role['id'], file_id)

        exists = self.userDao.roleHasFileSystem(role['id'], file_id)
        self.assertTrue(exists)

        self.userDao.removeFileSystemFromRole(role['id'], file_id)

        exists = self.userDao.roleHasFileSystem(role['id'], file_id)
        self.assertFalse(exists)

    def test_001c_filesystem_scheme(self):

        local_path = "/etc/hosts"
        remote_path = "file:///etc/hosts"

        path1 = self.storageDao.localPathToNormalPath(local_path)
        self.assertEqual(path1, remote_path)

        path2 = self.storageDao.NormalPathTolocalPath(remote_path)
        self.assertEqual(path2, local_path)

    def test_000a_listdir(self):
        """
        add two files to different directories and show
        that listing a directory returns the correct names
        """

        user_id = self.USER['id']

        names = ["file1.txt", "folder"]

        self.storageDao.insert(user_id, "file:///file1.txt", 1234, 1234567890)
        self.storageDao.insert(user_id, "file:///folder/file2.txt", 1234, 1234567890)

        count = 0
        for rec in self.storageDao.listdir(user_id, "file:///"):
            self.assertTrue(rec.name in names)
            count += 1
        self.assertEqual(len(names), count)

    def test_002a_insert_remove(self):
        """
        check that a user can insert and remove records
        """
        user_id = self.USER['id']
        name = 'file_insert_remove.txt'
        path = "file:///" + name

        with self.assertRaises(StorageNotFoundException):
            self.storageDao.file_info(user_id, path)

        self.storageDao.insert(user_id, path, 1234, 1234567890)

        record = self.storageDao.file_info(user_id, path)
        self.assertEqual(name, record.name)

        self.storageDao.remove(user_id, path)

        with self.assertRaises(StorageNotFoundException):
            self.storageDao.file_info(user_id, path)

    def test_002b_update(self):
        """
        """
        user_id = self.USER['id']
        name = 'file_update.txt'
        path = "file:///" + name

        with self.assertRaises(StorageNotFoundException):
            self.storageDao.file_info(user_id, path)

        self.storageDao.insert(user_id, path, 1234, 1234567890)

        record1 = self.storageDao.file_info(user_id, path)

        self.storageDao.update(user_id, path, 1000, 1000000000)

        record2 = self.storageDao.file_info(user_id, path)

        self.assertEqual(record1.version + 1, record2.version)

    def test_002b_rename(self):
        """
        """
        user_id = self.USER['id']
        name1 = 'file_src.txt'
        name2 = 'file_dst.txt'
        path1 = "file:///" + name1
        path2 = "file:///" + name2

        with self.assertRaises(StorageNotFoundException):
            self.storageDao.file_info(user_id, path1)

        # create and check that it exists
        self.storageDao.insert(user_id, path1, 1234, 1234567890)
        record1 = self.storageDao.file_info(user_id, path1)

        # rename and check the old name does not exist
        self.storageDao.rename(user_id, path1, path2)
        with self.assertRaises(StorageNotFoundException):
            self.storageDao.file_info(user_id, path1)

        # verify the new name exists
        record2 = self.storageDao.file_info(user_id, path2)
        self.assertEqual(record1.version, record2.version)

    def test_002b_insert_exists(self):
        """
        """
        user_id = self.USER['id']
        name1 = 'file_insert_src.txt'
        path1 = "file:///" + name1

        with self.assertRaises(StorageNotFoundException):
            self.storageDao.file_info(user_id, path1)

        # create and check that it exists
        self.storageDao.insert(user_id, path1, 1234, 1234567890)
        with self.assertRaises(StorageException):
            self.storageDao.insert(user_id, path1, 1234, 1234567890)

    def test_002b_rename_exists(self):
        """
        """
        user_id = self.USER['id']
        name1 = 'file_rename_src.txt'
        name2 = 'file_rename_dst.txt'
        path1 = "file:///" + name1
        path2 = "file:///" + name2

        with self.assertRaises(StorageNotFoundException):
            self.storageDao.file_info(user_id, path1)

        # create and check that it exists
        self.storageDao.insert(user_id, path1, 1234, 1234567890)
        self.storageDao.insert(user_id, path2, 1234, 1234567890)

        # rename and check the old name does not exist
        with self.assertRaises(StorageException):
            self.storageDao.rename(user_id, path1, path2)

    def test_003a_listdir_error(self):

        user_id = self.USER['id']

        with self.assertRaises(StorageException):
            for rec in self.storageDao.listdir(user_id, "file:///folder"):
                print(rec)

    def test_004a_file_info(self):

        user_id = self.USER['id']

        with self.assertRaises(StorageException):
            self.storageDao.file_info(user_id, "file://")

        rec = self.storageDao.file_info(user_id, "file:///")
        self.assertEqual(rec.name, '')

        rec = self.storageDao.file_info(user_id, "file:///file1.txt")
        self.assertEqual(rec.name, 'file1.txt')

        with self.assertRaises(StorageNotFoundException):
            self.storageDao.file_info(user_id, "file:///folder")

        rec = self.storageDao.file_info(user_id, "file:///folder/")
        self.assertEqual(rec.name, 'folder')

        rec = self.storageDao.file_info(user_id, "file:///folder/file2.txt")
        self.assertEqual(rec.name, 'file2.txt')

    # todo:
    #   test that a user cannot CRUD other users files
    #   rename when dst already exists should fail

def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(StorageTestCase)
    unittest.TextTestRunner().run(suite)

if __name__ == '__main__':
    main()