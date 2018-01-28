
import os, sys, argparse

if (sys.version_info[0] == 2):
    raise RuntimeError("python2 not supported")

#from flask_script import Manager
#from flask_migrate import Migrate, MigrateCommand


from server.config import Config

parser = argparse.ArgumentParser(description='yue server')
parser.add_argument('--config', type=str,
                    default="config/development/application.yml",
                    help='application config path')

parser.add_argument('mode', type=str,
                    help='action to take')

print(sys.argv)
args = parser.parse_args()

cfg = Config.init(args.config)

from server.app import app, db, dbtables, list_routes
from server.cli.config import db_init, db_drop_all

#migrate = Migrate(app, db)
#manager = Manager(app)

# migrations
#manager.add_command('db', MigrateCommand)

def create():
    """Creates the db tables."""
    db_init(db, dbtables, "config/production/env.yml")

def drop():
    """drop the db tables."""
    db_drop_all(db, dbtables)

def routes():
    """List application endpoints"""
    list_routes()


if __name__ == '__main__':

    if args.mode == "create":
        create()
    elif args.mode == "drop":
        drop()
    elif args.mode == "routes":
        routes()
