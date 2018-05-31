
import os
import sys

if (sys.version_info[0] == 2):
    raise RuntimeError("python2 not supported")

import logging
from logging.handlers import RotatingFileHandler

from .framework.application import FlaskApp
from .framework.web_resource import WebResource, get
from .framework.clientgen import generate_client as generate_client_impl

from .config import Config

from flask import jsonify, render_template

from .service.audio_service import AudioService
from .service.transcode_service import TranscodeService
from .service.user_service import UserService
from .service.filesys_service import FileSysService
from .dao.library import Song

from .resource.app_resource import AppResource
from .resource.user_resource import UserResource
from .resource.library_resource import LibraryResource
from .resource.queue_resource import QueueResource
from .resource.files_resource import FilesResource

from .dao.db import db_connect, db_init_main

import ssl
import argparse
import codecs

class YueApp(FlaskApp):
    """docstring for YueApp"""
    def __init__(self, config):
        super(YueApp, self).__init__(config)

        self.db = db_connect(self.config.database.url)

        self.user_service = UserService(config, self.db, self.db.tables)
        self.audio_service = AudioService(config, self.db, self.db.tables)
        self.transcode_service = TranscodeService(config, self.db, self.db.tables)
        self.filesys_service = FileSysService(config, self.db, self.db.tables)

        self.add_resource(AppResource(self.config))
        self.add_resource(UserResource(self.user_service))
        self.add_resource(LibraryResource(self.user_service,
                                          self.audio_service,
                                          self.transcode_service,
                                          self.filesys_service))
        self.add_resource(QueueResource(self.user_service,
                                        self.audio_service))
        self.add_resource(FilesResource(self.user_service, self.filesys_service))

class TestApp(YueApp):
    """docstring for TestApp"""
    def __init__(self, test_name=""):
        config = self._init_config(test_name)
        super(TestApp, self).__init__(config)

        db_init_main(self.db, self.db.tables, self.env_cfg)

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
                'cors': {'origin': '*'},
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
                'filesystem': {'media_root': os.getcwd()},
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
                # the test user has the minimum set of features to
                # be able to listen to music and manage their profile
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

        config = Config(self.app_cfg)
        config.database.url = None

        return config

    def login(self, username, password):
        token = self.user_service.loginUser(username, password)
        return self.test_client(token)

    def create_test_songs(self):
        self.SONGS = []
        self.SONGIDS = []
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
                    self.SONGIDS.append(song_id)

    def tearDown(self):
        # nothing to do
        pass

def connect(host, username, password):
    app = YueApp(Config.null())
    return app.client(host, username, password)

def generate_client(app, name="client", outdir="."):

    header = "# This file was auto generated. do not modify\n"
    client_dir = os.path.join(outdir, name)

    generate_client_impl(app, name, outdir)

    py_client_impl = os.path.join(client_dir, "sync.py")
    with open(py_client_impl, "w") as wf:
        wf.write(header)
        with open("server/tools/sync.py", "r") as rf:
            for line in rf:
                if 'import connect' in line:
                    wf.write("from .connect import connect\n")
                else:
                    wf.write(line)

def parseArgs(argv, default_profile=None):

    #encoding = "cp850"
    #if sys.stdout.encoding != encoding:
    #  sys.stdout = codecs.getwriter(encoding)(sys.stdout.buffer, 'strict')
    #if sys.stderr.encoding != encoding:
    #  sys.stderr = codecs.getwriter(encoding)(sys.stderr.buffer, 'strict')


    if default_profile is None:
        default_profile = "windev" if sys.platform == "win32" else "development"

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--config_dir', dest='config', default="./config",
                        help='enable verbose logging')
    parser.add_argument('-p', '--profile', dest='profile',
                        default=default_profile,
                        help='default profile to use (%s)' % default_profile)

    args = parser.parse_args(argv[1:])

    return args

def getApp(config_dir, profile):

    app_cfg_path = os.path.join(config_dir, profile, "application.yml")
    cfg = Config(app_cfg_path)

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

    app = YueApp(cfg)

    return app

def main():

    args = parseArgs(sys.argv)

    app = getApp(args.config, args.profile)

    app.run()

if __name__ == '__main__':
    main()