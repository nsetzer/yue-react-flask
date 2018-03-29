import os
import unittest
import tempfile
import json

from .config import db_init_main, db_update_main
from .managedb import db_connect, db_populate, db_repopulate
from ..dao.user import UserDao
from ..dao.library import Song, LibraryDao

class ManageDBTestCase(unittest.TestCase):

    db_name = "ManageDBTestCase"

    @classmethod
    def setUpClass(cls):

        cls.db_path = "database.test.%s.sqlite" % cls.db_name

        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)

        db = db_connect("sqlite:///" + cls.db_path)

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
                {'user': { 'features': [
                    'read_user',]}},
                {'editor': {'features': [
                    'read_user', 'write_user',]}},
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
        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)

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

        db_repopulate(db, db.tables, \
            self.user_name, self.domain_name, self.songs)

        # check that the songs were added to the database
        results = self.libraryDao.search(self.user_id, self.domain_id, "")
        self.assertEqual(len(results), len(self.songs),
            "%d/%d" % (len(results), len(self.songs)))

        songmap = {song[Song.ref_id]:song for song in results}

        # check that the values in the database were updated.
        for song in self.songs:
            song2 = songmap[song[Song.ref_id]]
            self.assertEqual(song[Song.rating], song2[Song.rating])

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

def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ManageDBTestCase)
    unittest.TextTestRunner().run(suite)
