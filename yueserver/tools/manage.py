
"""
A cli tool to manage the application database and query information about
the application
"""
import os, sys, argparse, json, logging

"""

python -u -m yue.core.api2 D:/Dropbox/ConsolePlayer/yue.db > yue.json
python -u -m yueserver.tools.manage import yue.json

/c/Python36/python -u -m yue.core.api2 /d/Dropbox/ConsolePlayer/yue.db | \
    python -u util/manage.py import -

"""

if (sys.version_info[0] == 2):
    raise RuntimeError("python2 not supported")

from ..dao.util import hash_password
from ..dao.db import db_remove, db_connect, db_init, \
    db_update, db_repopulate, db_drop_all, db_drop_songs
from ..dao.user import UserDao
from ..dao.storage import StorageDao
from ..app import YueApp, generate_client
from ..config import Config
from ..resource.util import get_features
from ..framework.client import cli_main
from ..framework.application import FlaskAppClient
from ..framework.crypto import CryptoManager

from pprint import pformat

def drop(args):
    """Creates the db tables."""

    if not args.force:
        string = input("drop? [y/N]").lower()
        if not string or string[0] != 'y':
            sys.stderr.write("drop action canceled by user\n")
            return

    sys.stderr.write("dropping database\n")

    if args.database_url.startswith("sqlite:"):
        db_path = args.database_url.replace("sqlite:///","")
        if not db_remove(db_path):
            raise Exception("cannot remove database")
    else:
        db = db_connect(args.database_url)
        db_drop_all(db, db.tables)

    sys.stderr.write("sucess\n")

def drop_songs(args):
    """Creates the db tables."""

    if not args.force:
        string = input("drop? [y/N]").lower()
        if not string or string[0] != 'y':
            sys.stderr.write("drop action canceled by user\n")
            return

    sys.stderr.write("dropping songs database\n")

    db = db_connect(args.database_url)
    db_drop_all(db, db.tables)

    sys.stderr.write("sucess\n")

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
      python -m yueserver.tools.manage cli -- --username admin library.get_song_audio

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

def generate_secret(args):

    cm = CryptoManager()

    cm.generate_key(args.outdir, args.name, args.size)

def encrypt64(args):

    with open(args.key, "rb") as rb:
        key = rb.read()
    cm = CryptoManager()
    dat = args.data.encode("utf-8")
    sys.stdout.write("%s\n" % cm.encrypt64(key, dat))

def decrypt64(args):

    with open(args.key, "rb") as rb:
        key = rb.read()
    cm = CryptoManager()
    dec = cm.decrypt64(key, args.data).decode("utf-8")
    sys.stdout.write("%s\n" % dec)

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

def import_songs(args):

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

def get_user(args):

    db = db_connect(args.database_url)
    storageDao = StorageDao(db, db.tables)
    userDao = UserDao(db, db.tables)
    user = userDao.findUserByEmail(args.username)

    domain = userDao.findDomainById(user['domain_id'])
    role = userDao.findRoleById(user['role_id'])

    user = dict(user)
    user['role'] = role['name']
    user['domain'] = domain['name']
    user['password'] = user['password'].decode("utf-8")

    file_count, total_bytes = storageDao.userDiskUsage(user['id'])
    quota_bytes = storageDao.userDiskQuota(user['id'], user['role_id'])

    for key, value in sorted(user.items()):
        print("%-10s : %s" % (key, value))

    print("%-10s : %s" % ("#files", file_count))
    print("%-10s : %.3f MB" % ("#bytes", total_bytes / 1024 / 1024))
    print("%-10s : %.3f MB" % ("#quota", quota_bytes / 1024 / 1024))

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
                        default=None,
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
    parser_import.set_defaults(func=import_songs)

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

    parser_drop = subparsers.add_parser('drop',
        help='drop all tables')
    parser_drop.add_argument('--force', action="store_true",
                               help='skip confirmation')
    parser_drop.set_defaults(func=drop)

    ###########################################################################
    # DROP_SONGS - drop all songs

    parser_drop_songs = subparsers.add_parser('drop_songs',
        help='drop all songs leaving basic account info intact')
    parser_drop_songs.add_argument('--force', action="store_true",
                               help='skip confirmation')
    parser_drop_songs.set_defaults(func=drop_songs)

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

    parser_setpw = subparsers.add_parser('setpw', help='change a password')
    parser_setpw.set_defaults(func=setpw)

    parser_setpw.add_argument('--workfactor', type=int, default=12,
                              help='bcrypt workfactor')

    parser_setpw.add_argument('username', type=str,
                              help='the user to update')

    parser_setpw.add_argument('password', type=str,
                              help='the password to hash')

    ###########################################################################
    # generate_secret - generate a public/private keypair

    parser_gensecret = subparsers.add_parser('generate_keypair',
        help='generate a public/private keypair')
    parser_gensecret.set_defaults(func=generate_secret)

    parser_gensecret.add_argument('--outdir', type=str, default="./",
        help='directory to write keys to')

    parser_gensecret.add_argument('--size', type=int, default=2048,
        help='RSA key size')

    parser_gensecret.add_argument('name',
        help='basename for the public and private key')

    ###########################################################################
    # encrypt64 - encrypt a string and encode as a base64 string

    parser_encrypt64 = subparsers.add_parser('encrypt64',
        help='encrypt a string and encode as a base64 string')
    parser_encrypt64.set_defaults(func=encrypt64)

    parser_encrypt64.add_argument('key',
        help='path to the public key to use for encryption')

    parser_encrypt64.add_argument('data',
        help='text string to encrypt')

    ###########################################################################
    # decrypt64 - decrypt a base64 encoded

    parser_decrypt64 = subparsers.add_parser('decrypt64',
        help='decrypt a base64 encoded')
    parser_decrypt64.set_defaults(func=decrypt64)

    parser_decrypt64.add_argument('key',
        help='path to the private key to use for encryption')

    parser_decrypt64.add_argument('data',
        help='text string to encrypt')

    ###########################################################################
    # GET_USER - get information about a user

    parser_get_user = subparsers.add_parser('get_user',
        help='get information about a user')

    parser_get_user.set_defaults(func=get_user)

    parser_get_user.add_argument('username', type=str,
        help='the user to list')

    ###########################################################################
    # CREATE_USER - create a user

    parser_create_user = subparsers.add_parser('create_user',
        help='create a user')
    parser_create_user.set_defaults(func=create_user)

    parser_create_user.add_argument('username', type=str,
                                    help='the user to update')

    parser_create_user.add_argument('domain', type=str,
                                    help='the users default domain')

    parser_create_user.add_argument('role', type=str,
                                    help='the users default role')

    parser_create_user.add_argument('password', type=str,
                                    help='the password to hash')

    ###########################################################################
    # REMOVE_USER - remove a user

    parser_remove_user = subparsers.add_parser('remove_user', help='remove a user')
    parser_remove_user.set_defaults(func=remove_user)

    parser_remove_user.add_argument('username', type=str,
                                    help='the user to update')

    ###########################################################################
    # FEATURES - list known features used by the rest service

    parser_features = subparsers.add_parser('features',
        help='list known features used by the app')
    parser_features.set_defaults(func=features)

    ###########################################################################
    # GENERATE_CLIENT - generate a python package implementing a client

    parser_generate_client = subparsers.add_parser('generate_client',
        help='generate a client package')
    parser_generate_client.set_defaults(func=generate_client_)

    ###########################################################################
    # TEST - user defined functions

    parser_test = subparsers.add_parser('test',
        help='used for random tests')
    parser_test.set_defaults(func=test_)

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    logging.warning("profile: %s" % args.profile)

    args.env_cfg_path = os.path.join(args.config, args.profile, "env.yml")
    args.app_cfg_path = os.path.join(args.config, args.profile, "application.yml")

    if args.database_url is None:
        cfg = Config(args.app_cfg_path)
        args.database_url = cfg.database.url
        logging.warning("database url not given. using profile default: %s" %
            cfg.database.dbhost)

    if not os.path.exists(args.env_cfg_path):
        sys.stderr.write("cannot find env cfg: %s" % args.env_cfg_path)
        sys.exit(1)

    logging.warning("executing task: %s" % args.func.__name__)

    if not hasattr(args, 'func'):
        parser.print_help()
    else:
        args.func(args)

if __name__ == '__main__':

    main()