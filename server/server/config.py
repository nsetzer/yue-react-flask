
import os, sys

import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

import logging

def _bytes(value):
    """
    convert a string or integer into a number of bytes
        int(4096) -> 4096
        "4096"    -> 4096
        "4k"      -> 4096
    """
    m = 1
    if isinstance(value, str):
        value = value.lower()
        # value could end with 'B', 'K', 'KB', etc
        if value.endswith("b"):
            value = value[:-1]

        if value.endswith("k"):
            value = value[:-1]
            m = 1024
        elif value.endswith("m"):
            value = value[:-1]
            m = 1024 * 1024
        elif value.endswith("g"):
            value = value[:-1]
            m = 1024 * 1024 * 1024
    return int(value) * m

def _level(value):
    value = value.lower()
    if value == "debug":
        return logging.DEBUG
    elif value == "warning":
        return logging.WARNING
    elif value == "info":
        return logging.INFO
    elif value == "critical":
        return logging.CRITICAL
    elif value == "trace":
        return logging.DEBUG - 1
    return logging.ERROR


class Config(object):
    """base class for application configurations"""

    _instance = None

    def __init__(self):

        self.build_dir = os.path.join(os.getcwd(), "build")
        self.static_dir = os.path.join(os.getcwd(), "build", "static")

    @staticmethod
    def init(yaml_cfg):
        with open(yaml_cfg, "r") as rf:
            data = yaml.load(rf, Loader=Loader)
            return Config.init_config(data)

    @staticmethod
    def init_config(data):

        cfg = Config()

        # TODO implement true sub classes
        cfg.host = data['server']['host']
        cfg.port = data['server']['port']
        cfg.domain = data['server']['env']
        cfg.secret_key = data['server']['secret_key']

        cfg.ssl = lambda: None
        cfg.ssl.private_key = data['server']['ssl']['private_key']
        cfg.ssl.certificate = data['server']['ssl']['certificate']

        cfg.cors = lambda: None
        cfg.cors.origins = data['server']['cors']['origins']

        cfg.logging = lambda: None
        cfg.logging.directory = data['server']['logging']['directory']
        cfg.logging.filename = data['server']['logging']['filename']
        cfg.logging.max_size = _bytes(data['server']['logging']['max_size'])
        cfg.logging.num_backups = int(data['server']['logging']['num_backups'])
        cfg.logging.level = _level(data['server']['logging']['level'])

        cfg.database = lambda: None
        cfg.database.kind = data['server']['database']['kind']
        if cfg.database.kind == "sqlite":
            path = data['server']['database']['path']
            path = os.path.abspath(path)
            cfg.database.url = "sqlite:///" + path
        else:
            raise Exception(cfg.database.kind + " unsupported")

        cfg.filesystem = lambda: None
        cfg.filesystem.media_root = data['server']['filesystem']['media_root']

        cfg.transcode = lambda: None
        cfg.transcode.audio = lambda: None
        cfg.transcode.audio.bin_path = data['server']['transcode']['audio']['bin_path']
        cfg.transcode.audio.tmp_path = data['server']['transcode']['audio']['tmp_path']

        Config._instance = cfg
        return cfg

    @staticmethod
    def default():

        cfg = Config()

        # TODO implement true sub classes
        cfg.host = "localhost"
        cfg.port = 4200
        cfg.domain = "test"
        cfg.secret_key = "secret"

        cfg.ssl = lambda: None
        cfg.ssl.private_key = None
        cfg.ssl.certificate = None

        cfg.cors = lambda: None
        cfg.cors.origins = ""

        cfg.logging = lambda: None
        cfg.logging.directory = "./log"
        cfg.logging.filename = "server.log"
        cfg.logging.max_size = 2*1024*1024
        cfg.logging.num_backups = 1
        cfg.logging.level = logging.ERROR

        cfg.database = lambda: None
        cfg.database.kind = "sqlite"
        cfg.database.url = None

        cfg.filesystem = lambda: None
        cfg.filesystem.media_root = "./tmp"

        cfg.transcode = lambda: None
        cfg.transcode.audio = lambda: None
        cfg.transcode.audio.bin_path = ""
        cfg.transcode.audio.tmp_path = "./tmp"

        return cfg

    @staticmethod
    def instance():
        return Config._instance

    def setenv_default(self, env, default):
        if env in os.environ:
            self.__dict__[env] = os.environ[env]
        else:
            self.__dict__[env] = default

class EnvironmentConfig(Config):
    """
    A configuration option which takes values from the current environment
    """

    def __init__(self):
        super(EnvironmentConfig, self).__init__()

        # self.setenv_default("DEFAULT_ROLE", "user")
        # self.setenv_default("DEFAULT_DOMAIN", "test")

        self.setenv_default("ENV", "production")
        # self.setenv_default("DEBUG", "False")
        # self.DEBUG = (self.DEBUG.lower() == "true") or \
        #    (self.ENV == "development")

        # self.setenv_default("PORT",4200)
        self.setenv_default("SECRET_KEY", "SECRET")
        self.setenv_default("DATABASE_URL",
            "sqlite:///" + os.path.join(os.getcwd(), "app.db"))







