import os
import unittest
import tempfile
import json
import time

from .app import AppResource, YueApp
from ..framework.application import FlaskApp
from ..framework.web_resource import WebResource

from ..service.audio_service import AudioService
from ..service.transcode_service import TranscodeService
from ..service.user_service import UserService

from ..config import Config

from ..cli.config import db_init_main
from ..cli.managedb import db_connect, db_remove

class TestApp(FlaskApp):
    """docstring for TestApp"""
    def __init__(self):

        ffmpeg_paths = [
            '/bin/ffmpeg',
            '/usr/bin/ffmpeg',
            '/usr/local/bin/ffmpeg',
            'C:\\ffmpeg\\bin\\ffmpeg.exe'
        ]

        ffmpeg_path = None;
        for path in ffmpeg_paths:
            if os.path.exists(path):
                ffmpeg_path = path
                break;

        tmp_path = os.path.join(os.getcwd(), "tmp")
        log_path = tmp_path

        self.app_cfg = {
            'server': {
                'host': 'localhost',
                'port': 4200,
                'env': 'production',
                'secret_key': 'secret',
                'cors': {'origins': '*'},
                'database': {
                    'kind': 'sqlite',
                    'path': 'database.test.sqlite'
                },
                'ssl': {'private_key': '', 'certificate': ''},
                'logging': {
                    'directory': log_path,
                    'filename': 'server.log',
                    'max_size': '2MB',
                    'num_backups': 10,
                    'level': 'debug'},
                'filesystem': {'media_root': '/mnt/data'},
                'transcode': {
                    'audio': {
                        'bin_path': ffmpeg_path,
                        'tmp_path': tmp_path,
                    },
                    'image': {}
                }
            }
        }
        print(self.app_cfg)

        self.env_cfg = {
            'features': ['test', ],
            'domains': ['test'],
            'roles': [
                {'test': { 'features': ['all',]}},
            ],
            'users': [
                {'email': 'user000',
                 'password': 'user000',
                 'domains': ['test'],
                 'roles': ['test']},
            ]
        }
        print(self.env_cfg)

        self.db_path = self.app_cfg['server']['database']['path']

        db_remove(self.db_path)

        config = Config.init_config(self.app_cfg)

        super(TestApp, self).__init__(config)

        print("db init")
        db_init_main(self.db, self.db.tables, self.env_cfg)

        self.audio_service = AudioService(self.db, self.db.tables)
        self.transcode_service = TranscodeService(self.db, self.db.tables)
        self.user_service = UserService(self.db, self.db.tables)


        self.resource_app = AppResource()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)


class AppTestCase(unittest.TestCase):

    db_name = "AppTestCase"

    @classmethod
    def setUpClass(cls):

        #cls.USERNAME = "user000"
        #cls.USER = cls.userDao.findUserByEmail(cls.USERNAME)

        #cls.libraryDao = LibraryDao(db, db.tables)
        #cls.songs = []
        #for a in range(3):
        #    for b in range(3):
        #        for t in range(3):
        #            song = {
        #                Song.artist: "Artist%03d" % a,
        #                Song.album: "Album%03d" % b,
        #                Song.title: "Title%03d" % t,
        #                Song.ref_id: "id%06d" % ((a+1)*100 + (b+1)*10 + (t+1)),
        #            }
        #            cls.songs.append(song)

        cls.app = TestApp();

        cls.app.add_resource(cls.app.resource_app)

    @classmethod
    def tearDownClass(cls):
        cls.app.tearDown()

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_health(self):
        with self.app.test_client() as app:
            result = app.get("/health")
            self.assertEqual(result.status_code, 200)

def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AppTestCase)
    unittest.TextTestRunner().run(suite)

if __name__ == '__main__':
    main()
