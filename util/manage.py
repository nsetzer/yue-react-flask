#! python $this routes

import os, sys, argparse

if (sys.version_info[0] == 2):
    raise RuntimeError("python2 not supported")

#from flask_script import Manager
#from flask_migrate import Migrate, MigrateCommand

from server.dao.util import hash_password
from server.dao.db import db_remove, db_connect, db_init, db_update
from server.server.app import YueApp
from server.server.config import Config
from server.server.util import get_features

def create(args):
    """Creates the db tables."""

    if args.database_url.startswith("sqlite:"):
        db_path = args.database_url.replace("sqlite:///","")
        if not db_remove(db_path):
            raise Exception("cannot remove database")

    db = db_connect(args.database_url)
    db_init(db, db.tables, args.env_cfg_path)

def update(args):
    """updates the db tables."""
    db = db_connect(args.database_url)
    db_update(db, db.tables, args.env_cfg_path)

def routes(args):
    """List application endpoints"""

    cfg = Config.default()
    app = YueApp(cfg)
    routes = app.list_routes()
    for endpoint, methods, url in routes:
        print("{:40s} {:20s} {}".format(endpoint, methods, url))
    sys.stdout.flush()

def features(args):
    for feat in sorted(get_features()):
        print(feat)

def hash(args):
    if len(args.extra)!=1:
        sys.stderr.write("usage: %s hash password\n" % sys.argv[0])
    print(hash_password(args.extra[0]).decode("utf-8"))


def main():

    default_profile = "windev" if sys.platform == "win32" else "development"
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--config_dir', dest='config', default="./config",
                        help='enable verbose logging')
    parser.add_argument('-p', '--profile', dest='profile',
                        default=default_profile,
                        help='default profile to use')

    parser.add_argument('--db', dest='database_url',
                        default="sqlite:///database.sqlite",
                        help='the database connection string')

    parser.add_argument('mode', type=str,
                        help='action to take')

    parser.add_argument('extra', type=str, nargs="*",
                        help='extra positional parameters')

    args = parser.parse_args()

    args.env_cfg_path = os.path.join(args.config, args.profile, "env.yml")
    args.app_cfg_path = os.path.join(args.config, args.profile, "application.yml")

    if not os.path.exists(args.env_cfg_path):
        sys.stderr.write("cannot find env cfg: %s" % args.env_cfg_path)
        sys.exit(1)

    if args.mode == "create":
        create(args)
    elif args.mode == "update":
        update(args)
    elif args.mode == "routes":
        routes(args)
    elif "hash_password".startswith(args.mode):
        hash(args)
    elif "features".startswith(args.mode):
        features(args)
    else:
        sys.stderr.write("unrecognized mode: %s" % args.mode)



if __name__ == '__main__':

    main()