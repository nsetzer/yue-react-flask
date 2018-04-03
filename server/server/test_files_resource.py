import os
import unittest
import json
import time

from .app import TestApp

class FilesResourceTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        cls.app = TestApp(cls.__name__);

    @classmethod
    def tearDownClass(cls):
        cls.app.tearDown()

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_get_domains(self):

        username = "admin"
        with self.app.login(username, username) as app:
            data = app.get_json('/api/fs/roots')
            self.assertTrue("default" in data, data)

def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(FilesResourceTestCase)
    unittest.TextTestRunner().run(suite)

if __name__ == '__main__':
    main()
