import os
import unittest
import tempfile
import json
import time

from ..cli.managedb import db_connect
from ..cli.config import db_init_main

from .user import UserDao
from .library import Song, LibraryDao

class LibraryTestCase(unittest.TestCase):

    db_name = "LibraryTestCase"

    @classmethod
    def setUpClass(cls):
        # build a test database, with a minimal configuration
        cls.db_path = "database.test.%s.sqlite" % cls.db_name

        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)

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

        cls.libraryDao = LibraryDao(db, db.tables)

        cls.songs = []
        for a in range(3):
            for b in range(3):
                for t in range(3):
                    song = {
                        Song.artist: "Artist%03d" % a,
                        Song.album: "Album%03d" % b,
                        Song.title: "Title%03d" % t,
                        Song.ref_id: "id%06d" % ((a+1)*100 + (b+1)*10 + (t+1)),
                    }
                    cls.songs.append(song)

        cls.db = db


    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_001_get_song_by_id(self):

        user_id = self.USER['id']
        domain_id = self.USER['domain_id']

        song = {
            "artist": "test",
            "title": "test",
            "album": "test",
        }

        uid = self.libraryDao.insert(user_id, domain_id, song)

        # show that we can find a song given an ID
        song2 = self.libraryDao.findSongById(user_id, domain_id, uid)
        for key, value in song.items():
            self.assertEqual(song2[key], song[key], key)
        self.assertEqual(song2['id'], uid, "id")

        # test domain filter
        song3 = self.libraryDao.findSongById(user_id, -1, uid)
        self.assertIsNone(song3)

    def test_002_insert_songs(self):
        user_id = self.USER['id']
        domain_id = self.USER['domain_id']


        for song in self.songs:
            self.libraryDao.insert(user_id, domain_id, song)

    def test_002a_all_text_search(self):
        user_id = self.USER['id']
        domain_id = self.USER['domain_id']


        songs = self.libraryDao.search(user_id, domain_id, "Artist000")

        self.assertEqual(len(songs), 9)

        for song in songs:
            self.assertEqual(song[Song.artist], "Artist000")

    def test_002b_simple_search(self):
        user_id = self.USER['id']
        domain_id = self.USER['domain_id']

        songs = self.libraryDao.search(user_id, domain_id, "art=Artist000")

        self.assertEqual(len(songs), 9)

        for song in songs:
            self.assertEqual(song[Song.artist], "Artist000")

    def test_002c_search_limit(self):
        user_id = self.USER['id']
        domain_id = self.USER['domain_id']
        limit = 4

        songs = self.libraryDao.search(user_id, domain_id,
            "Artist000", limit=limit)

        self.assertEqual(len(songs), limit)

        for song in songs:
            self.assertEqual(song[Song.artist], "Artist000")

    def test_002d_search_order_string(self):

        user_id = self.USER['id']
        domain_id = self.USER['domain_id']

        songs = self.libraryDao.search(user_id, domain_id,
            "Artist", orderby="artist")

        songs2 = [s['artist'] for s in songs]
        songs2.sort()

        for s1, s2 in zip(songs, songs2):
            self.assertEqual(s1['artist'], s2)

    def test_002e_search_order_forward(self):

        user_id = self.USER['id']
        domain_id = self.USER['domain_id']

        songs = self.libraryDao.search(user_id, domain_id,
            "Artist", orderby=[("artist", "ASC")])

        songs2 = [s['artist'] for s in songs]
        songs2.sort()

        for s1, s2 in zip(songs, songs2):
            self.assertEqual(s1['artist'], s2)

    def test_002f_search_order_reverse(self):

        user_id = self.USER['id']
        domain_id = self.USER['domain_id']

        songs = self.libraryDao.search(user_id, domain_id,
            "Artist", orderby=[("artist", "DESC")])

        songs2 = [s['artist'] for s in songs]
        songs2.sort(reverse=True)

        for s1, s2 in zip(songs, songs2):
            self.assertEqual(s1['artist'], s2)

    def test_003_bulk_upsert(self):

        # generate 1000 songs to insert
        songs = []
        for a in range(10):
            for b in range(10):
                for t in range(10):
                    song = {
                        Song.artist: "bulk%03d" % a,
                        Song.album: "bulk%03d" % b,
                        Song.title: "bulk%03d" % t,
                        Song.ref_id: "bulk%06d" % len(songs),
                    }
                    songs.append(song)

        # first upsert inserts 1000 records
        s = time.time()
        self.libraryDao.bulkUpsertByRefId( \
            self.USER['id'], self.USER['domain_id'], songs)
        e = time.time()
        #print( len(songs), len(songs)/(e-s), (e-s) )

        # second upsert updates the values instead
        s = time.time()
        self.libraryDao.bulkUpsertByRefId( \
            self.USER['id'], self.USER['domain_id'], songs)
        e = time.time()
        #print( len(songs), len(songs)/(e-s), (e-s) )

        #TODO: build a performance benchmark test
        # this test should write to stderr if the performance
        # changes between runs. cache results to the local file system
        return

def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(LibraryTestCase)
    unittest.TextTestRunner().run(suite)

