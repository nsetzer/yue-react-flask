

import os
import unittest
import tempfile
import json
import time

from .db import db_init_main, db_connect
from .user import UserDao
from .storage import StorageDao

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


    def test_001a_insert_test(self):

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