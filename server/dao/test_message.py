import os
import unittest
import tempfile
import json

from ..util import TestCase
from ..app import app, db

from .message import Message

class SongQueueTestCase(TestCase):

    def setUp(self):
        super().setUp()

        self.msg = Message(db)

    def tearDown(self):
        pass

    def test_message(self):

        msgs = self.msg.get_all_messages()
        self.assertEqual(len(msgs), 0)

        self.msg.add("abc")

        msgs = self.msg.get_all_messages()
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0][1], "abc")

        self.msg.remove(msgs[0][0])
        msgs = self.msg.get_all_messages()
        self.assertEqual(len(msgs), 0)
