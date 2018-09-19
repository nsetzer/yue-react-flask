

import os
import unittest
import tempfile
import json
import time

from .db import db_init_main, db_connect
from .user import UserDao
from .storage import StorageDao

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
                {'email': 'user001',
                 'password': 'user001',
                 'domains': ['test'],
                 'roles': ['test']},
                {'email': 'user002',
                 'password': 'user002',
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

    def test_002a_insert_test(self):

        user_id = self.USER['id']

        self.storageDao.insert(user_id, "file:///file1.txt", 1234, 1234567890)
        self.storageDao.insert(user_id, "file:///folder/file2.txt", 1234, 1234567890)
        for rec in self.storageDao.listdir(user_id, "file:///"):
            print(rec)

def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(StorageTestCase)
    unittest.TextTestRunner().run(suite)

if __name__ == '__main__':
    main()