import os
import unittest
import tempfile
import json

from ..util import TestCase

from ..dao.library import Song
from ..app import app, db


from io import BytesIO
import gzip
import datetime

"""

curl -u admin:admin
     -H"Accept-Encoding: gzip"
     http://localhost:4200/api/library/info
     -o out.zip

"""

class LibraryEndpointTestCase(TestCase):

    def setUp(self):
        super().setUp()

    def tearDown(self):
        pass

    def test_get_song_by_id(self):

        app = self.login(self.USERNAME, self.PASSWORD)
        url = "/api/library/%s" % self.SONG['id']
        res = app.get(url)
        body = json.loads(res.data.decode("utf-8"))
        song = body['result']

        self.assertIsNotNone(song)
        self.assertEqual(song['artist'], 'Artist000')

    def test_search_by_page(self):

        # the search has a default ordering (by artist)

        app = self.login(self.USERNAME, self.PASSWORD)

        # first run a query determining all songs
        # (assumes fewer songs than the default query limit)
        # this should be 29
        url = "/api/library?query=Artist"
        res = app.get(url)
        songs = json.loads(res.data.decode("utf-8"))['result']

        # slightly more than half of the documents...
        page_size = 1 + len(songs) // 2

        url = "/api/library?query=Artist&limit=%d" % page_size
        res = app.get(url)
        body = json.loads(res.data.decode("utf-8"))
        self.assertEqual(body['page_size'], page_size)
        songs_a = body['result']
        self.assertEqual(len(songs_a), page_size)

        url = "/api/library?query=Artist&limit=%d&page=1" % page_size
        res = app.get(url)
        body = json.loads(res.data.decode("utf-8"))
        self.assertEqual(body['page_size'], page_size)
        songs_b = body['result']
        # remaining documents is less than a full page by design
        self.assertNotEqual(len(songs_b), page_size)

        # none of the songs in the first page should be in the second
        for songb in songs_b:
            for songa in songs_a:
                self.assertNotEqual(songb['id'], songa['id'])

    def test_domain_info_compressed(self):

        app = self.login(self.USERNAME, self.PASSWORD)

        url = "/api/library/info"
        res = app.get(url, headers={"Accept-Encoding": "gzip"})

        data = gzip.decompress(res.data)
        result = json.loads(data.decode("utf-8"))['result']

        self.assertTrue('artists' in result)
        self.assertTrue('genres' in result)
        self.assertTrue('num_songs' in result)

    def test_domain_info(self):

        app = self.login(self.USERNAME, self.PASSWORD)

        url = "/api/library/info"
        res = app.get(url)

        result = json.loads(res.data.decode("utf-8"))['result']

        self.assertTrue('artists' in result)
        self.assertTrue('genres' in result)
        self.assertTrue('num_songs' in result)

    def test_post_history(self):
        """
        test that a user can send data records to update plaback history
        """
        records = [
            {"song_id": self.SONGS[0],
             "timestamp": 1000},
        ]

        app = self.login(self.USERNAME, self.PASSWORD)
        url = "/api/library/history"
        result = app.post_json(url, records)

        self.assertEqual(result.status_code, 200)

        # attempt a query using unix epoch time stamps
        start = 0
        end = 2000
        _records = app.get_json(url + "?start=%d&end=%d" % (start, end))
        n_records = len(_records)
        self.assertTrue(n_records > 0)

        # attempt a query using iso date format
        start = datetime.datetime.fromtimestamp(start).isoformat()
        end = datetime.datetime.fromtimestamp(end).isoformat()
        _records = app.get_json(url + "?start=%s&end=%s" % (start, end))
        self.assertEqual(len(_records), n_records)

        # perform a double post
        app = self.login(self.USERNAME, self.PASSWORD)
        url = "/api/library/history"
        result = app.post_json(url, records)

        # this should return the same number of records as before
        # the double post should de-duplicate
        start = 0
        end = 2000
        _records = app.get_json(url + "?start=%d&end=%d" % (start, end))
        self.assertEqual(len(_records), n_records)

    def test_get_audio(self):
        """
        test getting audio for a song, this will 404 since the audio path
        is not set. It should not fail with 401 or some other error.

        TODO: consider setting default audio path to /dev/null
        """

        apikey = self.USER['apikey']
        songid = self.SONGS[0]

        url = "/api/library/%s/audio?apikey=%s" % (songid, apikey)
        res = self.app.get(url)

        self.assertEqual(res.status_code, 404)

    def test_get_art(self):
        """
        test getting audio for a song, this will 404 since the audio path
        is not set. It should not fail with 401 or some other error.

        TODO: consider setting default audio path to /dev/null
        """

        apikey = self.USER['apikey']
        songid = self.SONGS[0]

        url = "/api/library/%s/art?apikey=%s" % (songid, apikey)
        res = self.app.get(url)

        self.assertEqual(res.status_code, 404)









