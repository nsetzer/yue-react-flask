import os
import unittest
import tempfile
import json

from .user import UserDao
from .library import Song, LibraryDao
from .queue import SongQueueDao
from .db import db_connect, db_remove, db_init_main

class SongQueueTestCase(unittest.TestCase):

    db_name = "SongQueueTestCase"

    @classmethod
    def setUpClass(cls):
        # build a test database, with a minimal configuration
        cls.db_path = "database.test.%s.sqlite" % cls.db_name

        db = db_connect(None)

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

        cls.queue = SongQueueDao(db, db.tables)

        cls.libraryDao = LibraryDao(db, db.tables)

        cls.SONGS = []
        for a in range(3):
            for b in range(3):
                for t in range(3):
                    song = {
                        Song.artist: "Artist%03d" % a,
                        Song.album: "Album%03d" % b,
                        Song.title: "Title%03d" % t,
                    }
                    cls.SONGS.append(song)

        cls.SONG_IDS = []
        for song in cls.SONGS:
            song_id = cls.libraryDao.insert(\
                cls.USER['id'], cls.USER['domain_id'], song)
            cls.SONG_IDS.append(song_id)

    @classmethod
    def tearDownClass(cls):
        pass

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

        self.queue.set(user_id, domain_id, self.SONG_IDS)

        item = self.queue.head(user_id, domain_id)
        self.assertEqual(item['id'], self.SONG_IDS[0])

    def test_queue_rest(self):

        user_id = self.USER['id']
        domain_id = self.USER['domain_id']

        self.queue.set(user_id, domain_id, self.SONG_IDS)

        items = self.queue.rest(user_id, domain_id)
        self.assertIsNotNone(items)
        self.assertEqual(len(items), len(self.SONG_IDS) - 1)
        for item, song_id in zip(items, self.SONG_IDS[1:]):
            self.assertEqual(item['id'], song_id)

    def test_queue_get(self):

        user_id = self.USER['id']
        domain_id = self.USER['domain_id']

        self.queue.set(user_id, domain_id, self.SONG_IDS)

        items = self.queue.get(user_id, domain_id)
        self.assertIsNotNone(items)
        self.assertEqual(len(items), len(self.SONG_IDS))
        for item, song_id in zip(items, self.SONG_IDS):
            self.assertEqual(item['id'], song_id)

def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SongQueueTestCase)
    unittest.TextTestRunner().run(suite)

if __name__ == '__main__':
    main()

