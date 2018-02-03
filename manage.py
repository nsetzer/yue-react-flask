
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

args = parser.parse_args()

cfg = Config.init(args.config)

from server.app import app, db, dbtables, list_routes
from server.cli.config import db_init, db_update, db_drop_all
from server.dao.util import hash_password

#migrate = Migrate(app, db)
#manager = Manager(app)

# migrations
#manager.add_command('db', MigrateCommand)

def create():
    """Creates the db tables."""
    db_init(db, dbtables, "config/development/env.yml")

def update():
    """Creates the db tables."""
    db_update(db, dbtables, "config/development/env.yml")

def drop():
    """drop the db tables."""
    db_drop_all(db, dbtables)

def routes():
    """List application endpoints"""
    list_routes()

def hash():
    if len(sys.argv)!=2:
        sys.stdout.write("usage: %s password" % sys.argv[0])
    print(hash_password(sys.argv[1]).decode("utf-8"))

if __name__ == '__main__':

    if args.mode == "create":
        create()
    elif args.mode == "update":
        update()
    elif args.mode == "drop":
        drop()
    elif args.mode == "routes":
        routes()
    elif args.mode == "hash_password":
        hash()