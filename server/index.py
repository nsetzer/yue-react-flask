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

app.config['SQLALCHEMY_DATABASE_URI'] = cfg.DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = cfg.SECRET_KEY
app.config['DEBUG'] = cfg.DEBUG
app.config['DEFAULT_ROLE'] = cfg.DEFAULT_ROLE
app.config['DEFAULT_DOMAIN'] = cfg.DEFAULT_DOMAIN

# app.config['CORS_HEADERS'] = 'Content-Type'
# app.config['CORS_RESOURCES'] = {r"/api/*": {"origins": "*"}}

# handler = RotatingFileHandler('foo.log', maxBytes=10000, backupCount=1)
# handler.setLevel(logging.INFO)
# app.logger.addHandler(handler)

# app.logger.addHandler(logging.StreamHandler())
# app.logger.setLevel(logging.INFO)

app.logger.info("database: %s", cfg.DATABASE_URL)

ORIGINS = "*"
# ORIGINS = "http://localhost:4100"

db     = SQLAlchemy(app)
bcrypt = Bcrypt(app)
cors = CORS(app, resources={r"/api/*": {"origins": ORIGINS}},
            headers="Content-Type")

dbtables = DatabaseTables(db.metadata)

if not os.path.exists(cfg.build_dir):
    # only an error in production environments
    app.logger.warn("build directory not found\n")

