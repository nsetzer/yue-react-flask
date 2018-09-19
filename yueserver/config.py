
"""
The Application Configuration used in Yue Server
"""
import os, sys

from .framework.config import BaseConfig, ApplicationBaseConfig

class DatabaseConfig(BaseConfig):
    """
    Database connection string information.

    the 'kind' is required to determine how to connect to SQLite or PostgreSQL
    the 'url' is a sqlalchemy url for connecting to the database and is
    generated based off of the values given in the configuration

    """
    def __init__(self, base):

        self.kind = self.get_key(base, 'database', 'kind', required=True)
        if self.kind == "sqlite":
            path = self.get_key(base, 'database', 'path', default=":memory:")
            if path == ":memory:":
                self.url = "sqlite://"
            else:
                path = os.path.abspath(path)
                self.url = "sqlite:///" + path
            self.dbhost = path
        elif self.kind == "postgresql":
            self.dbhost = self.get_key(base, 'database', 'hostname', required=True)
            self.dbuser = self.get_key(base, 'database', 'username', required=True)
            # TODO: password should come from an environment variable
            #      or configured in the environment by default
            self.dbpass = self.get_key(base, 'database', 'password', required=True)
            self.dbname = self.get_key(base, 'database', 'database', required=True)
            self.url = "postgresql://%s:%s@%s/%s" % (self.dbuser, self.dbpass,
                self.dbhost, self.dbname)
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

class AwsConfig(BaseConfig):
    """
    Amazon Web Services Credentials

    used for s3 bucket access
    """
    def __init__(self, base):

        creds = self.get_key(base, 'aws', 'creds', default={})

        self.endpoint = self.get_key(creds, 'endpoint', default=None)
        self.access_key = self.get_key(creds, 'access_key', default=None)
        self.secret_key = self.get_key(creds, 'secret_key', default=None)
        self.region = self.get_key(creds, 'region', default=None)

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
        self.aws = AwsConfig(base)

    @staticmethod
    def null():
        return Config({'server': {'secret_key': '', 'database': {'kind': 'sqlite'}}})

