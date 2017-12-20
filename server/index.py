import os, sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_cors import CORS

import logging
from logging.handlers import RotatingFileHandler

from .dao.tables.tables import DatabaseTables

from .config import Config

cfg = Config.instance()

app = Flask(__name__,
    static_folder=cfg.static_dir,
    template_folder=cfg.build_dir)

app.config['SQLALCHEMY_DATABASE_URI'] = cfg.database.url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = cfg.secret_key

# todo: these are deprecated and should be removed
app.config['DEFAULT_ROLE'] = "user"
app.config['DEFAULT_DOMAIN'] = "production"

db     = SQLAlchemy(app)
bcrypt = Bcrypt(app)
cors = CORS(app, resources={r"/api/*": {"origins": cfg.cors.origins}})

dbtables = DatabaseTables(db.metadata)

if not os.path.exists(cfg.build_dir):
    # only an error in production environments
    app.logger.warn("build directory not found\n")

