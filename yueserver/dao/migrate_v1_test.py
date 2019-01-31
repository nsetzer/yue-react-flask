
import os, sys
import unittest

from .db import db_connect_impl, db_reconnect, \
    db_add_column, db_get_columns, db_iter_rows

from .tables.tables import DatabaseTablesV0, DatabaseTablesV1

from .migrate import migratev1

from sqlalchemy.schema import Table, Column, ForeignKey
from sqlalchemy.types import Integer, String
from sqlalchemy import and_, or_, not_, select, column, update, insert, delete

from .util import hash_password

def v0_file_record(user_id, path):
    record = {
        'user_id': user_id,
        'version': 1,
        'path': path,
        'mtime': 1234567890,
        'size': 1474,
        'permission': 0o655,
    }
    return record

def v0_init(db):

    db.create_all()

    # create dummy data for a fake environment

    feat_fsread_id = db.session.execute(insert(db.tables.FeatureTable)
        .values({"feature": "filesystem_read"})).lastrowid

    fs_default = db.session.execute(insert(db.tables.FileSystemTable)
        .values({"name": "default", "path": "{pwd}/data/{user_id}"})).lastrowid

    fs_music = db.session.execute(insert(db.tables.FileSystemTable)
        .values({"name": "music", "path": "mem://memtest"})).lastrowid

    domain_prod_id = db.session.execute(insert(db.tables.DomainTable)
        .values({"name": "production"})).lastrowid

    role_test_id = db.session.execute(insert(db.tables.RoleTable)
        .values({"name": "test"})).lastrowid

    db.session.execute(insert(db.tables.RoleFeatureTable)
        .values({"role_id": role_test_id, "feature_id": feat_fsread_id}))

    db.session.execute(insert(db.tables.FileSystemPermissionTable)
        .values({"role_id": role_test_id, "file_id": fs_default}))

    db.session.execute(insert(db.tables.FileSystemPermissionTable)
        .values({"role_id": role_test_id, "file_id": fs_music}))

    user_ = {
        "email": "testuser",
        "password": hash_password("password", 4),
        "domain_id": domain_prod_id,
        "role_id": role_test_id,
    }

    user_id = db.session.execute(insert(db.tables.UserTable)
        .values(user_)).lastrowid

    # populate the database with fake user data

    sample_paths = [
        "sample.txt",
        "folder/sample2.txt",
        "folder/subfolder/sample3.txt",
    ]

    pwd = os.getcwd()

    for path in sample_paths:

        db.session.execute(insert(db.tables.FileSystemStorageTable)
            .values(v0_file_record(user_id, "%s/data/%s/%s" % (
                pwd, user_id, path))))

        db.session.execute(insert(db.tables.FileSystemStorageTable)
            .values(v0_file_record(user_id, "mem://memtest/%s" % path)))

    db.session.commit()

class MigrateV1TestCase(unittest.TestCase):

    def test_migrate_v1(self):

        dbv0 = db_connect_impl(DatabaseTablesV0, 'sqlite:///', False)
        v0_init(dbv0)

        dbv1 = db_reconnect(dbv0, DatabaseTablesV1)
        migratev1(dbv1)


        # check that the file_path/storage_path was migrated correctly
        sample_paths = [
            "sample.txt",
            "folder/sample2.txt",
            "folder/subfolder/sample3.txt",
        ]

        for row in db_iter_rows(dbv1, dbv1.tables.FileSystemStorageTable):
            for path in sample_paths:
                # paths now have a default prefix, /
                path = "/" + path
                if path == row.file_path:
                    break
            else:
                self.assertFail("unable to match any path")

def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(MigrateV1TestCase)
    unittest.TextTestRunner().run(suite)

if __name__ == '__main__':
    main()
