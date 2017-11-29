import os
import unittest
import tempfile
import json

from ..util import TestCase

from ..dao.library import Song
from ..app import app, db

class xLibraryEndpointTestCasex(TestCase):

    def setUp(self):
        super().setUp()

    def tearDown(self):
        pass

    def test_get_song_by_id(self):

        user_id = self.USER['id']
        domain_id = self.USER['domain_id']

        song = {
            "artist": "test",
            "title": "test",
            "album": "test",
            "comment": "test",
        }

        # uid = self.LIBRARY.insert(user_id, domain_id, song)

        # song = self.LIBRARY.findSongById(user_id, domain_id, uid)
        # print(song)
        # songs = self.LIBRARY._query(user_id, domain_id)
        # print("found: %s" % len(songs))

        # app = self.login(self.USERNAME, self.PASSWORD)
        # url = "/api/library/%s" % uid
        # res = app.get(url)
        # body = json.loads(res.data)
        # song = body['result']

        # songs = self.LIBRARY._query(user_id, domain_id)
        # print("found: %s" % len(songs))

        # self.assertIsNotNone(song)
        # self.assertEqual(song['artist'], 'test')

        # for field in Song.fields():
        #     self.assertTrue(field in song, field)

