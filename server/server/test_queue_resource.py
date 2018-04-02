import os
import unittest
import json
import time

from .app import TestApp

class QueueResourceTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        cls.app = TestApp(cls.__name__);

        cls.app.add_resource(cls.app.resource_queue)

        cls.app.create_test_songs()

    @classmethod
    def tearDownClass(cls):
        cls.app.tearDown()

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_001_queue_populate(self):

        username = "user000"
        with self.app.login(username, username) as app:
            data = app.get_json('/api/queue/populate')

            # TODO: something...
def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(QueueResourceTestCase)
    unittest.TextTestRunner().run(suite)

if __name__ == '__main__':
    main()
