
import os
import sys

from sqlalchemy.schema import Table, Column, ForeignKey
from sqlalchemy.types import Integer, String
from sqlalchemy import and_, or_, not_, select, column, update, insert, delete

from .tables.storage import FileSystemStorageTableV1, FileSystemStorageTableV2
from .db import db_connect_impl, db_add_column, db_get_columns, db_iter_rows
from .util import format_storage_path
from .filesys.crypt import generate_secure_password
from .settings import SettingsDao, Settings
from .user import UserDao

import logging

class _MigrateV1Context(object):
    def __init__(self, dbv1):
        super(_MigrateV1Context, self).__init__()
        self.dbv1 = dbv1

    def fs_storage_v0_to_v1(self, row):

        pwd = os.getcwd()

        # strip the filesystem root from the file_path
        # the storage path contains the actual location of the resource
        # while the file_path is the logical resource location the user
        # will interact with.

        # this use the first matching prefix assuming there are no
        # overlaping prefixes in the environment

        fs_items = list(self.dbv1.session.execute(
            self.dbv1.tables.FileSystemTable.select()).fetchall())

        file_path = row['path']
        for fs in fs_items:
            fs_root = format_storage_path(fs.path, row['user_id'], pwd)
            if file_path.startswith(fs_root):
                file_path = '/' + file_path[len(fs_root):].lstrip("/").lstrip("\\")
                break
        else:
            raise Exception("unable to determine root for: %s" % file_path)

        record = {
            'user_id': row['user_id'],
            'file_path': file_path,
            'storage_path': row['path'],
            'permission': row['permission'],
            'version': 1,
            'size': row['size'],
            'expired': None,
            'encryption': None,
            'public_password': None,
            'public': None,
            'mtime': row['mtime'],
        }
        return record

    def migrate(self):

        db = self.dbv1

        # init the new settings table
        db.session.execute(insert(db.tables.ApplicationSchemaTable)
            .values({"key": "db_version", "value": str(db.tables.version)}))

        db.session.execute(insert(db.tables.ApplicationSchemaTable)
            .values({
                "key": "storage_system_key",
                "value": generate_secure_password()
            }))

        # create a connection for the old FileSystemStorageTable
        tbl = FileSystemStorageTableV1(db.metadata)

        # migrate FileSystemStorageTable v1 -> v2

        for row in db_iter_rows(db, tbl):
            updated_row = self.fs_storage_v0_to_v1(row)

            db.session.execute(insert(db.tables.FileSystemStorageTable)
                .values(updated_row))

class _MigrateV2Context(object):
    def __init__(self, dbv2):
        super(_MigrateV2Context, self).__init__()
        self.dbv2 = dbv2

        query = self.dbv2.tables.FileSystemTable.select()
        self.fs_items = list(self.dbv2.session.execute(query).fetchall())

    def fs_storage_v2_to_v3(self, row):
        """
        adds filesystem id to a record
        """

        pwd = os.getcwd()

        fs_id = None
        for fs in self.fs_items:
            fsname = format_storage_path(fs.path, row['user_id'], pwd)
            if row['storage_path'].startswith(fsname):
                fs_id = fs.id
                break
        else:
            raise Exception("unable to determine root for: %s" % file_path)

        row = dict(row)
        row['filesystem_id'] = fs_id

        return row

    def migrate(self):

        db = self.dbv2

        settingsDao = SettingsDao(db, db.tables)
        settingsDao.set("db_version", str(db.tables.version))

        # create a connection for the old FileSystemStorageTable
        tbl = FileSystemStorageTableV2(db.metadata)

        for row in db_iter_rows(db, tbl):
            updated_row = self.fs_storage_v2_to_v3(row)
            st = db.tables.FileSystemStorageTable.insert().values(updated_row)
            db.session.execute(st)

class _MigrateV3Context(object):
    def __init__(self, dbv3):
        super(_MigrateV3Context, self).__init__()
        self.dbv3 = dbv3

        query = self.dbv3.tables.FileSystemTable.select()
        self.fs_items = list(self.dbv3.session.execute(query).fetchall())

    def migrate(self):

        db = self.dbv3

        settingsDao = SettingsDao(db, db.tables)
        settingsDao.set(Settings.db_version, str(db.tables.version))
        default_user_quota = 2**30
        settingsDao.set(Settings.default_user_quota, str(default_user_quota), commit=False)

        userDao = UserDao(db, db.tables)

        # set a default quota if one is not set
        tab = db.tables.FileSystemUserSupplementaryTable
        for domain in userDao.listDomains():
            for user in userDao.listUsers(domain.id):
                query = tab.select().where(tab.c.user_id == user['id'])
                item = db.session.execute(query).fetchone()
                if item is None:
                    print("setting default quota for %s" % user['id'])
                    statement = tab.insert().values({
                        tab.c.user_id: user['id'],
                        tab.c.quota: default_user_quota,
                    })
                    db.session.execute(statement)

def migratev1(dbv1):
    """
    dbv1: a database connection, db.tables must implement v1

    v1 adds:
        - a table to store the application schema version
        - a table to store arbitrary user preferences
            - columns: userid, key, json
        - a table to store user session keys
        - updates file system storage table to v2
        - a table to store encryption keys
    v1 requires:
        - the file system table contains the set of valid file
          systems (fs_name, fs_root)
    """

    # first create the new tables
    dbv1.tables.ApplicationSchemaTable.create(dbv1.engine)

    dbv1.tables.UserSessionTable.create(dbv1.engine)

    dbv1.tables.FileSystemStorageTable.create(dbv1.engine)
    dbv1.tables.FileSystemUserSupplementaryTable.create(dbv1.engine)
    dbv1.tables.FileSystemUserEncryptionTable.create(dbv1.engine)
    dbv1.tables.UserPreferencesTable.create(dbv1.engine)

    dbv1.session = dbv1.session()
    try:
        ctxt = _MigrateV1Context(dbv1)
        ctxt.migrate()
        dbv1.session.commit()
    except:
        dbv1.session.rollback()
        raise
    finally:
        dbv1.session.close()

    # delete the old FileSystemStorageTable table
    # tbl = FileSystemStorageTableV1(db.metadata)
    # tbl.drop(db.engine)

    return

def migratev2(dbv2):

    dbv2.tables.FileSystemStorageTable.create(dbv2.engine)

    dbv2.session = dbv2.session()
    try:
        ctxt = _MigrateV2Context(dbv2)
        ctxt.migrate()
        dbv2.session.commit()
    except:
        dbv2.session.rollback()
        raise
    finally:
        dbv2.session.close()

    return

def migratev3(dbv3):

    """
    two tables were added
    qutoa set for each user is now required
    """

    dbv3.session = dbv3.session()

    try:
        dbv3.tables.FileSystemPreviewStorageTable.create(dbv3.engine)
        dbv3.tables.FileSystemTempFileTable.create(dbv3.engine)

        ctxt = _MigrateV3Context(dbv3)
        ctxt.migrate()
        dbv3.session.commit()
    except:
        dbv3.session.rollback()
        raise
    finally:
        dbv3.session.close()

    return

def migrate_main(db):

    settingsDao = SettingsDao(db, db.tables)

    try:
        version = int(settingsDao.get("db_version"))
    except Exception:
        version = 0

    actions = [
        migratev1,
        migratev2,
        migratev3,
    ]

    if version >= len(actions):
        sys.stdout.write("nothing to migrate. version is %d.\n" % version)
        return

    actions[version](db)

    version = int(settingsDao.get("db_version"))
    sys.stdout.write("database migrated: new version is %d.\n" % version)




