import os, sys
import unittest
import json
import time

from ..app import TestApp
from .util import uuid_validator
from ..dao.library import Song
from ..dao.util import CaptureOutput

from io import BytesIO
import gzip
import datetime

class LibraryResourceTestCase(unittest.TestCase):

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
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_000a_search_null(self):
        """ show that a null search returns all songs
        """
        username = "user000"
        with self.app.login(username, username) as app:
            data = app.get_json('/api/library')
            self.assertEqual(len(self.app.SONGS), len(data))

    def test_000b_search_null_compressed(self):
        """ show that search results can be compressed
        """
        username = "user000"
        with self.app.login(username, username) as app:
            # for demonstration purposes, show how to formulate a request
            result = app.get('/api/library',
                             headers={"Accept-Encoding": "gzip"},
                             content_type="application/json")
            self.assertEqual(result.status_code, 200, result)
            json_data = gzip.decompress(result.data)
            data = json.loads(json_data.decode("utf-8"))['result']
            self.assertEqual(len(self.app.SONGS), len(data))

            # demonstrate a cleaner api for compressed requests
            data = app.get_json('/api/library', compressed=True)
            self.assertEqual(len(self.app.SONGS), len(data))

    def test_000c_search_invalid_page(self):
        # show that the validators work as intended.
        # the minimum page value is 0, any integer lower than that
        # should return an error, instead of defaulting to 0
        username = "user000"
        with self.app.login(username, username) as app:
            qs = {"page": 0, }
            result = app.get("/api/library", query_string=qs)
            self.assertEqual(result.status_code, 200, result)

            qs = {"page": -1, }
            result = app.get("/api/library", query_string=qs)
            self.assertEqual(result.status_code, 400, result)

    def test_001_history(self):
        """ show that history records can be imported for a song.
        """
        dt_now = datetime.datetime.now()
        dt_start = dt_now - datetime.timedelta(seconds=60)
        dt_end = dt_now + datetime.timedelta(seconds=60)
        epoch_time = int(dt_now.timestamp()) - 30

        iso_start = dt_start.isoformat()
        iso_end = dt_end.isoformat()

        username = "user000"
        song_id = self.app.SONGIDS[0]
        with self.app.login(username, username) as app:
            data = [
                {"timestamp": epoch_time, "song_id": song_id},
            ]

            # attempt to insert a single record
            result = app.post_json("/api/library/history", data)
            self.assertEqual(result.status_code, 200, result)
            body = json.loads(result.data.decode("utf-8"))

            self.assertTrue("result" in body)
            self.assertTrue("records" in body)
            # verify history records have been imported
            self.assertEqual(len(data), body['result'])
            # verify that the server received all records that were sent
            self.assertEqual(len(data), body['records'])

            # -----------------------------------------------------------------
            # attempt to insert the same data
            result = app.post_json("/api/library/history", data)
            self.assertEqual(result.status_code, 200, result)
            body = json.loads(result.data.decode("utf-8"))

            self.assertTrue("result" in body)
            self.assertTrue("records" in body)
            # no history records should have been imported
            self.assertEqual(0, body['result'], body)
            # verify that the server received all records that were sent
            self.assertEqual(len(data), body['records'])

            # -----------------------------------------------------------------
            # get the record that was sent to the server
            qs = {"start": iso_start, "end": iso_end}
            body = app.get_json("/api/library/history", query_string=qs)
            self.assertEqual(body[0]['song_id'], data[0]['song_id'])
            self.assertEqual(body[0]['timestamp'], data[0]['timestamp'])

    def test_001a_history_null(self):
        username = "user000"
        song_id = self.app.SONGIDS[0]
        with self.app.login(username, username) as app:
            data = []

            # attempt to insert zero records
            result = app.post_json("/api/library/history", data)
            self.assertEqual(result.status_code, 400, result)

    def test_001b_history_get_no_start(self):

        username = "user000"
        song_id = self.app.SONGIDS[0]
        with CaptureOutput():
            with self.app.login(username, username) as app:

                qs = {"end": 0}
                result = app.get("/api/library/history", query_string=qs)
                self.assertEqual(result.status_code, 400, result)

    def test_001c_history_get_no_end(self):

        username = "user000"
        song_id = self.app.SONGIDS[0]
        with CaptureOutput():
            with self.app.login(username, username) as app:

                qs = {"start": 0}
                result = app.get("/api/library/history", query_string=qs)
                self.assertEqual(result.status_code, 400, result)

    def test_002a_update_song(self):

        # TODO: this test currently updates the file path
        # in the future this should be disallowed, in favor of the
        # setSongFilePath api.

        song = {
            Song.artist: "update002a",
            Song.album: "update002a",
            Song.title: "update002a",

        }

        song_id = self.app.audio_service.createSong(self.app.USER, song)

        song_update = {
            Song.artist: "update002a",
            Song.id: song_id,
            Song.path: "test/r160.mp3"
        }

        username = "admin"
        with self.app.login(username, username) as app:
            result = app.put_json('/api/library', [song_update])
            self.assertEqual(result.status_code, 200, result)
            body = json.loads(result.data.decode("utf-8"))

            try:
                uuid_validator(body['result'])
            except Exception:
                self.fail("returned invalid uuid")

    def test_002b_update_song_dne(self):
        # TODO: unclear if this should be a 500 or 400 error

        song_update = {
            Song.artist: "update001",
            Song.id: "dne"
        }

        username = "admin"

        with CaptureOutput():
            with self.app.login(username, username) as app:
                result = app.put_json('/api/library', [song_update])
                self.assertEqual(result.status_code, 400, result)

    def test_002c_update_song_path(self):
        """ test that the file path can be updated.

        the file system service and audio service are used in conjunction
        to update the path for a given song id. the services validate that
        the file must exist.
        """

        # first create a new song for this test
        song1 = {
            Song.artist: "update002c",
            Song.album: "update002c",
            Song.title: "update002c",

        }

        song_id = self.app.audio_service.createSong(self.app.USER, song1)

        info = {
            "root": "default",
            "path": "test/r160.mp3",
        }

        # first add the song to the file system database
        path1 = "test/r160.mp3"
        file_path1 = "/%s" % path1
        storage_path1 = os.path.join(os.getcwd(), path1)
        self.storageDao.insert(self.USER['id'],
            file_path1, storage_path1, 0, 0)

        username = "admin"
        with self.app.login(username, username) as app:
            url = '/api/library/%s/audio' % song_id
            result = app.post_json(url, info)
            self.assertEqual(result.status_code, 200, result)

        song2 = self.app.audio_service.findSongById(self.app.USER, song_id)

        self.assertTrue(os.path.exists(song2[Song.path]))
        self.assertTrue(os.path.samefile("./test/r160.mp3", song2[Song.path]))

    def test_002d_update_song_path_error(self):
        """ test set audio path can fail

        missing parameters should cause the request to fail
        """
        song_id = self.app.SONGIDS[0]
        url = '/api/library/%s/audio' % song_id

        username = "admin"
        with self.app.login(username, username) as app:

            # no path given
            info = {
                "root": "default",
            }
            result = app.post_json(url, info)
            self.assertEqual(result.status_code, 400, result)

            # no root given
            info = {
                "path": "test/r160.mp3",
            }
            result = app.post_json(url, info)
            self.assertEqual(result.status_code, 400, result)

    def test_002e_update_song_path_dne(self):
        """ test set audio path can fail

        it should fail when the file does not exist
        """
        song_id = self.app.SONGIDS[0]
        url = '/api/library/%s/audio' % song_id

        username = "admin"
        with CaptureOutput():
            with self.app.login(username, username) as app:

                # no path given
                info = {
                    "root": "default",
                    "path": "++dne++",
                }
                result = app.post_json(url, info)
                self.assertEqual(result.status_code, 404, result.text)

    def test_002f_update_song_art_path(self):
        """ test that the file art path can be updated.

        the file system service and audio service are used in conjunction
        to update the path for a given song id. the services validate that
        the file must exist.
        """

        # first create a new song for this test
        song1 = {
            Song.artist: "update002f",
            Song.album: "update002f",
            Song.title: "update002f",

        }

        song_id = self.app.audio_service.createSong(self.app.USER, song1)

        info = {
            "root": "default",
            "path": "test/blank.png",
        }

        # first add the art to the file system database
        path1 = "test/blank.png"
        file_path1 = "/%s" % path1
        storage_path1 = os.path.join(os.getcwd(), path1)
        self.storageDao.insert(self.USER['id'],
            file_path1, storage_path1, 0, 0)

        username = "admin"
        with self.app.login(username, username) as app:
            url = '/api/library/%s/art' % song_id
            result = app.post_json(url, info)
            self.assertEqual(result.status_code, 200, result)

        song2 = self.app.audio_service.findSongById(self.app.USER, song_id)

        self.assertTrue(os.path.exists(song2[Song.art_path]))
        self.assertTrue(os.path.samefile("./test/blank.png",
            song2[Song.art_path]))

        username = "admin"
        with self.app.login(username, username) as app:
            url = '/api/library/%s/art' % song_id
            qs = {"scale": "small", }
            result = app.get(url, query_string=qs)
            self.assertEqual(result.status_code, 200, result)
            # it should always return a png
            # trust that the size is correct
            self.assertEqual(result.data[:4], b"\x89PNG")

    def test_003a_create_song(self):

        song = {
            Song.artist: "create000",
            Song.album: "create000",
            Song.title: "create000",
            Song.path: "test/r160.mp3",
        }

        username = "admin"
        with self.app.login(username, username) as app:
            result = app.post_json('/api/library', song)
            self.assertEqual(result.status_code, 201, result)
            body = json.loads(result.data.decode("utf-8"))

            try:
                uuid_validator(body['result'])
            except Exception:
                self.fail("returned invalid uuid")

    def test_003b_create_song_error(self):

        song = {
            Song.artist: "create000",
            Song.album: "create000",
        }

        username = "admin"
        with CaptureOutput():
            with self.app.login(username, username) as app:
                result = app.post_json('/api/library', song)
                self.assertEqual(result.status_code, 400, result)

def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(LibraryResourceTestCase)
    unittest.TextTestRunner().run(suite)

if __name__ == '__main__':
    main()
