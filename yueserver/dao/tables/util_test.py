import os
import unittest
import tempfile
import json
import datetime

from sqlalchemy.schema import Table, Column, ForeignKey, UniqueConstraint
from sqlalchemy.types import Integer, String, Boolean
from sqlalchemy.sql import func
from sqlalchemy.sql import select

from .util import CreateView, generate_uuid
from ..db import connection_string, db_connect_impl

def TestTable1(metadata):
    return Table('util_test_table1', metadata,
        Column('id', Integer, primary_key=True),
        Column('user_id', String, nullable=False),
        Column('size', Integer, nullable=False)
    )

def TestTable2(metadata):
    return Table('util_test_table2', metadata,
        Column('id', Integer, primary_key=True),
        Column('user_id', String, nullable=False),
        Column('quota', Integer, nullable=False)
    )

class DatabaseTablesV0(object):
    version = 0

    def __init__(self, metadata):
        super(DatabaseTablesV0, self).__init__()
        self.TestTable1 = TestTable1(metadata)
        self.TestTable2 = TestTable2(metadata)

class UtilTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_create_view(self):
        """
        Test the creation of a view

        construct a view that:
            1) joins two tables together
            2) sums one column
            3) assigns a new label to a column
            4) groups by user
        """

        url = connection_string()
        db = db_connect_impl(DatabaseTablesV0, url, False)

        t1 = db.tables.TestTable1
        t2 = db.tables.TestTable2
        query = select([
                t1.c.user_id,
                func.sum(t1.c.size).label('usage'),
                t2.c.quota,
        ]).select_from(t2) \
            .where(t1.c.user_id == t2.c.user_id) \
            .group_by(t1.c.user_id)

        db.engine.execute(CreateView('v_usage_v0', query))

        db.metadata.bind = db.engine
        db.metadata.create_all()

        view = Table('v_usage_v0', db.metadata,
            Column('user_id', String),
            Column('usage', Integer),
            Column('quota', Integer))

        # insert 3 users with different data
        for i, user_id in enumerate(["user0", "user1", "user2"]):

            db.tables.TestTable1.insert().values(
                {'user_id': user_id, 'size': 5 * (i + 1) + 100}).execute()

            db.tables.TestTable1.insert().values(
                {'user_id': user_id, 'size': 7 * (i + 1) + 100}).execute()

            db.tables.TestTable1.insert().values(
                {'user_id': user_id, 'size': 9 * (i + 1) + 100}).execute()

            db.tables.TestTable2.insert().values(
                {'user_id': user_id, 'quota': 400  * (i + 1)}).execute()

        print(dir(view))
        for row in view.select().where(view.c.user_id == 'user0').execute():
            self.assertEqual(row.usage, 321)
            self.assertEqual(row.quota, 400)

def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(UtilTestCase)
    unittest.TextTestRunner().run(suite)

if __name__ == '__main__':
    main()
