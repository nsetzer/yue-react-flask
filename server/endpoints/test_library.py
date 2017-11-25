import os
import unittest
import tempfile
import json

from ..util import TestCase

class LibraryTestCase(TestCase):

    def setUp(self):
        super().setUp();

    def tearDown(self):
        pass

    def test_get_song_by_id(self):

        url = "/api/library/%s"%self.SONG.id
        res = self.app.get(url);
        body = json.loads(res.data)
        print(body)