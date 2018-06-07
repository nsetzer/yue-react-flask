
"""
The Application Configuration used in Yue Server
"""
import os, sys

from .framework.config import BaseConfig, ApplicationBaseConfig

class DatabaseConfig(BaseConfig):
    def __init__(self, base):

        self.kind = self.get_key(base, 'database', 'kind', default="sqlite")
        if self.kind == "sqlite":
            path = self.get_key(base, 'database', 'path', default=":memory:")
            if path == ":memory:":
                self.url = "sqlite://"
            else:
                path = os.path.abspath(path)
                self.url = "sqlite:///" + path
        else:
            raise Exception(self.kind + " unsupported database type")

class FilesystemConfig(BaseConfig):
    def __init__(self, base):

        self.media_root = self.get_key(base, 'filesystem', 'media_root', default=os.getcwd())
        self.media_root = os.path.abspath(self.media_root)

        self.other = {}
        other = self.get_key(base, 'filesystem', 'other', default={})
        for k, v in other.items():
            if "://" not in v:
                v = os.path.abspath(v)
            self.other[k] = v

class TranscodeAudioConfig(BaseConfig):
    def __init__(self, base):
        self.bin_path = self.get_key(base, 'bin_path', default="")
        self.tmp_path = self.get_key(base, 'tmp_path', default="./tmp")

class TranscodeConfig(BaseConfig):
    def __init__(self, base):
        self.audio = TranscodeAudioConfig(self.get_key(base,'transcode',"audio"))
        self.image = None

class Config(ApplicationBaseConfig):
    """base class for application configurations"""

    def __init__(self, data):
        super(Config, self).__init__(data)

    def init(self, data):
        super(Config, self).init(data)

        base = self.get_key(data, "server")

        self.database = DatabaseConfig(base)
        self.filesystem = FilesystemConfig(base)
        self.transcode = TranscodeConfig(base)

    @staticmethod
    def null():
        return Config({'server':{'secret_key':""}})

