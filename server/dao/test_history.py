import os
import unittest
import tempfile
import json
import datetime

from .user import UserDao
from .library import Song, LibraryDao
from .history import HistoryDao

from .db import db_connect, db_remove, db_init_main

class SongHistoryTestCase(unittest.TestCase):

    db_name = "SongHistoryTestCase"

    @classmethod
    def setUpClass(cls):
        # build a test database, with a minimal configuration
        cls.db_path = "database.test.%s.sqlite" % cls.db_name

        if not db_remove(cls.db_path):
            raise RuntimeError("Unable to remove database: %s" % csl.db_path)

        db = db_connect("sqlite:///" + cls.db_path)

        env_cfg = {
            'features': ['test', ],
            'domains': ['test'],
            'roles': [
                {'test': { 'features': ['all',]}},
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

        cls.db = db

        cls.history = HistoryDao(db, db.tables)

        cls.libraryDao = LibraryDao(db, db.tables)

        cls.SONGS = []
        for a in range(3):
            for b in range(3):
                for t in range(3):
                    song = {
                        Song.artist: "Artist%03d" % a,
                        Song.album: "Album%03d" % b,
                        Song.title: "Title%03d" % t,
                        Song.id: "id%06d" % len(cls.SONGS),
                        Song.ref_id: "id%06d" % len(cls.SONGS),
                    }
                    cls.SONGS.append(song)

    @classmethod
    def tearDownClass(cls):
        db_remove(cls.db_path)

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def setUp(self):
        super().setUp()

    def tearDown(self):
        pass

    def test_queue_head(self):

        user_id = self.USER['id']
        domain_id = self.USER['domain_id']

        for song in self.SONGS:
            timestamp = int(datetime.datetime.now().timestamp())
            self.history.insert(user_id, song[Song.id], timestamp)

        start = (datetime.datetime.now() -
            datetime. timedelta(days=1)).timestamp()

        end = datetime.datetime.now().timestamp() + 1

        records = self.history.retrieve(user_id, start)
        self.assertEqual(len(records), len(self.SONGS))

        records = self.history.retrieve(user_id, start, end)
        self.assertEqual(len(records), len(self.SONGS))

def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SongHistoryTestCase)
    unittest.TextTestRunner().run(suite)

if __name__ == '__main__':
    main()
