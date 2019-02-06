import os
import sys
import unittest
import json
import time

from ..dao.db import main_test
from ..dao.library import Song
from ..dao.storage import StorageNotFoundException
from ..app import TestApp

from io import BytesIO
from .transcode_service import ImageScale


class AudioServiceTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = TestApp(cls.__name__)

        cls.audio_service = cls.app.audio_service
        cls.filesys_service = cls.app.filesys_service
        cls.fs = cls.app.filesys_service.fs
        cls.USERNAME = "admin"
        cls.USER = cls.audio_service.userDao.findUserByEmail(cls.USERNAME)
        cls.db = cls.app.db

    @classmethod
    def tearDownClass(cls):
        cls.app.tearDown()

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_001a_set_audio_path(self):
        """
        a test showing that audio path can be set for a song
        that exists, if the file already exists in the file system table
        """
        song = {
            'artist': 'artist',
            'album': 'album',
            'title': 'title',
        }

        song_id = self.audio_service.createSong(self.USER, song)

        fs_name = "mem"
        rel_path = "sample/audio/file1"

        self.filesys_service.saveFile(self.USER,
            fs_name, rel_path, BytesIO(b"hello world"))

        # there should not yet be a file path
        song = self.audio_service.findSongById(self.USER, song_id)
        self.assertFalse(song['file_path'])

        self.audio_service.setSongFilePath(
            self.USER, song_id, fs_name, rel_path)

        song = self.audio_service.findSongById(self.USER, song_id)

        # the file path is randomly assigned
        # but should exist and be set
        self.assertTrue(song['file_path'].startswith('mem://'))

    def test_001b_set_audio_path_noent(self):
        """
        similar to the first test, but write the file
        directly to the file system, without creating a database entry
        the process should create a file entry automatically
        """
        song = {
            'artist': 'artist',
            'album': 'album',
            'title': 'title',
        }

        song_id = self.audio_service.createSong(self.USER, song)

        fs_name = "mem"
        rel_path = "sample/audio/file2"

        with self.fs.open("mem://test/%s" % rel_path, "wb") as wf:
            wf.write(b"hello world")

        # there should not yet be a file path
        song = self.audio_service.findSongById(self.USER, song_id)
        self.assertFalse(song['file_path'])

        self.audio_service.setSongFilePath(
            self.USER, song_id, fs_name, rel_path)

        song = self.audio_service.findSongById(self.USER, song_id)

        # the file path is randomly assigned
        # but should exist and be set
        self.assertTrue(song['file_path'].startswith('mem://'))

    def test_001b_set_audio_path_dne(self):
        song = {
            'artist': 'artist',
            'album': 'album',
            'title': 'title',
        }

        song_id = self.audio_service.createSong(self.USER, song)

        fs_name = "mem"
        rel_path = "sample/audio/file3"

        with self.assertRaises(FileNotFoundError):
            self.audio_service.setSongFilePath(
                self.USER, song_id, fs_name, rel_path)

    def test_001a_set_art_path(self):
        """
        a test showing that audio path can be set for a song
        that exists, if the file already exists in the file system table
        """
        song = {
            'artist': 'artist',
            'album': 'album',
            'title': 'title',
        }

        song_id = self.audio_service.createSong(self.USER, song)

        fs_name = "mem"
        rel_path = "sample/art/file1"

        self.filesys_service.saveFile(self.USER,
            fs_name, rel_path, BytesIO(b"hello world"))

        # there should not yet be a file path
        song = self.audio_service.findSongById(self.USER, song_id)
        self.assertFalse(song['art_path'])

        self.audio_service.setSongAlbumArtPath(
            self.USER, song_id, fs_name, rel_path)

        song = self.audio_service.findSongById(self.USER, song_id)

        # the file path is randomly assigned
        # but should exist and be set
        self.assertTrue(song['art_path'].startswith('mem://'))

    def test_001b_set_art_path_noent(self):
        """
        similar to the first test, but write the file
        directly to the file system, without creating a database entry
        the process should create a file entry automatically
        """
        song = {
            'artist': 'artist',
            'album': 'album',
            'title': 'title',
        }

        song_id = self.audio_service.createSong(self.USER, song)

        fs_name = "mem"
        rel_path = "sample/art/file2"

        with self.fs.open("mem://test/%s" % rel_path, "wb") as wf:
            wf.write(b"hello world")

        # there should not yet be a file path
        song = self.audio_service.findSongById(self.USER, song_id)
        self.assertFalse(song['art_path'])

        self.audio_service.setSongAlbumArtPath(
            self.USER, song_id, fs_name, rel_path)

        song = self.audio_service.findSongById(self.USER, song_id)

        # the file path is randomly assigned
        # but should exist and be set
        print(song)
        self.assertTrue(song['art_path'].startswith('mem://'))

    def test_001b_set_art_path_dne(self):
        song = {
            'artist': 'artist',
            'album': 'album',
            'title': 'title',
        }

        song_id = self.audio_service.createSong(self.USER, song)

        fs_name = "mem"
        rel_path = "sample/art/file3"

        with self.assertRaises(FileNotFoundError):
            self.audio_service.setSongAlbumArtPath(
                self.USER, song_id, fs_name, rel_path)

if __name__ == '__main__':
    main_test(sys.argv, globals())

