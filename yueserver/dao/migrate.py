
import os

from sqlalchemy.schema import Table, Column, ForeignKey
from sqlalchemy.types import Integer, String
from sqlalchemy import and_, or_, not_, select, column, update, insert, delete

from .tables.storage import FileSystemStorageTableV1
from .db import db_connect_impl, db_add_column, db_get_columns, db_iter_rows
from .util import format_storage_path
from .filesys.crypt import generate_secure_password

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