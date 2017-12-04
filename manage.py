
import os, sys

if (sys.version_info[0] == 2):
    raise RuntimeError("python2 not supported")

from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand

from server.app import app, db, dbtables, list_routes
from server.cli.config import db_init, db_drop_all

migrate = Migrate(app, db)
manager = Manager(app)

# migrations
manager.add_command('db', MigrateCommand)

@manager.command
def create():
    """Creates the db tables."""
    db_init(db, dbtables, "config/production/env.yml")

@manager.command
def drop():
    """drop the db tables."""
    db_drop__all(db, dbtables)

@manager.command
def routes():
    """List application endpoints"""
    list_routes()


if __name__ == '__main__':
    manager.run()
