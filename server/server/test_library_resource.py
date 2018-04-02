import os
import unittest
import json
import time

from .app import TestApp

from io import BytesIO
import gzip
import datetime

class LibraryResourceTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        cls.app = TestApp(cls.__name__);

        cls.app.add_resource(cls.app.resource_library)

        cls.app.create_test_songs()

    @classmethod
    def tearDownClass(cls):
        cls.app.tearDown()

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_search_null(self):
        """ show that a user can change their password
        """
        username = "user000"
        with self.app.login(username, username) as app:
            data = app.get_json('/api/library')
            self.assertEqual(len(self.app.SONGS), len(data))

    def test_search_null_compressed(self):
        """ show that a user can change their password
        """
        username = "user000"
        with self.app.login(username, username) as app:
            # for demonstration purposes, show how to formulate a request
            result = app.get('/api/library',
                             headers={"Accept-Encoding": "gzip"},
                             content_type="application/json")
            self.assertEqual(result.status_code, 200, result)
            json_data = gzip.decompress(result.data)
            data = json.loads(json_data)['result']
            self.assertEqual(len(self.app.SONGS), len(data))

            # demonstrate a cleaner api for compressed requests
            data = app.get_json('/api/library', compressed=True)
            self.assertEqual(len(self.app.SONGS), len(data))




def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(LibraryResourceTestCase)
    unittest.TextTestRunner().run(suite)

if __name__ == '__main__':
    main()
