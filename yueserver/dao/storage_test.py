

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
            'filesystems': {},
            'domains': ['test'],
            'roles': [
                {'test': {'features': ['all'], 'filesystems': []}},
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

        self.db.delete(self.db.tables.FileSystemStorageTable)
        self.db.delete(self.db.tables.FileSystemTable)
        self.db.delete(self.db.tables.FileSystemPermissionTable)

    def test_001a_filesystem(self):

        name = "test"
        path = "file:///opt/yueserver"
        file_id = self.userDao.createFileSystem(name, path)

        with self.assertRaises(IntegrityError):
            self.userDao.createFileSystem(name, path)

        role = self.userDao.findFileSystemByName(name)
        self.assertEqual(role['id'], file_id)

        self.userDao.removeFileSystem(file_id)

        role = self.userDao.findFileSystemByName(name)
        self.assertIsNone(role)

    def test_001b_filesystem_permission(self):

        name = "test"
        path = "file:///opt/yueserver"
        file_id = self.userDao.createFileSystem(name, path)

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
        self.storageDao.insert(user_id, "file:///file1.txt", 1234, 0)
        self.storageDao.insert(user_id, "file:///folder/file2.txt", 1234, 0)

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

    def test_005a_abspath(self):
        user_id = self.USER['id']
        role_id = self.USER['role_id']

        root = "abspath"
        path = "mem:///opt/yueserver/data"
        name = "file1.txt"

        file_id = self.userDao.createFileSystem(root, path)
        self.userDao.addFileSystemToRole(role_id, file_id)

        # compose an absolute path given a user role
        abspath = self.storageDao.absolutePath(user_id, role_id, root, name)
        self.assertEqual(path + "/" + name, abspath)

        # permission denied, invalid role
        with self.assertRaises(StorageException):
            abspath = self.storageDao.absolutePath(user_id, -1, root, name)

        # root does not exist
        with self.assertRaises(StorageException):
            abspath = self.storageDao.absolutePath(user_id, role_id, "dne", name)

    def test_005a_abspath_sub(self):
        user_id = self.USER['id']
        role_id = self.USER['role_id']

        root = "abspath"
        path = "mem:///opt/yueserver/user/{user_id}"
        name = "file1.txt"

        file_id = self.userDao.createFileSystem(root, path)
        self.userDao.addFileSystemToRole(role_id, file_id)

        abspath = self.storageDao.absolutePath(user_id, role_id, root, name)
        expected = "mem:///opt/yueserver/user/%s/%s" % (user_id, name)
        self.assertEqual(expected, abspath)

    def test_006_quota(self):
        """
        show that adding files increases the disk usage of a user
        """
        user_id = self.USER['id']

        count, usage = self.storageDao.userDiskUsage(self.USER['id'])
        self.assertEqual(0, count)
        self.assertEqual(0, usage)

        self.storageDao.insert(user_id, "file:///file1.txt", 1024, 0)
        count, usage = self.storageDao.userDiskUsage(user_id)
        self.assertEqual(1, count)
        self.assertEqual(1024, usage)

        self.storageDao.insert(user_id, "file:///file2.txt", 512, 0)
        count, usage = self.storageDao.userDiskUsage(user_id)
        self.assertEqual(2, count)
        self.assertEqual(1536, usage)

        self.storageDao.remove(user_id, "file:///file1.txt")
        count, usage = self.storageDao.userDiskUsage(user_id)
        self.assertEqual(1, count)
        self.assertEqual(512, usage)

    # todo:
    #   test that a user cannot CRUD other users files
    #   rename when dst already exists should fail

def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(StorageTestCase)
    unittest.TextTestRunner().run(suite)

if __name__ == '__main__':
    main()