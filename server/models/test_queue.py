import os
import unittest
import tempfile
import json

from ..util import TestCase

from .song import Song, Library, LibraryException
from .user import User
from .queue import SongQueue

class SongQueueTestCase(TestCase):

    def setUp(self):
        super().setUp()

        username = "user000"
        self.user = User.get_user_with_email(username)
        self.lib = Library(self.user.id, self.user.domain_id)
        self.queue = SongQueue(self.user.id, self.user.domain_id)

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



