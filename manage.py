
import os, sys

if (sys.version_info[0] == 2):
    raise RuntimeError("python2 not supported")

from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand

from server.app import app, db, list_routes, db_init, db_drop

migrate = Migrate(app, db)
manager = Manager(app)

# migrations
manager.add_command('db', MigrateCommand)

@manager.command
def create():
    """Creates the db tables."""
    db_init()

@manager.command
def drop():
    """drop the db tables."""
    db_drop()

@manager.command
def routes():
    """List application endpoints"""
    list_routes()


if __name__ == '__main__':
    manager.run()
