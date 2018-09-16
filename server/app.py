
## @mainpage
#
# @par Yue Server
#
# A Web application for streaming music

## @page stack Application Stack
#
# @par Flask Application
#
#  A collection of resources, the configuration
#  database and web resources that make up a web app.
#
# @par Web Resource Layer
#
# Declarative definitions for REST Endpoints in the application.
# Each resource declares the mapping of a url path and HTTP verb to one or
# more functions in the service layer.
#
# @par Service Layer
#
# Services build the business logic by building on top of database.
#
# @par Dao Layer
#
# Data access objects for interacting with the database or filesystem
# This is made up of a database library, and an abstract file system.
#
# The db library  provides access to a sqlite or postgres database
#
# The file system library provides access to either local storage,
#  s3 or an in-memory (for testing) file system
#
# @par Database
#
# A database client to SQLite or PostgreSQL.

## @package server.app
#
#  The Application Backend
#
#

import os
import sys

if (sys.version_info[0] == 2):
    raise RuntimeError("python2 not supported")

import ssl
import argparse
import codecs

import logging
from logging.handlers import RotatingFileHandler

from flask import jsonify, render_template

from .config import Config

from .dao.library import Song
from .dao.transcode import find_ffmpeg
from .dao.db import db_connect, db_init_main

from .framework.application import FlaskApp
from .framework.web_resource import WebResource, get
from .framework.clientgen import generate_client as generate_client_impl

from .service.audio_service import AudioService
from .service.transcode_service import TranscodeService
from .service.user_service import UserService
from .service.filesys_service import FileSysService

from .resource.app_resource import AppResource
from .resource.user_resource import UserResource
from .resource.library_resource import LibraryResource
from .resource.queue_resource import QueueResource
from .resource.files_resource import FilesResource

class YueApp(FlaskApp):
    """docstring for YueApp"""
    def __init__(self, config):
        super(YueApp, self).__init__(config)

        logging.warning("db_connect: %s" % self.config.database.dbhost)
        self.db = db_connect(self.config.database.url)

        # check that the database is configured.
        # the number of tables may not match if there are additional
        # test tables, but in general should be the same
        nbTablesExpected = len(self.db.metadata.tables.keys())
        nbTablesActual = len(self.db.engine.table_names())
        if nbTablesExpected != nbTablesActual:
            logging.warning("database contains %d tables. expected %d." % (
                nbTablesActual, nbTablesExpected))

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
    """An app with helper functions for testing"""
    def __init__(self, test_name=""):
        config = self._init_config(test_name)
        super(TestApp, self).__init__(config)

        db_init_main(self.db, self.db.tables, self.env_cfg)

        self.TEST_DOMAIN = "test"
        self.TEST_ROLE = "test"

        self.USER = self.user_service.getUserByPassword("user000", "user000")

    def _init_config(self, test_name):

        ffmpeg_path = find_ffmpeg()

        if ffmpeg_path is None:
            raise Exception("FFmpeg not found")

        tmp_path = os.path.join(os.getcwd(), "test")
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
                'filesystem': {
                    'media_root': os.getcwd(),
                    'other': {
                        "mem": "mem://test",
                    },
                },
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
            'features': ["user_read",
                         "user_write",
                         "user_create",
                         "user_power",
                         "library_read",
                         "library_write",
                         "library_read_song",
                         "library_write_song",
                         "filesystem_read",
                         "filesystem_write",
                         "filesystem_delete"],
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
        """ return a test client which sends credentials with every request
        """
        token = self.user_service.loginUser(username, password)
        return self.test_client(token)

    def create_test_songs(self):
        """ add tests songs to the database
        """
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
    """ return a client which sends credentials with every request"""
    app = YueApp(Config.null())
    return app.client(host, username, password)

def generate_client(app, name="client", outdir="."):
    """generate a client python package

    the generated package will implement a rest client with endpoint
    definitions for the application server

    This wraps the framework implementation of the same function,
    and bundles in a sync tool which utilizes the file api.
    """

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
    """ parse the command line arguments used for launching an app

    builds an arg parser with the common options needed to create an app.
    """

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
    # workers and bind are for gunicorn support
    # todo: the default bind should be none
    # then use the config to set the default bind,
    #parser.add_argument('--bind', type=str, default="0.0.0.0:4200",
    #                    help="bind server to host:port")
    #parser.add_argument('-w', '--workers', type=int,
    #                    default=1,
    #                    help='number of workers')
    #parser.add_argument('appname', default='wsgi:app', nargs='?'
    #    help="the name of the app for running using wsgi (file:varname)")

    args, _ = parser.parse_known_args(argv[1:])


    #app.logger.handlers = gunicorn_logger.handlers
    #app.logger.setLevel(gunicorn_logger.level)


    return args

def getApp(config_dir, profile):
    """ get the application for a specific profile

    Loads the configuration for the specified profile and returns a new
    App instance.

    """

    app_cfg_path = os.path.join(config_dir, profile, "application.yml")
    cfg = Config(app_cfg_path)

    if not os.path.exists(cfg.logging.directory):
        os.makedirs(cfg.logging.directory)

    FORMAT = '%(levelname)-8s: %(asctime)-15s %(message)s'
    logging.basicConfig(format=FORMAT, level=cfg.logging.level)
    log_path = os.path.join(cfg.logging.directory, cfg.logging.filename)
    handler = RotatingFileHandler(log_path,
        maxBytes=cfg.logging.max_size,
        backupCount=cfg.logging.num_backups)
    handler.setLevel(cfg.logging.level)
    logging.getLogger().addHandler(handler)

    logging.info("using config: %s" % app_cfg_path)

    #gunicorn_logger = logging.getLogger('gunicorn.error')
    #print(list(sorted(logging.Logger.manager.loggerDict.keys())))
    #print(gunicorn_logger.level)

    app = YueApp(cfg)

    return app

def main():

    args = parseArgs(sys.argv)

    app = getApp(args.config, args.profile)

    app.run()

if __name__ == '__main__':
    main()