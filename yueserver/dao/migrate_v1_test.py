

import os, sys
import unittest

from .db import db_connect_impl, db_add_column, db_get_columns, db_iter_rows

from .tables.tables import DatabaseTablesV0, DatabaseTablesV1

from .migrate import migratev1

from sqlalchemy.schema import Table, Column, ForeignKey
from sqlalchemy.types import Integer, String
from sqlalchemy import and_, or_, not_, select, column, update, insert, delete

def v0_init(db):

    db.create_all()

class MigrateV1TestCase(unittest.TestCase):

    dbpath = "database-v1_test.sqlite"

    def setUp(self):

        if os.path.exists(MigrateV1TestCase.dbpath):
            os.remove(MigrateV1TestCase.dbpath)

    def tearDown(self):

        if os.path.exists(MigrateV1TestCase.dbpath):
            os.remove(MigrateV1TestCase.dbpath)

    def test_migrate_v1(self):

        dburl = 'sqlite:///' + MigrateV1TestCase.dbpath
        dbv0 = db_connect_impl(DatabaseTablesV0, dburl, False)
        v0_init(dbv0)

        dbv1 = db_connect_impl(DatabaseTablesV1, dburl, False)

def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(MigrateV1TestCase)
    unittest.TextTestRunner().run(suite)

if __name__ == '__main__':
    main()
