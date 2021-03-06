import os, sys
import unittest
import json

from ...app import TestApp
from .context import YueAppState

class ContextTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        cls.app = TestApp(cls.__name__)
        cls.storageDao = cls.app.filesys_service.storageDao
        cls.userDao = cls.app.filesys_service.userDao
        cls.app.create_test_songs()
        cls.USERNAME = "admin"
        cls.USER = cls.userDao.findUserByEmail(cls.USERNAME)

    @classmethod
    def tearDownClass(cls):
        cls.app.tearDown()

    def setUp(self):

        self.ctxt = YueAppState(
            self.app.user_service,
            self.app.audio_service,
            self.app.filesys_service
        )

        self.ctxt.authenticate("admin", "admin")

        self.ctxt.note_filesystem = 'mem'

    def tearDown(self):
        pass

    def test_000_notes(self):

        content1 = 'abc\n123\n'
        self.ctxt.setNoteContent("test.txt", content1)

        content2 = self.ctxt.getNoteContent("test.txt")

        self.assertEqual(content1, content2)

def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ContextTestCase)
    unittest.TextTestRunner().run(suite)

if __name__ == '__main__':
    main()
