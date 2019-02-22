
import os, sys
import unittest

from .db import db_connect_impl, db_reconnect, \
    db_add_column, db_get_columns, db_iter_rows

from .tables.tables import DatabaseTablesV1, DatabaseTablesV2
from .settings import SettingsDao

from .migrate import migratev2

from sqlalchemy.schema import Table, Column, ForeignKey
from sqlalchemy.types import Integer, String
from sqlalchemy import and_, or_, not_, select, column, update, insert, delete

from .util import hash_password

fs_id = 1
def v1_file_record(user_id, path):
    global fs_id
    record = {
        'id': fs_id,
        'user_id': user_id,
        'file_path': path,
        'storage_path': path,
        'preview_path': None,
        'permission': 0o655,
        'version': 1,
        'size': 1474,
        'expired': None,
        'encryption': None,
        'public_password': None,
        'public': None,
        'mtime': 1234567890,
    }
    fs_id += 1
    return record

def v1_init(db, sample_paths):

    db.create_all()

    settingsDao = SettingsDao(db, db.tables)
    settingsDao.set("db_version", str(db.tables.version))

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

    pwd = os.getcwd()

    for path in sample_paths:

        p1 = "%s/data/%s/%s" % (pwd, user_id, path)
        st = db.tables.FileSystemStorageTable.insert().values(
            v1_file_record(user_id, p1))
        db.session.execute(st)

        p2 = "mem://memtest/%s" % path
        st = db.tables.FileSystemStorageTable.insert().values(
            v1_file_record(user_id, p2))
        db.session.execute(st)

    db.session.commit()

    return {fs_default, fs_music}

class MigrateV2TestCase(unittest.TestCase):

    def test_migrate_v2(self):

        sample_paths = [
            "sample.txt",
            "folder/sample2.txt",
            "folder/subfolder/sample3.txt",
        ]

        dbv1 = db_connect_impl(DatabaseTablesV1, 'sqlite:///', False)
        filesystem_ids = v1_init(dbv1, sample_paths)

        settingsDao = SettingsDao(dbv1, dbv1.tables)
        version = int(settingsDao.get("db_version"))
        self.assertEqual(version, 1)

        dbv2 = db_reconnect(dbv1, DatabaseTablesV2)
        migratev2(dbv2)

        settingsDao = SettingsDao(dbv2, dbv2.tables)
        version = int(settingsDao.get("db_version"))
        self.assertEqual(version, 2)

        # check that the file record was migrated correctly
        # the new table has a filesystem id for each file
        for row in db_iter_rows(dbv2, dbv2.tables.FileSystemStorageTable):
            self.assertTrue(row.filesystem_id in filesystem_ids)

def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(MigrateV2TestCase)
    unittest.TextTestRunner().run(suite)

if __name__ == '__main__':
    main()
