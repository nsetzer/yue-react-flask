import os
import unittest
import tempfile
import json

from ..util import TestCase

from ..dao.library import Song
from ..dao.queue import SongQueueDao

from ..app import app, db, dbtables

class LibraryEndpointTestCase(TestCase):

    def setUp(self):
        super().setUp()

        user_id = self.USER['id']
        domain_id = self.USER['domain_id']

        self.queue = SongQueueDao(db, dbtables)

        self.queue.set(user_id, domain_id, [])

    def tearDown(self):
        pass

    def test_queue(self):

        app = self.login(self.USERNAME, self.PASSWORD)

        songs = app.get_json("/api/queue")
        self.assertEqual(len(songs), 0)

        songs = app.get_json("/api/queue/populate")
        self.assertNotEqual(len(songs), 0)

        song_ids1 = [song['id'] for song in songs[:5]]

        # set the queue to a random set of songs
        app.post_json("/api/queue", song_ids1)

        # check that setting the queue succeeded
        songs = app.get_json("/api/queue")
        song_ids2 = [song['id'] for song in songs]

        self.assertEqual(len(song_ids1), len(song_ids2))

        for a, b in zip(song_ids1, song_ids2):
            self.assertEqual(a, b)

    def test_queue_create(self):

        app = self.login(self.USERNAME, self.PASSWORD)

        url = "/api/queue/create"
        songs = app.get_json(url)
        self.assertGreater(len(songs), 0)

        url = "/api/queue/create?query=artist=Artist000&limit=5"
        songs = app.get_json(url)
        self.assertEqual(len(songs), 5)







