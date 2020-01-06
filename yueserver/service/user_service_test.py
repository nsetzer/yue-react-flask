

import os
import sys
import unittest
import json
import time

from ..dao.db import main_test
from ..dao.library import Song
from ..app import TestApp

class UserServiceTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = TestApp(cls.__name__)

        cls.service = cls.app.user_service

    @classmethod
    def tearDownClass(cls):
        cls.app.tearDown()

    def test_001a_uuid_token(self):

        two_weeks = 2 * 7 * 24 * 60 * 60
        token = self.service.generateUUIDToken(self.app.USER, two_weeks)

        user = self.service.getUserFromUUIDToken(token)

        self.assertEqual(user['id'], self.app.USER['id'])

if __name__ == '__main__':
    main_test(sys.argv, globals())

