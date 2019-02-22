import os
import sys
import unittest

from ..dao.db import main_test, db_connect, db_init_main
from .settings import SettingsDao

class SettingsTestCase(unittest.TestCase):

    db_name = "SettingsTestCase"

    @classmethod
    def setUpClass(cls):
        # build a test database, with a minimal configuration
        cls.db_path = "database.test.%s.sqlite" % cls.db_name

        db = db_connect(None)

        env_cfg = {
            'features': ['test', ],
            'domains': ['test'],
            'filesystems': {},
            'roles': [
                {'test': {'features': ['all'], 'filesystems': []}},
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

        cls.db = db

    def test_settings(self):

        dao = SettingsDao(self.db, self.db.tables)

        self.assertFalse(dao.has("test"))

        dao.set("test", "1234")
        self.assertTrue(dao.has("test"))
        self.assertEqual(dao.get("test"), "1234")

        dao.set("test", "5678")
        self.assertTrue(dao.has("test"))
        self.assertEqual(dao.get("test"), "5678")

if __name__ == '__main__':
    main_test(sys.argv, globals())

