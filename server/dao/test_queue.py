import os
import unittest
import tempfile
import json

from ..util import TestCase

from .queue import SongQueueDao

from ..app import app, db, dbtables

class SongQueueTestCase(TestCase):

    def setUp(self):
        super().setUp()

        self.queue = SongQueueDao(db, dbtables)

    def tearDown(self):
        pass

    def test_queue_head(self):

        user_id = self.USER['id']
        domain_id = self.USER['domain_id']

        self.queue.set(user_id, domain_id, self.SONGS)

        item = self.queue.head(user_id, domain_id)
        self.assertEqual(item['id'], self.SONGS[0])

    def test_queue_rest(self):

        user_id = self.USER['id']
        domain_id = self.USER['domain_id']

        self.queue.set(user_id, domain_id, self.SONGS)

        items = self.queue.rest(user_id, domain_id)
        self.assertIsNotNone(items)
        self.assertEqual(len(items), len(self.SONGS) - 1)
        for item, song_id in zip(items, self.SONGS[1:]):
            self.assertEqual(item['id'], song_id)

    def test_queue_get(self):

        user_id = self.USER['id']
        domain_id = self.USER['domain_id']

        self.queue.set(user_id, domain_id, self.SONGS)

        items = self.queue.get(user_id, domain_id)
        self.assertIsNotNone(items)
        self.assertEqual(len(items), len(self.SONGS))
        for item, song_id in zip(items, self.SONGS):
            self.assertEqual(item['id'], song_id)



