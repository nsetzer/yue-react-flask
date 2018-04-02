#! python $this update

import os, sys, argparse

if (sys.version_info[0] == 2):
    raise RuntimeError("python2 not supported")

from server.dao.util import hash_password
from server.dao.db import db_remove, db_connect, db_init, db_update, \
    db_populate, db_repopulate

from yue.core.api2 import export_database

def create(args):
    """Creates the db tables."""

    if args.database_url.startswith("sqlite:"):
        db_path = args.database_url.replace("sqlite:///","")
        if not db_remove(db_path):
            raise Exception("cannot remove database")

    db = db_connect(args.database_url)
    db_init(db, db.tables, args.env_cfg_path)

    json_objects = export_database(args.yue_db_path)
    db_populate(db, db.tables, args.username, args.domain, json_objects)

def update(args):
    """updates the db tables."""
    db = db_connect(args.database_url)
    db_update(db, db.tables, args.env_cfg_path)

    json_objects = export_database(args.yue_db_path)
    db_repopulate(db, db.tables, args.username, args.domain, json_objects)

def main():

    path1 = "/home/nsetzer/projects/android/YueMusicPlayer/yue.db"
    path2 = "/Users/nsetzer/Music/Library/yue.db"
    path3 = "D:\\Dropbox\\ConsolePlayer\\yue.db"
    dbpath = None
    for path in [path1, path2, path3]:
        if os.path.exists(path):
            dbpath = path
            break
    else:
        sys.stderr.write("cannot find source db")
        sys.exit(1)

    default_profile = "windev" if sys.platform == "win32" else "development"
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--config_dir', dest='config', default="./config",
                        help='enable verbose logging')
    parser.add_argument('-p', '--profile', dest='profile',
                        default=default_profile,
                        help='default profile to use')

    parser.add_argument('--username', dest='username',
                        default="admin",
                        help='username to populate')

    parser.add_argument('--domain', dest='domain',
                        default="production",
                        help='domain to populate')

    parser.add_argument('--db', dest='database_url',
                        default="sqlite:///database.sqlite",
                        help='the database connection string')

    parser.add_argument('mode', type=str,
                        help='action to take')

    parser.add_argument('extra', type=str, nargs="*",
                        help='extra positional parameters')

    args = parser.parse_args()

    args.yue_db_path = dbpath
    args.env_cfg_path = os.path.join(args.config, args.profile, "env.yml")
    args.app_cfg_path = os.path.join(args.config, args.profile, "application.yml")

    if not os.path.exists(args.env_cfg_path):
        sys.stderr.write("cannot find env cfg: %s" % args.env_cfg_path)
        sys.exit(1)

    if args.mode == "create":
        create(args)
    elif args.mode == "update":
        update(args)

if __name__ == '__main__':
    main()