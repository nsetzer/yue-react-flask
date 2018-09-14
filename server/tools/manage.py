
"""
A cli tool to manage the application database and query information about
the application
"""
import os, sys, argparse, json, logging

"""

python -u -m yue.core.api2 D:/Dropbox/ConsolePlayer/yue.db > yue.json
python -u -m server.tools.manage import yue.json

/c/Python36/python -u -m yue.core.api2 /d/Dropbox/ConsolePlayer/yue.db | \
    python -u util/manage.py import -

"""

if (sys.version_info[0] == 2):
    raise RuntimeError("python2 not supported")

from server.dao.util import hash_password
from server.dao.db import db_remove, db_connect, db_init, \
    db_update, db_repopulate, db_drop_all
from server.dao.user import UserDao
from server.app import YueApp, generate_client
from server.config import Config
from server.resource.util import get_features
from server.framework.client import cli_main
from server.framework.application import FlaskAppClient
from pprint import pformat

def drop(args):
    """Creates the db tables."""

    if args.database_url.startswith("sqlite:"):
        db_path = args.database_url.replace("sqlite:///","")
        if not db_remove(db_path):
            raise Exception("cannot remove database")
    else:
        db = db_connect(args.database_url)
        db_drop_all(db, db.tables)

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

def cli(args):
    """List application endpoints

    Note this usage:
      python -m server.tools.manage cli -- --username admin library.get_song_audio

    the -- after cli will cause all remaining arguments to be passed
    to the cli arg parser
    """

    cli_main(YueApp(Config.null())._registered_endpoints, args.args)

def features(args):
    for feat in sorted(get_features()):
        print(feat)

def hash(args):
    print(hash_password(args.password, args.workfactor).decode("utf-8"))

def setpw(args):
    db = db_connect(args.database_url)
    dao = UserDao(db, db.tables)
    user = dao.findUserByEmail(args.username)
    print(user)
    dao.changeUserPassword(user['id'], args.password)
    print(dao.findUserByEmail(args.username))

def create_user(args):

    db = db_connect(args.database_url)
    dao = UserDao(db, db.tables)

    domain = dao.findDomainByName(args.domain)
    role = dao.findRoleByName(args.role)

    # TODO: should this be in the dao layer?
    if dao.findUserByEmail(args.username):
        raise Exception("already exists: " + args.username)

    dao.createUser(args.username, args.password, domain['id'], role['id'])
    print(dao.findUserByEmail(args.username))

def remove_user(args):

    db = db_connect(args.database_url)
    dao = UserDao(db, db.tables)

    user = dao.findUserByEmail(args.username)

    dao.removeUser(user['id'])

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

def generate_client_(args):
    """
    generate a python package implementing a client Restful interface
    to the endpoints defined by the application
    """

    app = YueApp(Config.null())

    generate_client(app)

def test_(args):

    app = YueApp(Config.null())
    hostname = "https://localhost:4200"
    username = "admin"
    password = "admin"
    client = app.client(hostname, username, password, None, None)

    print(dir(client.user_list_users))

    print(client.endpoints())
    #response = client.user_list_users("production")
    #response = client.files_upload("default", "test/foo.md", open("README.md"))


    #print(response.text)

def main():

    parser = argparse.ArgumentParser(description='database utility')

    ###########################################################################
    # Default Options

    parser.add_argument('--config_dir', dest='config', default="./config",
                        help='directory containing application profiles')

    default_profile = "windev" if sys.platform == "win32" else "development"
    parser.add_argument('-p', '--profile', dest='profile',
                        default=default_profile,
                        help='default profile to use')

    parser.add_argument('--db', dest='database_url',
                        default="sqlite:///database.sqlite",
                        help='the database connection string (sqlite:///database.sqlite)')

    subparsers = parser.add_subparsers()

    ###########################################################################
    # CLI - provides cli access to restful endpoints for a running server

    parser_cli = subparsers.add_parser('cli',
        help="command line interface client")
    parser_cli.add_argument('args',
                            nargs="*",
                            help='cli arguments')
    parser_cli.set_defaults(func=cli)

    ###########################################################################
    # IMPORT - import a json document and update the database

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

    ###########################################################################
    # DROP - drop all tables

    parser_create = subparsers.add_parser('drop',
        help='drop all tables')
    parser_create.set_defaults(func=drop)

    ###########################################################################
    # CREATE - initialize a database

    parser_create = subparsers.add_parser('create',
        help='initialize a database')
    parser_create.set_defaults(func=create)

    ###########################################################################
    # UPDATE - update environment configuration of the database

    parser_update = subparsers.add_parser('update',
        help='update the environment config for an existing database')
    parser_update.set_defaults(func=update)

    ###########################################################################
    # ROUTES - list known endpoints of the rest service

    parser_routes = subparsers.add_parser('routes',
        help='list known routes')
    parser_routes.set_defaults(func=routes)

    ###########################################################################
    # HASH - produce a password hash of the input string

    parser_hash = subparsers.add_parser('hash', help='generate password hash')
    parser_hash.set_defaults(func=hash)

    parser_hash.add_argument('--workfactor', type=int, default=12,
                               help='bcrypt workfactor')

    parser_hash.add_argument('password', type=str,
                               help='the password to hash')

    ###########################################################################
    # SETPW - change a users password

    parser_hash = subparsers.add_parser('setpw', help='change a password')
    parser_hash.set_defaults(func=setpw)

    parser_hash.add_argument('--workfactor', type=int, default=12,
                               help='bcrypt workfactor')

    parser_hash.add_argument('username', type=str,
                               help='the user to update')

    parser_hash.add_argument('password', type=str,
                               help='the password to hash')

    ###########################################################################
    # CREATE_USER - create a user

    parser_hash = subparsers.add_parser('create_user', help='create a user')
    parser_hash.set_defaults(func=create_user)

    parser_hash.add_argument('username', type=str,
                               help='the user to update')

    parser_hash.add_argument('domain', type=str,
                               help='the users default domain')

    parser_hash.add_argument('role', type=str,
                               help='the users default role')

    parser_hash.add_argument('password', type=str,
                               help='the password to hash')

    ###########################################################################
    # REMOVE_USER - remove a user

    parser_hash = subparsers.add_parser('remove_user', help='remove a user')
    parser_hash.set_defaults(func=remove_user)

    parser_hash.add_argument('username', type=str,
                               help='the user to update')

    ###########################################################################
    # FEATURES - list known features used by the rest service

    parser_features = subparsers.add_parser('features',
        help='list known features used by the app')
    parser_features.set_defaults(func=features)

    ###########################################################################
    # GENERATE_CLIENT - generate a python package implementing a client

    parser_test = subparsers.add_parser('generate_client',
        help='generate a client package')
    parser_test.set_defaults(func=generate_client_)

    ###########################################################################
    # TEST - user defined functions

    parser_test = subparsers.add_parser('test',
        help='used for random tests')
    parser_test.set_defaults(func=test_)

    args = parser.parse_args()

    args.env_cfg_path = os.path.join(args.config, args.profile, "env.yml")
    args.app_cfg_path = os.path.join(args.config, args.profile, "application.yml")

    if not os.path.exists(args.env_cfg_path):
        sys.stderr.write("cannot find env cfg: %s" % args.env_cfg_path)
        sys.exit(1)

    args.func(args)

if __name__ == '__main__':

    main()