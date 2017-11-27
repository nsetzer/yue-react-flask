import os
import unittest
import tempfile
import json

from ..util import TestCase

from .song import Song, Library, LibraryException
from .user import User

class SongModelTestCase(TestCase):

    def setUp(self):
        super().setUp()

        username = "user000"
        self.user = User.get_user_with_email(username)
        self.lib = Library(self.user.id, self.user.domain_id)

    def tearDown(self):
        pass

    def test_get_song_by_id(self):

        song = self.lib.findSongById(self.SONG['id'])

        for field in Song.fields():
            self.assertEqual(song[field], self.SONG[field], field)

    def test_domain_filter(self):
        """return none when an unknown domain is used"""
        lib = Library(self.user.id, -1)

        with self.assertRaises(LibraryException):
            lib.findSongById(self.SONG['id'])

    def test_all_text_search(self):
        songs = self.lib.search("Artist000")

        self.assertEqual(len(songs), 3)

        for song in songs:
            self.assertEqual(song[Song.artist], "Artist000")

    def test_simple_search(self):
        songs = self.lib.search("art=Artist000")

        self.assertEqual(len(songs), 3)

        for song in songs:
            self.assertEqual(song[Song.artist], "Artist000")



