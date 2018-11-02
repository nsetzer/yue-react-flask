

from sqlalchemy.schema import Table, Column, ForeignKey
from sqlalchemy.types import Integer, String
from sqlalchemy import and_, or_, not_, select, column, update, insert, delete

from .tables.storage import FileSystemStorageTableV1

def migratev1(dbv1):
    """
    dbv1: a database connection, db.tables must implement v1

    v1 adds:
        - a table to store arbitrary user preferences
            - columns: userid, key, json
        - a table to store user session keys
        - updates file system storage table to v2
        -
    """

    # first create the new tables
    db.tables.UserSessionTable.create(db.engine)
    db.tables.UserPreferencesTable.create(db.engine)
    db.tables.self.FileSystemStorageTable.create(db.engine)
    db.tables.FileSystemUserDataTable.create(db.engine)

    # create a connection for the old FileSystemStorageTable
    tbl = FileSystemStorageTableV1(db.metadata)

    # migrate FileSystemStorageTable v1 -> v2


    # delete the old FileSystemStorageTable table
    tbl.drop(db.engine)

    return