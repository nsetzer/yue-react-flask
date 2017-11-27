import os
import unittest
import tempfile
import json

from ..util import TestCase

from ..models.song import Song

class LibraryTestCase(TestCase):

    def setUp(self):
        super().setUp()

    def tearDown(self):
        pass

    def test_get_song_by_id(self):

        email = "user000"
        password = "user000"
        app = self.login(email, password)
        url = "/api/library/%s" % self.SONG['id']
        res = app.get(url)
        body = json.loads(res.data)

        song = body['result']
        self.assertEqual(song['artist'], 'Artist000')

        for field in Song.fields():
            self.assertTrue(field in song, field)

