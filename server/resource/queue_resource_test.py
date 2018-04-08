import os
import unittest
import json
import time

from ..app import TestApp
from ..dao.library import Song

class QueueResourceTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        cls.app = TestApp(cls.__name__);

        cls.app.create_test_songs()

    @classmethod
    def tearDownClass(cls):
        cls.app.tearDown()

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_001_set_get(self):

        song_ids = self.app.SONGIDS[:5]
        username = "user000"
        with self.app.login(username, username) as app:
            result = app.post_json("/api/queue", song_ids)
            self.assertEqual(result.status_code, 200, result)

            songs = app.get_json("/api/queue")
            self.assertEqual(len(songs), len(song_ids))

            for i, song in enumerate(songs):
                self.assertEqual(song[Song.id], song_ids[i])

    def test_002_queue_populate(self):

        username = "user000"
        with self.app.login(username, username) as app:
            songs = app.get_json('/api/queue/populate')

            self.assertNotEqual(len(songs), 0)

    def test_003_create(self):

        limit = 5
        username = "user000"
        with self.app.login(username, username) as app:
            qs = {"query": "artist=000", "limit": limit}
            songs = app.get_json('/api/queue/create', query_string=qs)

            self.assertEqual(len(songs), limit)
            for song in songs:
                self.assertEqual(song[Song.artist], "Artist000")

            # limit out of range
            qs = {"query": "artist=000", "limit": -1}
            result = app.get('/api/queue/create', query_string=qs)
            self.assertEqual(result.status_code, 400, result)

            qs = {"query": "artist=000", "limit": 54321}
            result = app.get('/api/queue/create', query_string=qs)
            self.assertEqual(result.status_code, 400, result)



def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(QueueResourceTestCase)
    unittest.TextTestRunner().run(suite)

if __name__ == '__main__':
    main()
