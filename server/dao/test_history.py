import os
import unittest
import tempfile
import json
import datetime

from ..util import TestCase

from .history import HistoryDao

from ..app import app, db, dbtables

class SongHistoryTestCase(TestCase):

    def setUp(self):
        super().setUp()

        self.history = HistoryDao(db, dbtables)

    def tearDown(self):
        pass

    def test_queue_head(self):

        user_id = self.USER['id']
        domain_id = self.USER['domain_id']

        for _id in self.SONGS:
            timestamp = int(datetime.datetime.now().timestamp())
            self.history.insert(user_id, _id, timestamp)

        start = (datetime.datetime.now() -
            datetime. timedelta(days=1)).timestamp()

        end = datetime.datetime.now().timestamp() + 1

        records = self.history.retrieve(user_id, start)
        self.assertEqual(len(records), len(self.SONGS))

        records = self.history.retrieve(user_id, start, end)
        self.assertEqual(len(records), len(self.SONGS))
