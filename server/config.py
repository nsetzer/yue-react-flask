
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
    """
    convert a string logging level into a logging enum
    """
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

def _get_key(d, *keys, default=None, required=False):

    try:
        p = d
        for k in keys:
            p = p[k]
        return p
    except:
        if not required:
            return default

    raise KeyError(",".join(keys))

class SSLConfig(object):
    def __init__(self, base):
        self.private_key = _get_key(base, 'ssl', 'private_key', default="")
        self.certificate = _get_key(base, 'ssl', 'certificate', default="")

class CORSConfig(object):
    def __init__(self, base):
        # TODO: revist default values
        self.origin = _get_key(base, 'cors', 'origin',
            default="*")
        self.headers = _get_key(base, 'cors', 'headers',
            default="Origin, X-Requested-With, Content-Type, Accept")
        self.methods = _get_key(base, 'cors', 'methods',
            default="GET, POST, PUT, DELETE, OPTIONS")

class LoggingConfig(object):
    def __init__(self, base):
        self.directory =  _get_key(base, 'logging', 'directory', default="./log")
        self.filename =  _get_key(base, 'logging', 'filename', default="server.log")
        self.max_size = _bytes(_get_key(base, 'logging', 'max_size', default="2048k"))
        self.num_backups = int(_get_key(base, 'logging', 'num_backups', default=10))
        self.level = _level(_get_key(base, 'logging', 'level', default="error"))

class DatabaseConfig(object):
    def __init__(self, base):

        self.kind = _get_key(base, 'database', 'kind', default="sqlite")
        if self.kind == "sqlite":
            path = _get_key(base, 'database', 'path', default=":memory:")
            if path == ":memory:":
                self.url = "sqlite://"
            else:
                path = os.path.abspath(path)
                self.url = "sqlite:///" + path
        else:
            raise Exception(self.kind + " unsupported database type")

class FilesystemConfig(object):
    def __init__(self, base):

        self.media_root = _get_key(base, 'filesystem', 'media_root', default=os.getcwd())

class TranscodeConfig(object):
    def __init__(self, base):
        self.audio = lambda: None
        self.audio.bin_path = _get_key(base, 'transcode', 'audio', 'bin_path', default="")
        self.audio.tmp_path = _get_key(base, 'transcode', 'audio', 'tmp_path', default="./tmp")
        self.image = lambda: None

# todo, break this into an AppConfig and BaseAppConfig
# stash the BaseAppConfig in the framework

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

        base = data['server']

        cfg = Config()

        # TODO implement true sub classes
        cfg.host = _get_key(base, 'host', default="localhost")
        cfg.port = _get_key(base, 'port', default=4200)
        cfg.domain = _get_key(base, 'env', default="production")
        cfg.secret_key = _get_key(base, 'secret_key', required=True)

        cfg.ssl = SSLConfig(base)
        cfg.cors = CORSConfig(base)
        cfg.logging = LoggingConfig(base)
        cfg.database = DatabaseConfig(base)
        cfg.filesystem = FilesystemConfig(base)
        cfg.transcode = TranscodeConfig(base)

        Config._instance = cfg
        return cfg

    @staticmethod
    def null():
        return Config.init_config({'server':{'secret_key':""}})

    @staticmethod
    def instance():
        return Config._instance
