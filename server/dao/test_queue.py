import os
import unittest
import tempfile
import json

from ..util import TestCase

from .queue import SongQueue

from ..app import app, db

class SongQueueTestCase(TestCase):

    def setUp(self):
        super().setUp()

        self.queue = SongQueue(db, self.USER['id'], self.USER['domain_id'])

    def tearDown(self):
        pass

    def test_queue_head(self):

        self.queue.set(self.SONGS)

        item = self.queue.head()
        self.assertEqual(item['id'], self.SONGS[0])

    def test_queue_rest(self):

        self.queue.set(self.SONGS)

        items = self.queue.rest()
        self.assertIsNotNone(items)
        self.assertEqual(len(items), len(self.SONGS) - 1)
        for item, song_id in zip(items, self.SONGS[1:]):
            self.assertEqual(item['id'], song_id)

    def test_queue_get(self):

        self.queue.set(self.SONGS)

        items = self.queue.get()
        self.assertIsNotNone(items)
        self.assertEqual(len(items), len(self.SONGS))
        for item, song_id in zip(items, self.SONGS):
            self.assertEqual(item['id'], song_id)



