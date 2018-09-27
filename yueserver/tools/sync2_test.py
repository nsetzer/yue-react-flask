import os
import sys
import logging
import posixpath
import unittest

from ..dao.db import main_test
from ..dao.filesys.filesys import FileSystem, MemoryFileSystemImpl

from ..app import TestApp
from ..framework.client import FlaskAppClient
from ..framework.application import AppTestClientWrapper

from .sync2 import db_connect, \
    DatabaseTables, LocalStoragDao, \
    _check, RecordBuilder, FileState, FileEnt, DirEnt, \
    _check_get_state

def createTestFile(storageDao, fs, state, variant, rel_path, remote_base, local_base, content=b""):
    """create a file which represents a requested state

    variant: for some states there may be more than one way to produce a file
            variant is an integer which allows for more producing these
            different types of file patterns
    """

    local_path = fs.join(local_base, rel_path)
    remote_path = posixpath.join(remote_base, rel_path)

    if state == FileState.SAME:
        with fs.open(local_path, "wb") as wb:
            wb.write(content)
        info = fs.file_info(local_path)
        record = RecordBuilder() \
            .localFromInfo(info).local(1) \
            .remoteFromInfo(info).remote(1).build()
        storageDao.insert(remote_path, record)
    if state == FileState.PUSH:
        if variant == 0:
            # a file created locally which has never been pushed
            with fs.open(local_path, "wb") as wb:
                wb.write(content)
            info = fs.file_info(local_path)
            record = RecordBuilder().build()
            storageDao.insert(remote_path, record)
        elif variant == 1:
            # a file which exists locally and remotely and has been changed
            with fs.open(local_path, "wb") as wb:
                wb.write(content)
            info = fs.file_info(local_path)
            record = RecordBuilder() \
                .localFromInfo(info).local(1) \
                .remoteFromInfo(info).remote(1).build()
            fs.set_mtime(local_path, info.mtime + 10)
            storageDao.insert(remote_path, record)
    if state == FileState.PULL:
        if variant == 0:
            # a file which does not exist locally
            record = RecordBuilder().remote(1, 1, 1, 1).build()
            storageDao.insert(remote_path, record)
        if variant == 1:
            # the remote version is newer, locally has not changed
            with fs.open(local_path, "wb") as wb:
                wb.write(content)
            info = fs.file_info(local_path)
            record = RecordBuilder() \
                .localFromInfo(info).local(1) \
                .remoteFromInfo(info).remote(2).build()
            storageDao.insert(remote_path, record)
    if state == FileState.CONFLICT_MODIFIED:
        with fs.open(local_path, "wb") as wb:
            wb.write(content)
        info = fs.file_info(local_path)
        record = RecordBuilder() \
            .localFromInfo(info).local(1) \
            .remoteFromInfo(info).remote(2).build()
        fs.set_mtime(local_path, info.mtime + 10)
        storageDao.insert(remote_path, record)
    if state == FileState.CONFLICT_CREATED:
        with fs.open(local_path, "wb") as wb:
            wb.write(content)
        info = fs.file_info(local_path)
        record = RecordBuilder() \
            .remoteFromInfo(info).remote(2).build()
        storageDao.insert(remote_path, record)
    if state == FileState.CONFLICT_VERSION:
        if variant == 0:
            with fs.open(local_path, "wb") as wb:
                wb.write(content)
            info = fs.file_info(local_path)
            record = RecordBuilder() \
                .localFromInfo(info).local(2) \
                .remoteFromInfo(info).remote(1).build()
            storageDao.insert(remote_path, record)
        elif variant == 1:
            with fs.open(local_path, "wb") as wb:
                wb.write(content)
            info = fs.file_info(local_path)
            record = RecordBuilder() \
                .localFromInfo(info).local(1) \
                .remoteFromInfo(info).remote(1, 6).build()
            storageDao.insert(remote_path, record)
    if state == FileState.DELETE_BOTH:
        with fs.open(local_path, "wb") as wb:
            wb.write(content)
        info = fs.file_info(local_path)
        fs.remove(local_path)
        record = RecordBuilder() \
            .localFromInfo(info).local(1).build()
        storageDao.insert(remote_path, record)
    if state == FileState.DELETE_REMOTE:
        with fs.open(local_path, "wb") as wb:
            wb.write(content)
        info = fs.file_info(local_path)
        record = RecordBuilder() \
            .localFromInfo(info).local(1).build()
        storageDao.insert(remote_path, record)
    if state == FileState.DELETE_LOCAL:
        with fs.open(local_path, "wb") as wb:
            wb.write(content)
        info = fs.file_info(local_path)
        fs.remove(local_path)
        record = RecordBuilder() \
            .localFromInfo(info).local(1) \
            .remoteFromInfo(info).remote(1).build()
        storageDao.insert(remote_path, record)

DIR_E_LOCAL = -1
DIR_E_BOTH = 0
DIR_E_REMOTE = 1

def createTestDirectory(storageDao, fs, dir_state, rel_path, remote_base, local_base):

    """
    directories don't actually exist and can't be empty
    create a '.keep' file to implicitly create a directory.
    """
    local_path = fs.join(local_base, rel_path, ".keep")
    remote_path = posixpath.join(remote_base, rel_path, ".keep")

    # remote | local
    # (none  , none) : not possible
    # (none  , true) : push
    # (true  , none) : pull
    # (true  , true) : check : remote may or may not exist

    builder = RecordBuilder()

    if dir_state in (DIR_E_BOTH, DIR_E_LOCAL):
        with fs.open(local_path, "wb") as wb:
            wb.write(b"")
        builder.local(1)

    if dir_state in (DIR_E_BOTH, DIR_E_REMOTE):
        builder.remote(1)

    if dir_state != DIR_E_LOCAL:
        record = builder.build()
        storageDao.insert(remote_path, record)

class CheckSyncTestCase(unittest.TestCase):

    """
    there are 8 states a file could exist in depending on its local, remote
    and actual status. in addition, if all three exist variations in the
    file content can result in additional states which overlap.

    Test:
        1. examples can be created for all possible states, and variants
        2. the _check method can detect these states correctly

    """
    @classmethod
    def setUpClass(cls):

        db = db_connect("sqlite://")  # memory
        db.create_all()

        storageDao = LocalStoragDao(db, db.tables)

        fs = FileSystem()

        cls.db = db
        cls.storageDao = storageDao
        cls.fs = fs

    def setUp(self):
        self.db.delete(self.db.tables.LocalStorageTable)
        MemoryFileSystemImpl.clear()

    def __check(self, state, variant):
        createTestFile(self.storageDao, self.fs, state, variant,
            "local/test.txt", "", "mem://", b"hello world")

        dent = _check(self.storageDao, self.fs, "mem", "local", "mem://local")

        self.assertEqual(len(dent.files), 1)
        actual = _check_get_state(dent.files[0])
        self.assertTrue(actual.startswith(state), actual)
        fent = dent.files[0]
        sys.stderr.write("\r%s %s -> %s \t%s\n" % (state, variant, actual, fent))

    def test_000_state_same(self):
        self.__check(FileState.SAME, 0)

    def test_000_state_push_0(self):
        self.__check(FileState.PUSH, 0)

    def test_000_state_push_1(self):
        self.__check(FileState.PUSH, 1)

    def test_000_state_pull_0(self):
        self.__check(FileState.PULL, 0)

    def test_000_state_pull_1(self):
        self.__check(FileState.PULL, 1)

    def test_000_state_conflict_0(self):
        self.__check(FileState.CONFLICT_MODIFIED, 0)

    def test_000_state_conflict_1(self):
        self.__check(FileState.CONFLICT_CREATED, 0)

    def test_000_state_conflict_2(self):
        self.__check(FileState.CONFLICT_VERSION, 0)

    def test_000_state_conflict_3(self):
        self.__check(FileState.CONFLICT_VERSION, 1)

    def test_000_state_delete_both(self):
        self.__check(FileState.DELETE_BOTH, 0)

    def test_000_state_delete_remote(self):
        self.__check(FileState.DELETE_REMOTE, 0)

    def test_000_state_delete_remote(self):
        self.__check(FileState.DELETE_LOCAL, 0)

    def test_001_dir_both(self):
        createTestDirectory(self.storageDao, self.fs, DIR_E_BOTH,
            "subfolder", "", "mem://")

        dent = _check(self.storageDao, self.fs, "mem", "", "mem://")

        self.assertEqual(len(dent.dirs), 1)
        remote, local = list(dent.dirs)[0]

        self.assertTrue(remote is not None)
        self.assertTrue(local is not None)

    def test_001_dir_remote(self):
        createTestDirectory(self.storageDao, self.fs, DIR_E_REMOTE,
            "subfolder", "", "mem://")

        dent = _check(self.storageDao, self.fs, "mem", "", "mem://")

        self.assertEqual(len(dent.dirs), 1)
        remote, local = list(dent.dirs)[0]

        self.assertTrue(remote is not None)
        self.assertTrue(local is None)

    def test_001_dir_local(self):
        createTestDirectory(self.storageDao, self.fs, DIR_E_LOCAL,
            "subfolder", "", "mem://")

        dent = _check(self.storageDao, self.fs, "mem", "", "mem://")

        self.assertEqual(len(dent.dirs), 1)
        remote, local = list(dent.dirs)[0]

        self.assertTrue(remote is None)
        self.assertTrue(local is not None)

if __name__ == '__main__':
    main_test(sys.argv, globals())

