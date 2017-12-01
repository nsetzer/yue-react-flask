import os, sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_cors import CORS

import logging
from logging.handlers import RotatingFileHandler

from .dao.tables.tables import DatabaseTables

class EnvironmentConfig(object):
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

        self.build_dir = os.path.join(os.getcwd(), "build")
        self.static_dir = os.path.join(os.getcwd(), "build", "static")

    def setenv_default(self, env, default):
        if env in os.environ:
            self.__dict__[env] = os.environ[env]
        else:
            self.__dict__[env] = default


cfg = EnvironmentConfig()

app = Flask(__name__,
    static_folder=cfg.static_dir,
    template_folder=cfg.build_dir)

app.config['SQLALCHEMY_DATABASE_URI'] = cfg.DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = cfg.SECRET_KEY
app.config['DEBUG'] = cfg.DEBUG
app.config['DEFAULT_ROLE'] = cfg.DEFAULT_ROLE
app.config['DEFAULT_DOMAIN'] = cfg.DEFAULT_DOMAIN

# handler = RotatingFileHandler('foo.log', maxBytes=10000, backupCount=1)
# handler.setLevel(logging.INFO)
# app.logger.addHandler(handler)

# app.logger.addHandler(logging.StreamHandler())
# app.logger.setLevel(logging.INFO)

app.logger.info("database: %s", cfg.DATABASE_URL)

db     = SQLAlchemy(app)
bcrypt = Bcrypt(app)
cors   = CORS(app, resources={r"/api/*": {"origins": "*"}})

dbtables = DatabaseTables(db.metadata)

if not os.path.exists(cfg.build_dir):
    # only an error in production environments
    app.logger.warn("build directory not found\n")

