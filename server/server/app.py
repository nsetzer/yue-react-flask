
import os
import sys
import logging
from logging.handlers import RotatingFileHandler

from ..framework.application import FlaskApp
from ..framework.web_resource import WebResource, get

from .config import Config

from flask import jsonify, render_template

from ..service.audio_service import AudioService
from ..service.transcode_service import TranscodeService
from ..service.user_service import UserService
from ..dao.library import Song

from .user_resource import UserResource
from .library_resource import LibraryResource
from .queue_resource import QueueResource
from .files_resource import FilesResource

from ..dao.db import db_connect, db_remove, db_init_main

import ssl

class AppResource(WebResource):
    """docstring for AppResource
    """

    def __init__(self):
        super(AppResource, self).__init__()
        #self.register('/', self.index1, ['GET'])
        #self.register('/<path:path>', self.index2, ['GET'])
        #self.register('/health', self.health, ['GET'])
        #self.register('/.well-known/<path:path>', self.webroot, ['GET'])

    @get("/")
    def index1(self, app):
        return render_template('index.html')

    @get("/<path:path>")
    def index2(self, app, path):
        return render_template('index.html')

    @get("/health")
    def health(self, app):
        return jsonify(result="OK")

    @get("/.well-known/<path:path>")
    def webroot(self, app, path):
        base = os.path.join(os.getcwd(), ".well-known")
        return send_from_directory(base, path)

class YueApp(FlaskApp):
    """docstring for YueApp"""
    def __init__(self, config):
        super(YueApp, self).__init__(config)

        self.db = db_connect(self.config.database.url)

        self.user_service = UserService(config, self.db, self.db.tables)
        self.audio_service = AudioService(config, self.db, self.db.tables)
        self.transcode_service = TranscodeService(config, self.db, self.db.tables)

        self.add_resource(AppResource())
        self.add_resource(UserResource(self.user_service))
        self.add_resource(LibraryResource(self.user_service,
                                          self.audio_service,
                                          self.transcode_service))
        self.add_resource(QueueResource(self.user_service,
                                        self.audio_service))
        self.add_resource(FilesResource(self.user_service))

class TestApp(FlaskApp):
    """docstring for TestApp"""
    def __init__(self, test_name=""):
        config = self._init_config(test_name)
        super(TestApp, self).__init__(config)

        # self.db = db_connect(self.config.database.url)
        self.db = db_connect(None)

        db_init_main(self.db, self.db.tables, self.env_cfg)

        self.audio_service = AudioService(config, self.db, self.db.tables)
        self.transcode_service = TranscodeService(config, self.db, self.db.tables)
        self.user_service = UserService(config, self.db, self.db.tables)

        # create the resources, but let the individual tests decide which
        # resources will be registed.
        self.resource_app = AppResource()
        self.resource_user = UserResource(self.user_service)
        self.resource_library = LibraryResource(self.user_service,
                                                self.audio_service,
                                                self.transcode_service)
        self.resource_queue = QueueResource(self.user_service,
                                              self.audio_service)
        self.resource_files = FilesResource(self.user_service)

        self.TEST_DOMAIN = "test"
        self.TEST_ROLE = "test"

        self.USER = self.user_service.getUserByPassword("user000", "user000")

    def _find_ffmpeg(self):
        ffmpeg_paths = [
            '/bin/ffmpeg',
            '/usr/bin/ffmpeg',
            '/usr/local/bin/ffmpeg',
            'C:\\ffmpeg\\bin\\ffmpeg.exe'
        ]

        for path in ffmpeg_paths:
            if os.path.exists(path):
                return path
        return None

    def _init_config(self, test_name):

        ffmpeg_path = self._find_ffmpeg()

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
                    'path': 'database.test.%s.sqlite' % test_name
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

        self.env_cfg = {
            'features': ["user_read", "user_write",
                         "user_create", "user_power",
                         "library_read", "library_write",
                         "library_read_song", "library_write_song",
                         "filesystem_read","filesystem_write"],
            'domains': ['test'],
            'roles': [
                {'null': { 'features': []}},
                {'test': { 'features': [
                            "user_read",
                            "user_write",
                            "library_read",
                            "library_read_song"]
                         }
                },
                {'admin': { 'features': ['all',]}},
            ],
            'users': [
                {'email': 'null',
                 'password': 'null',
                 'domains': ['test'],
                 'roles': ['null']},
                {'email': 'user000',
                 'password': 'user000',
                 'domains': ['test'],
                 'roles': ['test']},
                {'email': 'admin',
                 'password': 'admin',
                 'domains': ['test'],
                 'roles': ['admin']},
            ]
        }

        self.db_path = self.app_cfg['server']['database']['path']

        db_remove(self.db_path)

        config = Config.init_config(self.app_cfg)

        return config

    def add_all_resources(self):
        self.add_resource(AppResource())
        self.add_resource(UserResource(self.user_service))
        self.add_resource(LibraryResource(self.user_service,
                                          self.audio_service,
                                          self.transcode_service))
        self.add_resource(QueueResource(self.user_service,
                                        self.audio_service))
        self.add_resource(FilesResource(self.user_service))

    def login(self, username, password):
        token = self.user_service.loginUser(username, password)
        return self.test_client(token)

    def create_test_songs(self):
        self.SONGS = []
        for a in range(3):
            for b in range(3):
                for t in range(3):
                    song = {
                        Song.artist: "Artist%03d" % a,
                        Song.album: "Album%03d" % b,
                        Song.title: "Title%03d" % t,
                        Song.ref_id: "id%06d" % (len(self.SONGS)),
                    }
                    song_id = self.audio_service.createSong(self.USER, song)
                    song[Song.id] = song_id
                    self.SONGS.append(song)

    def tearDown(self):
        db_remove(self.db_path)

def main():

    import argparse
    import codecs

    encoding = "cp850"
    if sys.stdout.encoding != encoding:
      sys.stdout = codecs.getwriter(encoding)(sys.stdout.buffer, 'strict')
    if sys.stderr.encoding != encoding:
      sys.stderr = codecs.getwriter(encoding)(sys.stderr.buffer, 'strict')


    default_profile = "windev" if sys.platform == "win32" else "development"
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--config_dir', dest='config', default="./config",
                        help='enable verbose logging')
    parser.add_argument('-p', '--profile', dest='profile',
                        default=default_profile,
                        help='default profile to use')

    args = parser.parse_args()


    app_cfg_path = os.path.join(args.config, args.profile, "application.yml")
    cfg = Config.init("config/windev/application.yml")

    if not os.path.exists(cfg.logging.directory):
        os.makedirs(cfg.logging.directory)

    FORMAT = '%(asctime)-15s %(message)s'
    logging.basicConfig(format=FORMAT, level=cfg.logging.level)
    log_path = os.path.join(cfg.logging.directory, cfg.logging.filename)
    handler = RotatingFileHandler(log_path,
        maxBytes=cfg.logging.max_size,
        backupCount=cfg.logging.num_backups)
    handler.setLevel(cfg.logging.level)
    logging.getLogger().addHandler(handler)

    logging.info("using config: %s" % app_cfg_path)

    context = None
    if os.path.exists(cfg.ssl.private_key) and os.path.exists(cfg.ssl.certificate):
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        context.load_cert_chain(cfg.ssl.certificate, cfg.ssl.private_key)

    # configure logging

    app = YueApp(cfg)

    app.run(context)

if __name__ == '__main__':
    main()