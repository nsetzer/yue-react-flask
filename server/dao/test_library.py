import os
import unittest
import tempfile
import json

from ..util import TestCase

from .user import UserDao
from .library import Song, LibraryDao

from ..app import app, db, dbtables

class LibraryTestCase(unittest.TestCase):

    def setUp(self):
        super().setUp()

        self.userDao = UserDao(db, dbtables)

        self.USERNAME = "user000"
        self.USER = self.userDao.findUserByEmail(self.USERNAME)

        self.lib = LibraryDao(db, dbtables)

    def tearDown(self):
        pass

    def test_get_song_by_id(self):

        user_id = self.USER['id']
        domain_id = self.USER['domain_id']

        song = {
            "artist": "test",
            "title": "test",
            "album": "test",
        }

        uid = self.lib.insert(user_id, domain_id, song)

        # show that we can find a song given an ID
        song2 = self.lib.findSongById(user_id, domain_id, uid)
        for key, value in song.items():
            self.assertEqual(song2[key], song[key], key)
        self.assertEqual(song2['id'], uid, "id")

        # test domain filter
        song3 = self.lib.findSongById(user_id, -1, uid)
        self.assertIsNone(song3)

    def test_all_text_search(self):
        user_id = self.USER['id']
        domain_id = self.USER['domain_id']

        songs = self.lib.search(user_id, domain_id, "Artist000")

        self.assertEqual(len(songs), 3)

        for song in songs:
            self.assertEqual(song[Song.artist], "Artist000")

    def test_simple_search(self):
        user_id = self.USER['id']
        domain_id = self.USER['domain_id']

        songs = self.lib.search(user_id, domain_id, "art=Artist000")

        self.assertEqual(len(songs), 3)

        for song in songs:
            self.assertEqual(song[Song.artist], "Artist000")



