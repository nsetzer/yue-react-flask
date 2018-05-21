import os
import unittest
import tempfile
import json

from .db import db_connect, db_populate, db_repopulate, \
    db_init_main, db_update_main, ConfigException, yaml_assert
from .user import UserDao
from .library import Song, LibraryDao
from .util import CaptureOutput

class ManageDBTestCase(unittest.TestCase):

    db_name = "ManageDBTestCase"

    @classmethod
    def setUpClass(cls):

        cls.db_path = "database.test.%s.sqlite" % cls.db_name

        db = db_connect(None)

        cls.userDao = UserDao(db, db.tables)
        cls.libraryDao = LibraryDao(db, db.tables)

        cls.env_cfg = {
            'features': [
                'read_user', 'write_user', 'create_user',
                'read_song_record', 'write_song_record',
                'read_song', 'write_song', 'read_filesystem'
            ],
            'domains': ['production'],
            'roles': [
                {'user': {'features': [
                    'read_user']}},
                {'editor': {'features': [
                    'read_user', 'write_user']}},
                {'admin': {'features': ['all']}}
            ],
            'users': [
                {'email': 'admin',
                 'password': 'admin',
                 'domains': ['production'],
                 'roles': ['admin']},
                {'email': 'user000',
                 'password': 'user000',
                 'domains': ['production'],
                 'roles': ['user']},
                {'email': 'user001',
                 'password': 'user001',
                 'domains': ['production'],
                 'roles': ['user']},
                {'email': 'user002',
                 'password': 'user002',
                 'domains': ['production'],
                 'roles': ['user']}
            ]
        }

        # initilize the environment
        db_init_main(db, db.tables, cls.env_cfg)

        cls.db = db

        cls.user = cls.userDao.findUserByEmail("user000")
        cls.user_name = cls.user['email']
        cls.domain_name = cls.userDao.findDomainById( \
            cls.user['domain_id'])['name']

        cls.user_id = cls.user['id']
        cls.domain_id = cls.user['domain_id']

        cls.songs = []
        for i in range(10):
            song = {
                Song.artist : "artist%d" % i,
                Song.title : "album%d" % i,
                Song.album : "title%d" % i,
                Song.rating : i%10,
                Song.path : "/dev/null",
                Song.ref_id : "id%06d" % i
            }
            cls.songs.append(song)


    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        pass
    def tearDown(self):
        pass

    def test_000_validate(self):
        roles = self.userDao.listRoles()
        self.assertEqual(len(roles), len(self.env_cfg['roles']))

        domains = self.userDao.listDomains()
        self.assertEqual(len(domains), len(self.env_cfg['domains']))

        for domain in domains:
            users = self.userDao.listUsers(domain.id)
            self.assertEqual(len(users), len(self.env_cfg['users']))

    def test_000a_validate_yaml(self):

        data = self.env_cfg.copy()
        data['features'] = [1, 2, 3]

        with self.assertRaises(ConfigException):
            yaml_assert(data)

        data['features'] = None
        with self.assertRaises(ConfigException):
            yaml_assert(data)

        data = self.env_cfg.copy()
        data['roles'] = None
        with self.assertRaises(ConfigException):
            yaml_assert(data)

        # the listed features for a role must match the features list
        data = self.env_cfg.copy()
        data['roles'] = [{'user': {'features': ['dne']}}]
        with self.assertRaises(ConfigException):
            yaml_assert(data)

        # users must have all parameters set correctly
        user1 = {'password': 'admin',
                 'domains': ['production'],
                 'roles': ['admin']}

        user2 = {'email': 'admin',
                 'domains': ['production'],
                 'roles': ['admin']}

        user3 = {'email': 'admin',
                 'password': 'admin',
                 'roles': ["user"]}

        user4 = {'email': 'admin',
                 'password': 'admin',
                 'domains': [None]}

        for user in [user1, user2, user3, user4]:
            data = self.env_cfg.copy()
            data['users'] = [user]
            with self.assertRaises(ConfigException):
                yaml_assert(data)

    def test_001_db_populate(self):

        db = self.db

        # check that the database is empty
        results = self.libraryDao.search(self.user_id, self.domain_id, "")
        self.assertEqual(len(results), 0,
            "%d/%d" % (len(results), 0))

        db_populate(db, db.tables, \
            self.user_name, self.domain_name, self.songs)

        # check that the songs were added to the database
        results = self.libraryDao.search(self.user_id, self.domain_id, "")
        self.assertEqual(len(results), len(self.songs),
            "%d/%d" % (len(results), len(self.songs)))

    def test_002_db_repopulate(self):

        db = self.db
        # update the original song meta data, and repopulate
        for song in self.songs:
            song[Song.rating] = 10 - song[Song.rating]

        self.assertTrue(db_repopulate(db, db.tables,
            self.user_name, self.domain_name, self.songs))

        # check that the songs were added to the database
        results = self.libraryDao.search(self.user_id, self.domain_id, "")
        self.assertEqual(len(results), len(self.songs),
            "%d/%d" % (len(results), len(self.songs)))

        songmap = {song[Song.ref_id]: song for song in results}

        # check that the values in the database were updated.
        for song in self.songs:
            song2 = songmap[song[Song.ref_id]]
            self.assertEqual(song[Song.rating], song2[Song.rating])

    def test_002a_db_repopulate_invalid_domain(self):

        db = self.db
        # update the original song meta data, and repopulate
        for song in self.songs:
            song[Song.rating] = 10 - song[Song.rating]

        with CaptureOutput() as cap:
            self.assertFalse(db_repopulate(db, db.tables,
                self.user_name, "dne", self.songs))

            self.assertEqual(cap.stderr().strip(),
                             "Domain with name `dne` not found")

    def test_002b_db_repopulate_invalid_name(self):

        db = self.db
        # update the original song meta data, and repopulate
        for song in self.songs:
            song[Song.rating] = 10 - song[Song.rating]

        with CaptureOutput() as cap:
            self.assertFalse(db_repopulate(db, db.tables,
                "dne", self.domain_name, self.songs))

            self.assertEqual(cap.stderr().strip(),
                             "User with name `dne` not found")

    def test_003_db_update(self):
        db = self.db

        # updating the environment with the same config should change nothing
        n_changes = db_update_main(db, db.tables, self.env_cfg)
        self.assertEqual(n_changes, 0, "changes: %d" % n_changes)

        # modify the environment config and validate that the
        # changes were performed correctly
        self.env_cfg['features'] = ['read_user', 'write_user', 'delete_user']
        n_changes = db_update_main(db, db.tables, self.env_cfg)
        # todo, check that roles were updated, features changed
        self.assertEqual(n_changes, 8, "changes: %d" % n_changes)

        self.env_cfg['domains'] = ['test', ]
        n_changes = db_update_main(db, db.tables, self.env_cfg)
        self.assertEqual(n_changes, 1, "changes: %d" % n_changes)

        role = {'test': {'features': ['delete_user', ]}}
        self.env_cfg['roles'].append(role)
        n_changes = db_update_main(db, db.tables, self.env_cfg)
        self.assertEqual(n_changes, 1, "changes: %d" % n_changes)

def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ManageDBTestCase)
    unittest.TextTestRunner().run(suite)

if __name__ == '__main__':
    main()
