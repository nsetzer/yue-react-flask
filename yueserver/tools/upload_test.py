import os
import sys
import logging
import posixpath
import unittest

from base64 import b64encode

from ..dao.db import main_test
from ..dao.filesys.filesys import FileSystem, MemoryFileSystemImpl

from ..app import TestApp
from ..framework.client import FlaskAppClient
from ..framework.application import AppTestClientWrapper

from ..dao.filesys.crypt import HEADER_SIZE

from .upload import do_upload, JsonUploader, S3Upload
from ..dao.transcode import FFmpeg, find_ffmpeg

def Song(ref, static_path, local_path):
    song = {
        "ref_id": ref,
        "static_path": static_path,
        "file_path": local_path,
        "art_path": "/mnt/music/artist/album/folder.jpg",
        "artist": "artist",
        "album": "album",
        "title": "title",
        "equalizer": 0,
    }
    return song

class UploadIntegrationTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """
        """

        cls.app = TestApp(cls.__name__)
        cls.db = cls.app.db

        cls.libraryDao = cls.app.audio_service.libraryDao
        cls.storageDao = cls.app.filesys_service.storageDao
        cls.userDao = cls.app.filesys_service.userDao

        cls.fs = cls.app.filesys_service.fs

        # a test_client is a client which supports http methods
        # e.g. .get, .post, etc
        cls.token = 'Basic ' + b64encode(b"admin:admin").decode("utf-8")
        cls.test_client = cls.app.test_client(cls.token)
        # a client supports application methods
        # e.g. .files_upload
        cls.client = FlaskAppClient(cls.test_client,
            cls.app._registered_endpoints)

        cls.binpath = find_ffmpeg()

    def test_upload(self):

        songs = [Song(i, "a/b/t/%d" % i, "test/r160.mp3") for i in range(3)]
        root = 'mem'
        do_upload(self.client, songs, root,
            nparallel=1,
            ffmpeg_path=self.binpath)

        # the files that actually exist
        memstore = self.fs._mem()
        print()

        # the files in the database
        statement = self.db.tables.FileSystemStorageTable.select()
        rows = self.db.session.execute(statement).fetchall()
        dbpaths = [row.storage_path for row in rows]

        # the songs that exist
        statement = self.db.tables.SongDataTable.select()
        rows = self.db.session.execute(statement).fetchall()

        for row in rows:
            self.assertTrue(row.file_path in memstore)
            self.assertTrue(row.file_path in dbpaths)
if __name__ == '__main__':
    main_test(sys.argv, globals())
