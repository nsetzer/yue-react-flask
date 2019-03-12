

import os
import sys
import unittest
import tempfile
import json
import time

from .db import db_init_main, db_connect, main_test
from .user import UserDao
from .storage import StorageDao, \
    StorageException, StorageNotFoundException, FileRecord2
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError

class StorageTestCase(unittest.TestCase):

    db_name = "StorageTestCase"

    @classmethod
    def setUpClass(cls):
        # build a test database, with a minimal configuration
        cls.db_path = "database.test.%s.sqlite" % cls.db_name

        db = db_connect(None)

        env_cfg = {
            'features': ['test', ],
            'filesystems': {
                "default": "{pwd}/data/{user_id}",
                "mem": "mem://memtest"
            },
            'domains': ['test'],
            'roles': [
                {'test': {'features': ['all'], 'filesystems': ["default"]}},
            ],
            'users': [
                {'email': 'user000',
                 'password': 'user000',
                 'domains': ['test'],
                 'roles': ['test']},
            ]
        }

        db_init_main(db, db.tables, env_cfg)

        cls.userDao = UserDao(db, db.tables)

        cls.USERNAME = "user000"
        cls.USER = cls.userDao.findUserByEmail(cls.USERNAME)

        cls.storageDao = StorageDao(db, db.tables)

        user_id = cls.USER['id']
        role_id = cls.USER['role_id']
        cls.fs_default_id = cls.storageDao.getFilesystemId(
            user_id, role_id, "default")

        cls.db = db

    def test_000a_filesystem(self):

        name = "test"
        path = "file:///opt/yueserver"
        file_id = self.userDao.createFileSystem(name, path)

        with self.assertRaises(IntegrityError):
            self.userDao.createFileSystem(name, path)

        role = self.userDao.findFileSystemByName(name)
        self.assertEqual(role['id'], file_id)

        self.userDao.removeFileSystem(file_id)

        role = self.userDao.findFileSystemByName(name)
        self.assertIsNone(role)

    def test_000b_filesystem_permission(self):

        name = "test"
        path = "file:///opt/yueserver"
        file_id = self.userDao.createFileSystem(name, path)

        role = self.userDao.findRoleByName('test')

        self.userDao.addFileSystemToRole(role['id'], file_id)

        exists = self.userDao.roleHasFileSystem(role['id'], file_id)
        self.assertTrue(exists)

        self.userDao.removeFileSystemFromRole(role['id'], file_id)

        exists = self.userDao.roleHasFileSystem(role['id'], file_id)
        self.assertFalse(exists)

    def test_000c_filesystem_scheme(self):

        local_path = "/etc/hosts"
        remote_path = "file:///etc/hosts"

        path1 = self.storageDao.localPathToNormalPath(local_path)
        self.assertEqual(path1, remote_path)

        path2 = self.storageDao.NormalPathTolocalPath(remote_path)
        self.assertEqual(path2, local_path)

    def test_001a_insert_update(self):

        user_id = self.USER['id']

        path = "/insert0"
        data = dict(storage_path='mem://test/' + path,
            preview_path="mem://test/img",
            permission=0o644,
            version=2,
            size=1234,
            expired=None,
            mtime=1234567890,
            encryption=None,
            public_password=None,
            public=None)
        self.storageDao.insertFile(user_id, self.fs_default_id, path, data)

        item = self.storageDao.selectFile(user_id, self.fs_default_id, path)

        self.assertEqual(user_id, item['user_id'])
        self.assertEqual(path, item['file_path'])
        for key, val in data.items():
            self.assertEqual(data[key], item[key], key)

        # show that file all attributes can be changed
        data = dict(storage_path='mem://test2/' + path,
            preview_path="mem://test2/img",
            permission=0o777,
            version=3,
            size=1024,
            expired=123456789,
            mtime=123456789,
            encryption='client',
            public_password='password',
            public='randomid')
        self.storageDao.updateFile(item.id, data)
        item = self.storageDao.selectFile(user_id, self.fs_default_id, path)

        self.assertEqual(user_id, item['user_id'])
        self.assertEqual(path, item['file_path'])
        for key, val in data.items():
            self.assertEqual(data[key], item[key], key)

        # show that a single element can be changed
        data['size'] = 555
        data['version'] += 1
        self.storageDao.updateFile(item.id, dict(size=555))
        item = self.storageDao.selectFile(user_id, self.fs_default_id, path)

        self.assertEqual(user_id, item['user_id'])
        self.assertEqual(path, item['file_path'])
        for key, val in data.items():
            self.assertEqual(data[key], item[key], key)

        # show that the file path can be changed
        data['version'] += 1
        self.storageDao.updateFile(item.id, dict(file_path="/foo"))
        item = self.storageDao.selectFile(user_id, self.fs_default_id, "/foo")

        self.assertEqual(user_id, item['user_id'])
        self.assertEqual("/foo", item['file_path'])

    def test_001b_upsert(self):

        user_id = self.USER['id']

        path = "/insert0"
        data = dict(storage_path='mem://test/' + path,
            preview_path="mem://test/img",
            permission=0o644,
            version=2,
            size=1234,
            expired=None,
            mtime=1234567890,
            encryption=None,
            public_password=None,
            public=None)
        self.storageDao.upsertFile(user_id, self.fs_default_id, path, data)

        item = self.storageDao.selectFile(user_id, self.fs_default_id, path)

        self.assertEqual(user_id, item['user_id'])
        self.assertEqual(path, item['file_path'])
        for key, val in data.items():
            self.assertEqual(data[key], item[key], key)

        data2 = dict(user_id='0', size=555)
        self.storageDao.upsertFile(user_id, self.fs_default_id, path, data2)
        item = self.storageDao.selectFile(user_id, self.fs_default_id, path)

        data['size'] = 555
        data['version'] = data['version'] + 1

        # user_id should not be changed...
        self.assertEqual(user_id, item['user_id'])
        self.assertEqual(path, item['file_path'])
        for key, val in data.items():
            self.assertEqual(data[key], item[key], key)

    def test_001c_insert_constraint(self):
        # user_id, filesystem, filepath cannot be null
        user_id = self.USER['id']

        path = "/insert_null"
        data = dict(storage_path='mem://test/' + path,
            preview_path="mem://test/img",
            permission=0o644,
            version=2,
            size=1234,
            expired=None,
            mtime=1234567890,
            encryption=None,
            public_password=None,
            public=None)
        # not null
        with self.assertRaises(StorageException):
            self.storageDao.insertFile(user_id, None, path, data)

    def test_001d_insert_constraint(self):
        # user_id, filesystem, filepath cannot be null
        user_id = self.USER['id']

        path = "/insert_null"
        data = dict(storage_path='mem://test/' + path,
            preview_path="mem://test/img",
            permission=0o644,
            version=2,
            size=1234,
            expired=None,
            mtime=1234567890,
            encryption=None,
            public_password=None,
            public=None)
        # not null
        with self.assertRaises(StorageException):
            self.storageDao.insertFile(user_id, "default", None, data)

    def test_001e_insert_constraint(self):
        # user_id, filesystem, filepath must be unique
        user_id = self.USER['id']

        fsname = "default"
        path = "/insert_null"
        data = dict(storage_path='mem://test/' + path,
            preview_path="mem://test/img",
            permission=0o644,
            version=2,
            size=1234,
            expired=None,
            mtime=1234567890,
            encryption=None,
            public_password=None,
            public=None)
        self.storageDao.insertFile(user_id, fsname, path, data)

        # integrity error: unique constraint fails
        with self.assertRaises(StorageException):
            self.storageDao.insertFile(user_id, fsname, path, data)

    def test_002a_listdir_insert(self):
        user_id = self.USER['id']

        self.db.delete(self.db.tables.FileSystemStorageTable)
        self.db.delete(self.db.tables.FileSystemTable)
        self.db.delete(self.db.tables.FileSystemPermissionTable)

        path = "/file1.txt"
        data = dict(storage_path='file://' + path, size=1234)
        self.storageDao.insertFile(user_id, self.fs_default_id, path, data)
        path = "/file2.txt"
        data = dict(storage_path='file://' + path, size=1234)
        self.storageDao.insertFile(user_id, self.fs_default_id, path, data)
        path = "/folder/file3.txt"
        data = dict(storage_path='file://' + path, size=1234)
        self.storageDao.insertFile(user_id, self.fs_default_id, path, data)

    def test_002b_listdir(self):
        """
        add two files to different directories and show
        that listing a directory returns the correct names
        """

        user_id = self.USER['id']

        names = ["file1.txt", "file2.txt", "folder"]

        count = 0
        for rec in self.storageDao.listdir(user_id, self.fs_default_id, "/"):
            self.assertTrue(rec.name in names)
            count += 1
        self.assertEqual(len(names), count)

    def test_002c_listdir(self):
        """
        add two files to different directories and show
        that listing a directory returns the correct names
        """

        user_id = self.USER['id']
        names = ["file3.txt"]

        count = 0
        for rec in self.storageDao.listdir(user_id, self.fs_default_id, "/folder/"):
            self.assertTrue(rec.name in names)
            count += 1
        self.assertEqual(len(names), count)

    def test_002d_listall(self):
        """
        add two files to different directories and show
        that listing a directory returns the correct names
        """

        user_id = self.USER['id']
        names = ["file1.txt", "file2.txt", "folder/file3.txt"]

        count = 0
        for rec in self.storageDao.listall(user_id, self.fs_default_id, "/"):
            self.assertTrue(rec['path'] in names, rec['path'])
            count += 1
        self.assertEqual(len(names), count)

        names

    def test_002e_listall(self):

        user_id = self.USER['id']
        names = ["file3.txt"]

        count = 0
        for rec in self.storageDao.listall(user_id, self.fs_default_id, "/folder/"):
            self.assertTrue(rec['path'] in names, rec['path'])
            count += 1
        self.assertEqual(len(names), count)

    def test_002f_listall_limit(self):
        """
        add two files to different directories and show
        that listing a directory returns the correct names
        """

        user_id = self.USER['id']
        names = ["file1.txt", "file2.txt", "folder/file3.txt"]

        # get the files in pages of size 1, sorted by primary key
        count = 0
        for offset in range(len(names)):
            for rec in self.storageDao.listall(user_id, self.fs_default_id,
              "/", limit=1, offset=offset):
                self.assertEqual(rec['path'], names[offset], rec['path'])
                count += 1
        self.assertEqual(len(names), count)

    def test_003a_preview(self):

        user_id = self.USER['id']

        path = "/preview"
        data = dict(storage_path='mem://test/' + path,
            preview_path="mem://test/img",
            permission=0o644,
            version=2,
            size=1234,
            expired=None,
            mtime=1234567890,
            encryption=None,
            public_password=None,
            public=None)
        self.storageDao.insertFile(user_id, self.fs_default_id, path, data)

        item = self.storageDao.selectFile(user_id, self.fs_default_id, path)

        # no item should exist
        pitem = self.storageDao.previewFind(user_id, item.id, 'thumb')
        self.assertIsNone(pitem)

        preview_path = "%s~thumb" % path
        info = {
            'width': 80,
            'height': 60,
            'filesystem_id': self.fs_default_id,
            'size': 8096,
            'path': preview_path
        }
        self.storageDao.previewInsert(
            user_id, item.id, 'thumb', info)

        # read back the preview item that was stored
        pitem = self.storageDao.previewFind(user_id, item.id, 'thumb')
        self.assertIsNotNone(pitem)
        self.assertEqual(pitem.valid, 1)
        self.assertEqual(pitem.width, 80)
        self.assertEqual(pitem.height, 60)
        self.assertEqual(pitem.size, 8096)

        # invalidate
        pitem = self.storageDao.previewInvalidate(user_id, item.id)
        # valid should now be false
        pitem = self.storageDao.previewFind(user_id, item.id, 'thumb')
        self.assertIsNotNone(pitem)
        self.assertEqual(pitem.valid, 0)
        self.assertEqual(pitem.width, 80)
        self.assertEqual(pitem.height, 60)
        self.assertEqual(pitem.size, 8096)

        # remove all items
        pitem = self.storageDao.previewRemove(user_id, item.id)

        # no item should exist
        pitem = self.storageDao.previewFind(user_id, item.id, 'thumb')
        self.assertIsNone(pitem)

    def test_003b_preview_upsert(self):

        user_id = self.USER['id']

        path = "/preview2"
        data = dict(storage_path='mem://test/' + path,
            preview_path="mem://test/img",
            permission=0o644,
            version=2,
            size=1234,
            expired=None,
            mtime=1234567890,
            encryption=None,
            public_password=None,
            public=None)
        self.storageDao.insertFile(user_id, self.fs_default_id, path, data)

        item = self.storageDao.selectFile(user_id, self.fs_default_id, path)

        # no item should exist
        pitem = self.storageDao.previewFind(user_id, item.id, 'thumb')
        self.assertIsNone(pitem)

        preview_path = "%s~thumb" % path
        info = {
            'width': 80,
            'height': 60,
            'filesystem_id': self.fs_default_id,
            'size': 8096,
            'path': preview_path
        }
        self.storageDao.previewUpsert(
            user_id, item.id, 'thumb', info)

        # read back the preview item that was stored
        pitem = self.storageDao.previewFind(user_id, item.id, 'thumb')
        self.assertIsNotNone(pitem)
        self.assertEqual(pitem.valid, 1)
        self.assertEqual(pitem.width, 80)
        self.assertEqual(pitem.height, 60)
        self.assertEqual(pitem.size, 8096)
        self.assertEqual(pitem.path, preview_path)

        preview_path2 = "%s~thumb2" % path
        info = {
            'width': 40,
            'height': 30,
            'filesystem_id': self.fs_default_id,
            'size': 4096,
            'path': preview_path2
        }
        self.storageDao.previewUpsert(
            user_id, item.id, 'thumb', info)

        # read back the preview item that was stored
        pitem = self.storageDao.previewFind(user_id, item.id, 'thumb')
        self.assertIsNotNone(pitem)
        self.assertEqual(pitem.valid, 1)
        self.assertEqual(pitem.width, 40)
        self.assertEqual(pitem.height, 30)
        self.assertEqual(pitem.size, 4096)
        self.assertEqual(pitem.path, preview_path2)

    def test_003c_double_insert(self):

        user_id = self.USER['id']

        path = "/preview3"
        data = dict(storage_path='mem://test/' + path,
            preview_path="mem://test/img",
            permission=0o644,
            version=2,
            size=1234,
            expired=None,
            mtime=1234567890,
            encryption=None,
            public_password=None,
            public=None)
        self.storageDao.insertFile(user_id, self.fs_default_id, path, data)

        item = self.storageDao.selectFile(user_id, self.fs_default_id, path)

        # no item should exist
        pitem = self.storageDao.previewFind(user_id, item.id, 'thumb')
        self.assertIsNone(pitem)

        preview_path = "%s~thumb" % path
        info = {
            'width': 80,
            'height': 60,
            'filesystem_id': self.fs_default_id,
            'size': 8096,
            'path': preview_path
        }
        self.storageDao.previewInsert(
            user_id, item.id, 'thumb', info)

        with self.assertRaises(StorageException):
            self.storageDao.previewInsert(
                user_id, item.id, 'thumb', info)

    def test_004a_tempfile(self):
        # add and remove two temp files
        user_id = self.USER['id']

        uid1 = 'abc'
        uid2 = 'def'

        count, total = self.storageDao.tempFileUsage(user_id)
        self.assertEqual(count, 0)
        self.assertEqual(total, 0)

        self.storageDao.tempFileUpdate(user_id, uid1, 1024)

        count, total = self.storageDao.tempFileUsage(user_id)
        self.assertEqual(count, 1)
        self.assertEqual(total, 1024)

        self.storageDao.tempFileUpdate(user_id, uid2, 512)

        count, total = self.storageDao.tempFileUsage(user_id)
        self.assertEqual(count, 2)
        self.assertEqual(total, 1536)

        self.storageDao.tempFileRemove(user_id, uid1)

        count, total = self.storageDao.tempFileUsage(user_id)
        self.assertEqual(count, 1)
        self.assertEqual(total, 512)

        self.storageDao.tempFileRemove(user_id, uid2)

        count, total = self.storageDao.tempFileUsage(user_id)
        self.assertEqual(count, 0)
        self.assertEqual(total, 0)

class Storage2TestCase(unittest.TestCase):

    db_name = "StorageTestCase"

    @classmethod
    def setUpClass(cls):
        # build a test database, with a minimal configuration
        cls.db_path = "database.test.%s.sqlite" % cls.db_name

        db = db_connect(None)

        env_cfg = {
            'features': ['test', ],
            'filesystems': {
                "default": "{pwd}/data/{user_id}",
                "mem": "mem://memtest"
            },
            'domains': ['test'],
            'roles': [
                {'test': {'features': ['all'], 'filesystems': ["default"]}},
            ],
            'users': [
                {'email': 'user000',
                 'password': 'user000',
                 'domains': ['test'],
                 'roles': ['test']},
            ]
        }

        db_init_main(db, db.tables, env_cfg)

        cls.userDao = UserDao(db, db.tables)

        cls.USERNAME = "user000"
        cls.USER = cls.userDao.findUserByEmail(cls.USERNAME)

        cls.storageDao = StorageDao(db, db.tables)

        user_id = cls.USER['id']
        role_id = cls.USER['role_id']
        cls.fs_default_id = cls.storageDao.getFilesystemId(
            user_id, role_id, "default")

        cls.db = db

    def setUp(self):

        self.db.delete(self.db.tables.FileSystemStorageTable)
        self.db.delete(self.db.tables.FileSystemTable)
        self.db.delete(self.db.tables.FileSystemPermissionTable)

    def test_002b_insert_exists(self):
        """
        """
        user_id = self.USER['id']
        name1 = 'file_insert_src.txt'
        path1 = "/" + name1
        path2 = "file:///" + name1

        with self.assertRaises(StorageNotFoundException):
            self.storageDao.file_info(user_id, self.fs_default_id, path1)

        data = dict(storage_path=path2)
        self.storageDao.insertFile(user_id, self.fs_default_id, path1, data)

        with self.assertRaises(StorageException):
            self.storageDao.insertFile(user_id, self.fs_default_id, path1, data)

    def test_003a_listdir_error(self):

        user_id = self.USER['id']

        with self.assertRaises(StorageException):
            for rec in self.storageDao.listdir(user_id, self.fs_default_id, "/folder"):
                print(rec)  # unreachable

    def test_005a_abspath(self):
        user_id = self.USER['id']
        role_id = self.USER['role_id']

        root = "abspath"
        path = "mem:///opt/yueserver/data"
        name = "file1.txt"

        file_id = self.userDao.createFileSystem(root, path)
        self.userDao.addFileSystemToRole(role_id, file_id)

        # compose an absolute path given a user role
        abspath = self.storageDao.absolutePath(user_id, role_id, root, name)
        self.assertEqual(path + "/" + name, abspath)

        # permission denied, invalid role
        with self.assertRaises(StorageException):
            abspath = self.storageDao.absolutePath(user_id, -1, root, name)

        # root does not exist
        with self.assertRaises(StorageException):
            abspath = self.storageDao.absolutePath(user_id, role_id, "dne", name)

    def test_005a_abspath_sub(self):
        user_id = self.USER['id']
        role_id = self.USER['role_id']

        root = "abspath"
        path = "mem:///opt/yueserver/user/{user_id}"
        name = "file1.txt"

        file_id = self.userDao.createFileSystem(root, path)
        self.userDao.addFileSystemToRole(role_id, file_id)

        abspath = self.storageDao.absolutePath(user_id, role_id, root, name)
        expected = "mem:///opt/yueserver/user/%s/%s" % (user_id, name)
        self.assertEqual(expected, abspath)

    def test_006a_quota(self):
        """
        show that adding files increases the disk usage of a user
        """
        user_id = self.USER['id']

        # self.storageDao.setUserDiskQuota(self.USER['id'], 1024)
        # with self.assertRaises(StorageException):
        #    self.storageDao.userDiskUsage(self.USER['id'])

        count, usage, _ = self.storageDao.userDiskUsage(self.USER['id'])
        self.assertEqual(0, count)
        self.assertEqual(0, usage)

        data = dict(storage_path="file:///file1.txt", size=1024)
        self.storageDao.insertFile(user_id, self.fs_default_id, "/file1.txt", data)
        count, usage, _ = self.storageDao.userDiskUsage(user_id)
        self.assertEqual(1, count)
        self.assertEqual(1024, usage)

        path = "file:///file2.txt"
        data = dict(storage_path="file:///file2.txt", size=512)
        self.storageDao.insertFile(user_id, self.fs_default_id, "/file2.txt", data)
        count, usage, _ = self.storageDao.userDiskUsage(user_id)
        self.assertEqual(2, count)
        self.assertEqual(1536, usage)

        path = "/file1.txt"
        self.storageDao.removeFile(user_id, self.fs_default_id, path)
        count, usage, _ = self.storageDao.userDiskUsage(user_id)
        self.assertEqual(1, count)
        self.assertEqual(512, usage)

    def test_006b_set_quota(self):

        # if not set at all for a user, return 0
        # disables because there is now a default quota for all users
        # quota = self.storageDao.userDiskQuota(self.USER['id'])
        # self.assertEqual(quota, 0)

        # set the disk quota
        self.storageDao.setUserDiskQuota(self.USER['id'], 1024)
        quota = self.storageDao.userDiskQuota(self.USER['id'])
        self.assertEqual(quota, 1024)

        # set the disk quota
        self.storageDao.setUserDiskQuota(self.USER['id'], 2048)
        quota = self.storageDao.userDiskQuota(self.USER['id'])
        self.assertEqual(quota, 2048)

        # set the disk quota
        self.storageDao.setUserDiskQuota(self.USER['id'], 0)
        quota = self.storageDao.userDiskQuota(self.USER['id'])
        self.assertEqual(quota, 0)

    def test_007_encryption(self):

        user_id = self.USER['id']
        password = "password"
        new_password = "new-password"

        with self.assertRaises(StorageException):
            self.storageDao.getEncryptionKey(user_id, password)

        self.storageDao.changePassword(user_id, password, password)

        tab = self.storageDao.dbtables.FileSystemUserEncryptionTable

        key1 = self.storageDao.getEncryptionKey(user_id, password)

        # look up the encrypted key and use to further verify that
        # the update logic on the table is performing correctly
        cryptkey1 = self.storageDao.getUserKey(user_id)
        query = tab.select().where(tab.c.encryption_key == cryptkey1)
        item = self.db.session.execute(query).fetchone()
        self.assertTrue(item.id is not None)
        self.assertTrue(item.expired is None)

        self.storageDao.changePassword(user_id, password, new_password)

        key2 = self.storageDao.getEncryptionKey(user_id, new_password)

        # changing the password should still keep the same key
        self.assertEqual(key1, key2)

        query = tab.select().where(tab.c.encryption_key == cryptkey1)
        item1 = self.db.session.execute(query).fetchone()
        self.assertTrue(item1.id is not None)
        self.assertTrue(item1.expired is not None)

        cryptkey2 = self.storageDao.getUserKey(user_id)
        query = tab.select().where(tab.c.encryption_key == cryptkey2)
        item2 = self.db.session.execute(query).fetchone()
        self.assertTrue(item2.id is not None)
        self.assertTrue(item2.expired is None)
        self.assertTrue(item2.id != item1.id)

    def test_008_public(self):

        user_id = self.USER['id']
        path1 = '/file_insert_public.txt'

        # create and check that it exists
        data = dict(storage_path=path1)
        self.storageDao.insertFile(user_id, self.fs_default_id, path1, data)

        # mark this file as public, generating a public unique id
        public_id1 = self.storageDao.setFilePublic(user_id, path1)

        # no password, this will always fail
        self.assertFalse(self.storageDao.verifyPublicPassword(
            public_id1, "wrong"))

        # show the file is accessible with only the public id
        rec = self.storageDao.publicFileInfo(public_id1)
        self.assertEqual(rec.file_path, path1)

        # mark this file as public, generating a public unique id
        # also store a password
        public_id2 = self.storageDao.setFilePublic(
            user_id, path1, password="password")

        # show that the old id is no longer useable
        with self.assertRaises(StorageNotFoundException):
            self.storageDao.publicFileInfo(public_id1)

        # show the file is accessible with the new id
        rec = self.storageDao.publicFileInfo(public_id2)
        self.assertEqual(rec.file_path, path1)

        # validate the password
        self.assertTrue(self.storageDao.verifyPublicPassword(
            public_id2, "password"))

        self.assertFalse(self.storageDao.verifyPublicPassword(
            public_id2, "wrong"))

        # revoke the public permissions, show that it is not longer accessible
        self.storageDao.setFilePublic(
            user_id, path1, revoke=True)

        with self.assertRaises(StorageNotFoundException):
            self.storageDao.publicFileInfo(public_id1)

        with self.assertRaises(StorageNotFoundException):
            self.storageDao.publicFileInfo(public_id2)

    def test_008_public_dne(self):

        with self.assertRaises(StorageNotFoundException):
            self.storageDao.publicFileInfo("dne")

    # todo:
    #   test that a user cannot CRUD other users files

if __name__ == '__main__':
    main_test(sys.argv, globals())