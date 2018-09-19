import os
import unittest
import tempfile
import json
import datetime

from .util import pathCorrectCase

class UtilTestCase(unittest.TestCase):

    db_name = "SongHistoryTestCase"

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def setUp(self):
        super().setUp()

    def tearDown(self):
        pass

    def test_path(self):

        # most of these tests dont work on windows, because
        # case does not matter in that instance

        path1 = "./TEST/R160.MP3"
        path1o = pathCorrectCase(path1)
        self.assertTrue(os.path.exists(path1o))
        self.assertTrue(os.path.isabs(path1o))

        path1 = "./test/r160.mp3"
        path1o = pathCorrectCase(path1)
        self.assertTrue(os.path.exists(path1o))
        self.assertTrue(os.path.isabs(path1o))

        path2 = "./TEST/D160.mp3"
        with self.assertRaises(Exception):
            pathCorrectCase(path2)

        path1 = "TEST/./R160.mp3"
        path1o = pathCorrectCase(path1)
        self.assertTrue(os.path.exists(path1o))
        self.assertTrue(os.path.isabs(path1o))

        path1 = "TEST/../TEST/R160.mp3"
        path1o = pathCorrectCase(path1)
        self.assertTrue(os.path.exists(path1o))
        self.assertTrue(os.path.isabs(path1o))

        path = pathCorrectCase("~")
        self.assertTrue(os.path.isabs(path))

def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(UtilTestCase)
    unittest.TextTestRunner().run(suite)

if __name__ == '__main__':
    main()
