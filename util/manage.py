
import os, sys, argparse, json

"""
python -u -m yue.core.api2 /d/Dropbox/ConsolePlayer/yue.db | \
    python -u util/manage.py import -

"""

if (sys.version_info[0] == 2):
    raise RuntimeError("python2 not supported")

from server.dao.util import hash_password
from server.dao.db import db_remove, db_connect, db_init, \
    db_update, db_repopulate
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

    cfg = Config.null()
    app = YueApp(cfg)
    routes = app.list_routes()
    for endpoint, methods, url in routes:
        print("{:40s} {:20s} {}".format(endpoint, methods, url))
    sys.stdout.flush()

def features(args):
    for feat in sorted(get_features()):
        print(feat)

def hash(args):
    print(hash_password(args.password, args.workfactor).decode("utf-8"))

def _read_json(path):

    if path == "-":
        return json.load(sys.stdin)
    elif path is not None:
        if not os.path.exists(path):
            sys.stdout.write("cannot find: %s" % path)
            sys.exit(1)
        return json.load(open(path))
    return None

def import_(args):

    do_init = False
    if args.database_url.startswith("sqlite:///"):
        db_path = args.database_url.replace("sqlite:///","")
        if not os.path.exists(db_path):
            do_init = True

    db = db_connect(args.database_url)
    if do_init:
        db_init(db, db.tables, args.env_cfg_path)

    json_objects = _read_json(args.file)

    db_repopulate(db, db.tables, args.username, args.domain, json_objects)

def main():

    parser = argparse.ArgumentParser(description='database utility')

    parser.add_argument('--config_dir', dest='config', default="./config",
                        help='directory containig application profiles')

    default_profile = "windev" if sys.platform == "win32" else "development"
    parser.add_argument('-p', '--profile', dest='profile',
                        default=default_profile,
                        help='default profile to use')

    parser.add_argument('--db', dest='database_url',
                        default="sqlite:///database.sqlite",
                        help='the database connection string')

    subparsers = parser.add_subparsers()

    parser_import = subparsers.add_parser('import',
        help="import json files containing song records")
    parser_import.set_defaults(func=import_)

    parser_import.add_argument('--username', dest='username',
                               default="admin",
                               help='username to populate (admin)')

    parser_import.add_argument('--domain', dest='domain',
                               default="production",
                               help='domain to populate (production)')

    parser_import.add_argument('file',
                               default="-",
                               help='json file to import (- for stdin)')

    parser_create = subparsers.add_parser('create',
        help='initialize a database')
    parser_create.set_defaults(func=create)

    parser_update = subparsers.add_parser('update',
        help='update the environment config for an existing database')
    parser_update.set_defaults(func=update)

    parser_routes = subparsers.add_parser('routes',
        help='list known routes')
    parser_routes.set_defaults(func=routes)

    parser_hash = subparsers.add_parser('hash', help='generate password hash')
    parser_hash.set_defaults(func=hash)

    parser_hash.add_argument('--workfactor', type=int, default=12,
                               help='bcrypt workfactor')

    parser_hash.add_argument('password', type=str,
                               help='the password to hash')

    parser_features = subparsers.add_parser('features',
        help='list known features used by the app')
    parser_features.set_defaults(func=features)

    args = parser.parse_args()

    args.env_cfg_path = os.path.join(args.config, args.profile, "env.yml")
    args.app_cfg_path = os.path.join(args.config, args.profile, "application.yml")

    if not os.path.exists(args.env_cfg_path):
        sys.stderr.write("cannot find env cfg: %s" % args.env_cfg_path)
        sys.exit(1)

    args.func(args)

if __name__ == '__main__':

    main()