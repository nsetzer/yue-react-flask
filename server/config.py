
import os, sys

import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

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

        print(data)

    @staticmethod
    def instance():
        if Config._instance is None:
            Config._instance = EnvironmentConfig()
        return Config._instance

class EnvironmentConfig(Config):
    """
    A configuration option which takes values from the current environment
    """

    def __init__(self):
        super(EnvironmentConfig, self).__init__()

        self.setenv_default("DEFAULT_ROLE", "user")
        self.setenv_default("DEFAULT_DOMAIN", "test")

        self.setenv_default("ENV", "production")
        self.setenv_default("DEBUG", "False")
        self.DEBUG = (self.DEBUG.lower() == "true") or \
            (self.ENV == "development")

        # self.setenv_default("PORT",4200)
        self.setenv_default("SECRET_KEY", "SECRET")
        self.setenv_default("DATABASE_URL",
            "sqlite:///" + os.path.join(os.getcwd(), "app.db"))

    def setenv_default(self, env, default):
        if env in os.environ:
            self.__dict__[env] = os.environ[env]
        else:
            self.__dict__[env] = default





