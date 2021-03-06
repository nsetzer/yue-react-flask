
"""
A YAML config parser
"""
import os, sys

import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

import logging

from .crypto import CipherConfigDecryptor, ParameterStoreConfigDecryptor

def yload(path):

    if not os.path.exists(path):
        return {}

    with open(path, "r") as rf:
        return yaml.load(rf, Loader=Loader)

def ydump(path, obj):
    dir, _ = os.path.split(path)

    if not os.path.exists(dir):
        os.makedirs(dir)

    with open(path, "w") as wf:
        yaml.dump(obj, wf, width=78, indent=4)

class BaseConfig(object):
    def __init__(self):
        super(BaseConfig, self).__init__()

    def get_key(self, d, *keys, default=None, required=False):

        try:
            p = d
            for k in keys:
                p = p[k]
            return p
        except Exception:
            if not required:
                return default

        raise KeyError("/".join(keys))

    def parse_bytes(self, value):
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

    def parse_loglevel(self, value):
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

class SSLConfig(BaseConfig):
    def __init__(self, base):
        self.private_key = self.get_key(base, 'ssl', 'private_key', default="")
        self.certificate = self.get_key(base, 'ssl', 'certificate', default="")

class CORSConfig(BaseConfig):
    def __init__(self, base):
        # TODO: revist default values
        self.origin = self.get_key(base, 'cors', 'origin',
            default="*")
        self.headers = self.get_key(base, 'cors', 'headers',
            default="Origin, X-Requested-With, Content-Type, Accept, Authorization")
        self.methods = self.get_key(base, 'cors', 'methods',
            default="GET, POST, PUT, DELETE, OPTIONS")

class LoggingConfig(BaseConfig):
    def __init__(self, base):
        self.directory = self.get_key(base, 'logging', 'directory', default="./log")
        self.filename = self.get_key(base, 'logging', 'filename', default="server.log")
        self.max_size = self.parse_bytes(self.get_key(base, 'logging', 'max_size', default="2048k"))
        self.num_backups = int(self.get_key(base, 'logging', 'num_backups', default=10))
        self.level = self.parse_loglevel(self.get_key(base, 'logging', 'level', default="error"))

class ApplicationBaseConfig(BaseConfig):
    def __init__(self, data):
        super(ApplicationBaseConfig, self).__init__()

        if isinstance(data, str):
            with open(data, "r") as rf:
                data = yaml.load(rf, Loader=Loader)

        self.init(data)

    def _decrypt_inplace(self, data):
        """ recursivley decrypt all secrets """

        for key, value in data.items():
            if isinstance(value, str):
                if value.startswith(self.decryptor.prefix):
                    value = value.encode("utf-8")
                    data[key] = self.decryptor.decrypt(value).decode("utf-8")

            elif isinstance(value, dict):
                self._decrypt_inplace(value)

    def init(self, data):

        self.null = False

        base = self.get_key(data, "server")

        build_dir = os.path.join(os.getcwd(), "build")
        self.build_dir = self.get_key(base, "build", default=build_dir)

        static_dir = os.path.join(os.getcwd(), "build", "static")
        self.static_dir = self.get_key(base, "static", default=static_dir)

        mode = self.get_key(data, "encryption_mode", default="none")

        logging.debug("encryption mode: %s" % mode)
        if mode == "rsa":
            self.decryptor = CipherConfigDecryptor()
            self._decrypt_inplace(data)
        elif mode == "ssm":
            self.decryptor = ParameterStoreConfigDecryptor()
            self._decrypt_inplace(data)

        # TODO implement true sub classes
        self.host = self.get_key(base, 'host', default="localhost")
        self.port = self.get_key(base, 'port', default=4200)
        # TODO: move this into the appl config
        self.domain = self.get_key(base, 'env', default="production")
        # TODO: move this into the appl config
        self.secret_key = self.get_key(base, 'secret_key', required=False)

        self.ssl = SSLConfig(base)
        self.cors = CORSConfig(base)
        self.logging = LoggingConfig(base)



