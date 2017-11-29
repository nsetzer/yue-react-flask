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

        app = self.login(self.USERNAME, self.PASSWORD)
        url = "/api/library/%s" % self.SONG['id']
        res = app.get(url)
        body = json.loads(res.data)
        song = body['result']

        self.assertIsNotNone(song)
        self.assertEqual(song['artist'], 'Artist000')


