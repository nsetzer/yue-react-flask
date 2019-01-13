
import os

from sqlalchemy.schema import Table, Column, ForeignKey
from sqlalchemy.types import Integer, String
from sqlalchemy import and_, or_, not_, select, column, update, insert, delete

from .tables.storage import FileSystemStorageTableV1
from .db import db_connect_impl, db_add_column, db_get_columns, db_iter_rows
from .util import format_storage_path

class _MigrateV1Context(object):
    def __init__(self, dbv1, env_yaml):
        super(_MigrateV1Context, self).__init__()
        self.dbv1 = dbv1
        self.env_yaml = env_yaml

    def fs_storage_v0_to_v1(self, row):

        pwd = os.getcwd()

        file_path = row['path']
        for fs_name, fs_path in self.env_yaml['filesystems'].items():
            fs_root = format_storage_path(fs_path, row['user_id'], pwd)
            if file_path.startswith(fs_root):
                file_path = file_path[len(fs_root):].lstrip("/").lstrip("\\")
                break

        record = {
            'user_id': row['user_id'],
            'file_path': file_path,
            'storage_path': row['path'],
            'permission': row['permission'],
            'version': 1,
            'size': row['size'],
            'expired': None,
            'encrypted': 0,
            'public': None,
            'mtime': row['mtime'],
        }
        return record

    def migrate(self):

        db = self.dbv1

        # init the new settings table
        db.session.execute(insert(db.tables.ApplicationSchemaTable)
            .values({"key": "db_version", "value": str(db.tables.version)}))

        # create a connection for the old FileSystemStorageTable
        tbl = FileSystemStorageTableV1(db.metadata)

        # migrate FileSystemStorageTable v1 -> v2

        for row in db_iter_rows(db, tbl):
            updated_row = self.fs_storage_v0_to_v1(row)

            db.session.execute(insert(db.tables.FileSystemStorageTable)
                .values(updated_row))

def migratev1(dbv1, env_yaml):
    """
    dbv1: a database connection, db.tables must implement v1

    v1 adds:
        - a table to store the application schema version
        - a table to store arbitrary user preferences
            - columns: userid, key, json
        - a table to store user session keys
        - updates file system storage table to v2
        - a table to store encryption keys
    """

    # first create the new tables
    dbv1.tables.ApplicationSchemaTable.create(dbv1.engine)

    dbv1.tables.UserSessionTable.create(dbv1.engine)

    dbv1.tables.FileSystemStorageTable.create(dbv1.engine)
    dbv1.tables.FileSystemUserDataTable.create(dbv1.engine)
    dbv1.tables.UserPreferencesTable.create(dbv1.engine)

    dbv1.session = dbv1.session()
    try:
        ctxt = _MigrateV1Context(dbv1, env_yaml)
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