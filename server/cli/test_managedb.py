import os
import unittest
import tempfile
import json

from .config import db_init_main, db_update_main
from .managedb import db_connect, db_populate, db_repopulate
from ..dao.user import UserDao
from ..dao.library import Song, LibraryDao

class ManageDBTestCase(unittest.TestCase):

    def setUp(self):
        super().setUp()

    def tearDown(self):
        pass

    def test_db_populate(self):

        db_path = "database.test.sqlite"

        if os.path.exists(db_path):
            os.remove(db_path)

        db = db_connect("sqlite:///" + db_path)

        userDao = UserDao(db, db.tables)
        libraryDao = LibraryDao(db, db.tables)

        env_cfg = {
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
        db_init_main(db, db.tables, env_cfg)

        # validate the environment config was applied correctly
        roles = userDao.listRoles()
        self.assertEqual(len(roles), len(env_cfg['roles']))

        domains = userDao.listDomains()
        self.assertEqual(len(domains), len(env_cfg['domains']))

        for domain in domains:
            users = userDao.listUsers(domain.id)
            self.assertEqual(len(users), len(env_cfg['users']))

        # populate the database with some songs
        songs = []
        for i in range(10):
            song = {
                Song.artist : "artist%d" % i,
                Song.title : "album%d" % i,
                Song.album : "title%d" % i,
                Song.rating : i%10,
                Song.path : "/dev/null",
                Song.ref_id : "id%06d" % i
            }
            songs.append(song)

        user = userDao.findUserByEmail("user000")
        domain_name = userDao.findDomainById(user['domain_id'])['name']

        # check that the database is empty
        results = libraryDao.search(user['id'], user['domain_id'], "")
        self.assertEqual(len(results), 0,
            "%d/%d" % (len(results), 0))

        db_populate(db, db.tables, user['email'], domain_name, songs)

        # check that the songs were added to the database
        results = libraryDao.search(user['id'], user['domain_id'], "")
        self.assertEqual(len(results), len(songs),
            "%d/%d" % (len(results), len(songs)))

        # update the original song meta data, and repopulate
        for song in songs:
            song[Song.rating] = 10 - song[Song.rating]
        db_repopulate(db, db.tables, user['email'], domain_name, songs)
        #TODO: verify that the songs fields were updated.

        # updating the environment with the same config should change nothing
        n_changes = db_update_main(db, db.tables, env_cfg)
        self.assertEqual(n_changes, 0, "changes: %d" % n_changes)

        # modify the environment config and validate that the
        # changes were performed correctly
        env_cfg['features'] = ['read_user', 'write_user', 'delete_user']
        n_changes = db_update_main(db, db.tables, env_cfg)
        # todo, check that roles were updated, features changed
        self.assertEqual(n_changes, 8, "changes: %d" % n_changes)

    def test_db_repopulate(self):
        return

def main():
    test = ManageDBTestCase()
    test.test_db_populate()
