
"""
this test is intended to demonstrate how to migrate the database
between schema versions
"""

import os, sys
import unittest

from .db import db_connect_impl, db_add_column, db_get_columns, db_iter_rows

from sqlalchemy.schema import Table, Column, ForeignKey
from sqlalchemy.types import Integer, String
from sqlalchemy import and_, or_, not_, select, column, update, insert, delete

def DomainTableV1(metadata):
    return Table('user_test', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String, unique=True, nullable=False),
    )

def DomainTableV2(metadata):
    return Table('user_test', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String, unique=True, nullable=False),
        Column('version', String, nullable=False),
    )

def DomainTableV3(metadata):
    return Table('user_test_v3', metadata,
        Column('id', Integer, primary_key=True),
        Column('username', String, unique=True, nullable=False),
        Column('version', Integer, nullable=False),
    )

class DatabaseTablesV1(object):
    """define all tables required for the database"""
    version = 1

    def __init__(self, metadata):
        super(DatabaseTablesV1, self).__init__()

        self.DomainTable = DomainTableV1(metadata)

class DatabaseTablesV2(object):
    """define all tables required for the database"""
    version = 2

    def __init__(self, metadata):
        super(DatabaseTablesV2, self).__init__()

        self.DomainTable = DomainTableV2(metadata)

class DatabaseTablesV3(object):
    """define all tables required for the database"""
    version = 3

    def __init__(self, metadata):
        super(DatabaseTablesV3, self).__init__()

        self.DomainTable = DomainTableV3(metadata)

def migratev2(db):
    """
    migrate from version 1 to 2 of DatabaseTables
        - add a new column to the user_test table
    """

    if db.tables.version != 2:
        raise ValueError(db.tables.version)

    # migrate version 1 table to version 2
    column_names = db_get_columns(db, db.tables.DomainTable)
    for column in db.tables.DomainTable.c:
        if column.name not in column_names:
            db_add_column(db, db.tables.DomainTable, column)

def migratev3(db):
    """
    migrate from version 2 to 3 of DatabaseTables
        - create a new user_test table
        - migrate date from the old table
        - drop the old table
    """

    if db.tables.version != 3:
        raise ValueError(db.tables.version)

    # migrate version 2 table to version 3
    tbl = DomainTableV2(db.metadata)

    # first create the new table
    db.tables.DomainTable.create(db.engine)

    # in a single session, migrate all data from the old table to the new one
    # map column name -> username
    # the new column version will default to 0 for all entries
    sess = db.session()
    for row in db_iter_rows(db, tbl, sess=sess):
        values = {
            "id": row['id'],
            "username": row['name'],
            "version": 0,
        }
        sess.execute(db.tables.DomainTable.insert(values))

    sess.commit()

    # drop the old version of the table
    tbl.drop(db.engine)

class MigrateTestCase(unittest.TestCase):

    def test_migrate_add_column(self):

        path = "test.db"
        if os.path.exists(path):
            os.remove(path)

        dburl = 'sqlite:///' + path
        db = db_connect_impl(DatabaseTablesV1, dburl, False)

        db.create_all()

        sess = db.session()
        try:
            for i in range(1000):
                query = db.tables.DomainTable.insert(
                    {"id": i, "name": "name-%3d" % i})
                sess.execute(query)
            sess.commit()
        except:
            sess.close()

        keys = set(db_get_columns(db, db.tables.DomainTable))
        self.assertEqual(len(keys), 2)
        self.assertTrue("id" in keys)
        self.assertTrue("name" in keys)
        nitems = len(list(db_iter_rows(db, db.tables.DomainTable)))
        self.assertEqual(nitems, 1000)

        # ------------------------------------------------------------------------
        # migrate by adding a new column
        db = db_connect_impl(DatabaseTablesV2, dburl, False)
        migratev2(db)

        keys = set(db_get_columns(db, db.tables.DomainTable))
        self.assertEqual(len(keys), 3)
        self.assertTrue("id" in keys)
        self.assertTrue("name" in keys)
        self.assertTrue("version" in keys)
        nitems = len(list(db_iter_rows(db, db.tables.DomainTable)))
        self.assertEqual(nitems, 1000)

        # this would fail before the migrate add
        query = db.tables.DomainTable.select()
        result = db.session.execute(query)
        db.session.close()

        # ------------------------------------------------------------------------
        # migrate again by creating a new table
        db = db_connect_impl(DatabaseTablesV3, dburl, False)
        migratev3(db)

        keys = set(db_get_columns(db, db.tables.DomainTable))
        self.assertEqual(len(keys), 3)
        self.assertTrue("id" in keys)
        self.assertTrue("username" in keys)
        self.assertTrue("version" in keys)
        nitems = len(list(db_iter_rows(db, db.tables.DomainTable)))
        self.assertEqual(nitems, 1000)

        if os.path.exists(path):
            os.remove(path)

def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(MigrateTestCase)
    unittest.TextTestRunner().run(suite)

if __name__ == '__main__':
    main()
