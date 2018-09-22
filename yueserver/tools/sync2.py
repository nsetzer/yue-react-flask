#! python $this init -u admin:admin localhost:4200

import os, sys
import argparse
import posixpath
import logging
import json

import yueserver
from yueserver.tools.upload import S3Upload
from yueserver.dao.search import regexp
from yueserver.app import connect
from yueserver.framework.client import split_auth
from yueserver.framework.crypto import CryptoManager
from yueserver.tools.sync import SyncManager

from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm.session import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy.schema import Table, Column
from sqlalchemy.types import Integer, String

def LocalStorageTable(metadata):
    return Table('filesystem_storage', metadata,
        # text
        Column('relpath', String, unique=True, nullable=False),
        # number
        Column('local_version', Integer, default=0),
        Column('remote_version', Integer, default=0),
        Column('size', Integer, default=0),
        # date
        Column('mtime', Integer, default=lambda: int(time.time()))
    )

class DatabaseTables(object):
    def __init__(self, metadata):
        super(DatabaseTables, self).__init__()
        self.LocalStorageTable = LocalStorageTable(metadata)

def db_connect(connection_string):

    if connection_string is None or connection_string == ":memory:":
        connection_string = 'sqlite://'

    engine = create_engine(connection_string)
    Session = scoped_session(sessionmaker(bind=engine))

    db = lambda: None
    db.engine = engine
    db.metadata = MetaData()
    db.session = Session
    db.tables = DatabaseTables(db.metadata)
    db.connection_string = connection_string
    db.kind = lambda: connection_string.split(":")[0]
    db.conn = db.session.bind.connect()
    db.conn.connection.create_function('REGEXP', 2, regexp)
    db.create_all = lambda: db.metadata.create_all(engine)

    path = connection_string[len("sqlite:///"):]
    if path and not os.access(path, os.W_OK):
        logging.warning("database at %s not writable" % connection_string)

    return db

def get_cfg(directory):

    local_base = directory

    relpath = ""
    names = os.listdir(directory)
    while '.yue' not in names:
        temp, t = os.path.split(directory)
        if relpath:
            relpath = t + "/" + relpath
        else:
            relpath = t
        if temp == directory:
            break
        directory = temp
        names = os.listdir(directory)

    cfgdir = os.path.join(directory, '.yue')
    if not os.path.exists(cfgdir):
        raise Exception("not found: %s" % cfgdir)

    pemkey_path = os.path.join(cfgdir, 'rsa.pem')
    with open(pemkey_path, "rb") as rb:
        pemkey = rb.read()

    userdata_path = os.path.join(cfgdir, 'userdata.json')
    with open(userdata_path, "r") as rf:
        userdata = json.load(rf)

    cm = CryptoManager()
    userdata['password'] = cm.decrypt64(pemkey,
        userdata['password']).decode("utf-8")

    userdata['cfgdir'] = directory
    userdata['local_base'] = local_base
    userdata['default_remote_base'] = userdata['remote_base']
    userdata['remote_base'] = posixpath.join(userdata['remote_base'], relpath)

    return userdata

def get_mgr(directory, dryrun=False):

    userdata = get_cfg(directory)

    client = connect(userdata['hostname'],
        userdata['username'], userdata['password'])

    mgr = SyncManager(client, userdata['root'], userdata['cfgdir'], dryrun)
    mgr.setDirectory(userdata['local_base'])

    return mgr

def cli_init(args):

    cfgdir = os.path.join(args.local_base, ".yue")
    dbpath = os.path.abspath(os.path.join(cfgdir, "database.sqlite"))
    userpath = os.path.abspath(os.path.join(cfgdir, "userdata.json"))
    if not os.path.exists(cfgdir):
        os.makedirs(cfgdir)

    dburl = "sqlite:///" + dbpath
    db = db_connect(dburl)
    db.create_all()

    if args.username is None:
        args.password = input("username:")
    if args.password is None and ':' in args.username:
        args.username, args.password = args.username.split(':', 1)
    elif args.password is None:
        args.password = input("password:")

    cm = CryptoManager()

    private_key, public_key = cm.generate_key(cfgdir, "rsa", 2048)

    enc_password = cm.encrypt64(public_key, args.password.encode("utf-8"))
    userdata = {
        "username": args.username,
        "password": enc_password,
        "hostname": args.hostname,
        "root": args.root,
        "remote_base": args.remote_base,
    }

    with open(userpath, "w") as wf:
        json.dump(userdata, wf, indent=4, sort_keys=True)

def cli_fetch(args):

    userdata = get_cfg(os.getcwd())
    print(userdata)

    client = connect(userdata['hostname'],
        userdata['username'], userdata['password'])

    pass

def cli_status(args):

    mgr = get_mgr(os.getcwd(), True)

    settings = {'pull': True, 'push': True, 'delete': False}
    cont = True
    while cont:
        cont = mgr.next(**settings)

def cli_pull(args):

    mgr = get_mgr(os.getcwd())

    settings = {'pull': True, 'push': False, 'delete': False}
    cont = True
    while cont:
        cont = mgr.next(**settings)

def cli_push(args):

    mgr = get_mgr(os.getcwd())

    settings = {'pull': False, 'push': True, 'delete': False}
    cont = True
    while cont:
        cont = mgr.next(**settings)

def main():

    parser = argparse.ArgumentParser(description='sync utility')
    subparsers = parser.add_subparsers()

    ###########################################################################
    # Init

    parser_init = subparsers.add_parser('init',
        help="initialize a directory")
    parser_init.set_defaults(func=cli_init)

    parser_init.add_argument('-u', '--username',
        default=None)

    parser_init.add_argument('-p', '--password',
        default=None)

    parser_init.add_argument('-b', '--local_base', dest="local_base",
        default=os.getcwd())
    parser_init.add_argument('-r', '--remote_base', dest="remote_base",
        default="")

    parser_init.add_argument('hostname')
    parser_init.add_argument('root', nargs="?", default="default")

    ###########################################################################
    # Fetch

    parser_fetch = subparsers.add_parser('fetch',
        help="update the local database")
    parser_fetch.set_defaults(func=cli_fetch)

    ###########################################################################
    # status

    parser_status = subparsers.add_parser('status',
        help="check for changes")
    parser_status.set_defaults(func=cli_status)

    ###########################################################################
    # Pull

    parser_pull = subparsers.add_parser('pull',
        help="retrieve remote files")
    parser_pull.set_defaults(func=cli_pull)

    ###########################################################################
    # Push

    parser_push = subparsers.add_parser('push',
        help="push local files")
    parser_push.set_defaults(func=cli_push)


    ###########################################################################
    args = parser.parse_args()

    FORMAT = '%(levelname)-8s - %(message)s'
    logging.basicConfig(level=logging.INFO, format=FORMAT)

    if not hasattr(args, 'func'):
        parser.print_help()
    else:
        args.func(args)

if __name__ == '__main__':
    main()

