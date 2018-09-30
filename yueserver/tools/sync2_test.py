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
    DatabaseTables, LocalStoragDao, SyncContext, \
    _check, RecordBuilder, FileState, _sync_file, _sync_file_impl

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
            record = RecordBuilder().remote(1, len(content), 1, 0).build()
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
                .remoteFromInfo(info).remote(1, len(content)).build()
            storageDao.insert(remote_path, record)
        elif variant == 1:
            with fs.open(local_path, "wb") as wb:
                wb.write(content)
            info = fs.file_info(local_path)
            record = RecordBuilder() \
                .localFromInfo(info).local(1) \
                .remoteFromInfo(info).remote(1, len(content), -1).build()
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

        ctxt = SyncContext(None, storageDao, fs, "mem", "local", "mem://local")

        cls.db = db
        cls.storageDao = storageDao
        cls.fs = fs

        cls.ctxt = ctxt

    def setUp(self):
        self.db.delete(self.db.tables.LocalStorageTable)
        MemoryFileSystemImpl.clear()

    def __check(self, state, variant):
        createTestFile(self.storageDao, self.fs, state, variant,
            "test.txt", "local", "mem://local", b"hello world")

        result = _check(self.ctxt, "local", "mem://local")

        self.assertEqual(len(result.files), 1)
        actual = result.files[0].state()
        self.assertTrue(actual.startswith(state), actual)
        fent = result.files[0]

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

        result = _check(self.ctxt, "", "mem://")

        self.assertEqual(len(result.dirs), 1)
        dent = result.dirs[0]

        self.assertEqual(dent.state(), FileState.SAME, dent.state())

    def test_001_dir_remote(self):
        createTestDirectory(self.storageDao, self.fs, DIR_E_REMOTE,
            "subfolder", "", "mem://")

        result = _check(self.ctxt, "", "mem://")

        self.assertEqual(len(result.dirs), 1)
        dent = result.dirs[0]

        self.assertEqual(dent.state(), FileState.PULL, dent.state())

    def test_001_dir_local(self):
        createTestDirectory(self.storageDao, self.fs, DIR_E_LOCAL,
            "subfolder", "", "mem://")

        result = _check(self.ctxt, "", "mem://")

        self.assertEqual(len(result.dirs), 1)
        dent = result.dirs[0]

        self.assertEqual(dent.state(), FileState.PUSH, dent.state())

class TestClient(object):
    """docstring for TestClient"""
    def __init__(self, fs, storageDao):
        super(TestClient, self).__init__()
        self.fs = fs
        self.storageDao = storageDao

    def files_upload(self, root, relpath, rb, mtime=None, permission=None):

        path = "mem://remote/%s" % (relpath)

        with self.fs.open(path, "wb") as wb:
            #for buf in iter(lambda: rb.read(2048), b""):
            #    wb.write(buf)
            for buf in rb:
                wb.write(buf)
        # todo set perm
        # todo assert version
        self.fs.set_mtime(path, mtime)

    def files_get_path(self, root, rel_path, stream=False):
        path = "mem://remote/%s" % (rel_path)
        response = lambda: None
        f = self.fs.open(path, "rb")
        info = self.storageDao.file_info(rel_path)
        response.stream = lambda: iter(lambda: f.read(1024), b"")
        # TODO: this is cheating, will need to make a better test
        # client in the future
        response.headers = {
            'X-YUE-PERMISSION': info['remote_permission'],
            'X-YUE-VERSION': info['remote_version'],
            'X-YUE-MTIME': info['remote_mtime'],
        }
        return response

    def files_delete(self, root, relpath):
        path = "mem://remote/%s" % (relpath)
        self.fs.remove(path)

class SyncTestCase(unittest.TestCase):

    # push / pull should ask how to resolve conflicts unless force is given
    #   either overwrite or do nothing
    # sync should not try to resolve conflicts

    # the transition table for pushing a file given a state.
    # a file should begin in a key state and end in a value state
    transition_push = {
      FileState.SAME: FileState.SAME,
      FileState.PUSH: FileState.SAME,
      FileState.PULL: FileState.PULL,
      FileState.ERROR: FileState.ERROR,
      FileState.CONFLICT_MODIFIED: FileState.SAME,
      FileState.CONFLICT_CREATED: FileState.SAME,
      FileState.CONFLICT_VERSION: FileState.SAME,
      FileState.DELETE_BOTH: None,
      FileState.DELETE_REMOTE: FileState.SAME,
      FileState.DELETE_LOCAL: None,
    }

    # the transition table for pulling a file given a state.
    transition_pull = {
      FileState.SAME: FileState.SAME,
      FileState.PUSH: FileState.PUSH,
      FileState.PULL: FileState.SAME,
      FileState.ERROR: FileState.ERROR,
      FileState.CONFLICT_MODIFIED: FileState.SAME,
      FileState.CONFLICT_CREATED: FileState.SAME,
      FileState.CONFLICT_VERSION: FileState.SAME,
      FileState.DELETE_BOTH: None,
      FileState.DELETE_REMOTE: None,
      FileState.DELETE_LOCAL: FileState.SAME,
    }

    # the transition table for syncing a file given a state.
    # a sync is both a push and pull
    transition_sync = {
      FileState.SAME: FileState.SAME,
      FileState.PUSH: FileState.SAME,
      FileState.PULL: FileState.SAME,
      FileState.ERROR: FileState.ERROR,
      FileState.CONFLICT_MODIFIED: FileState.CONFLICT_MODIFIED,
      FileState.CONFLICT_CREATED: FileState.CONFLICT_CREATED,
      FileState.CONFLICT_VERSION: FileState.CONFLICT_VERSION,
      FileState.DELETE_BOTH: None,
      FileState.DELETE_REMOTE: None,
      FileState.DELETE_LOCAL: None,
    }

    @classmethod
    def setUpClass(cls):

        db = db_connect("sqlite://")  # memory
        db.create_all()

        storageDao = LocalStoragDao(db, db.tables)

        fs = FileSystem()

        client = TestClient(fs, storageDao)

        ctxt = SyncContext(client, storageDao, fs, "mem", "", "mem://local")
        cls.db = db
        cls.storageDao = storageDao
        cls.fs = fs
        cls.client = client

        cls.ctxt = ctxt

    def setUp(self):
        self.db.delete(self.db.tables.LocalStorageTable)
        MemoryFileSystemImpl.clear()

    def __push(self, state, variant):

        root = "mem"
        remote_base = ""
        local_base = "mem://local"
        name = "test.txt"
        local_path = "mem://local/test.txt"
        remote_path = "test.txt"
        remote_abs_path = "mem://remote/test.txt"
        content = b"hello world"
        final_state = self.transition_push[state]

        createTestFile(self.storageDao, self.fs, state, variant,
            name, remote_base, local_base, content)

        result = _check(self.ctxt, remote_base, local_base)
        fent = result.files[0]
        self.assertTrue(fent.state().startswith(state))

        _sync_file_impl(self.ctxt, fent, True, False, True)

        if final_state is None:
            self.assertFalse(self.fs.exists(local_path))
            self.assertTrue(self.storageDao.file_info(remote_path) is None)
            self.assertFalse(self.fs.exists(remote_abs_path),
                MemoryFileSystemImpl._mem_store.keys())
        else:
            result2 = _check(self.ctxt, remote_base, local_base)
            fent2 = result2.files[0]
            self.assertTrue(fent2.state().startswith(final_state), fent2.state())
            self.assertTrue(self.fs.exists(remote_abs_path),
                MemoryFileSystemImpl._mem_store.keys())

    def test_push_000_same_0(self):
        with self.fs.open("mem://remote/test.txt", "wb") as wb:
            wb.write(b"hello world")
        self.__push(FileState.SAME, 0)

    def test_push_000_push_0(self):
        # variant 0, remote does not yet exist
        self.__push(FileState.PUSH, 0)

    def test_push_000_push_1(self):
        # variant 1, overwrite remote
        with self.fs.open("mem://remote/test.txt", "wb") as wb:
            wb.write(b"hello world")
        self.__push(FileState.PUSH, 1)

    def test_push_000_pull_0(self):
        with self.fs.open("mem://remote/test.txt", "wb") as wb:
            wb.write(b"hello world")
        self.__push(FileState.PULL, 0)

    def test_push_000_pull_1(self):
        with self.fs.open("mem://remote/test.txt", "wb") as wb:
            wb.write(b"hello world")
        self.__push(FileState.PULL, 1)

    def test_push_000_conflict_0(self):
        with self.fs.open("mem://remote/test.txt", "wb") as wb:
            wb.write(b"hello world")
        self.__push(FileState.CONFLICT_MODIFIED, 0)

    def test_push_000_conflict_1(self):
        with self.fs.open("mem://remote/test.txt", "wb") as wb:
            wb.write(b"hello world")
        self.__push(FileState.CONFLICT_CREATED, 0)

    def test_push_000_conflict_2(self):
        with self.fs.open("mem://remote/test.txt", "wb") as wb:
            wb.write(b"hello world")
        self.__push(FileState.CONFLICT_VERSION, 0)

    def test_push_000_conflict_3(self):
        with self.fs.open("mem://remote/test.txt", "wb") as wb:
            wb.write(b"hello world")
        self.__push(FileState.CONFLICT_VERSION, 1)

    def test_push_000_delete_0(self):
        self.__push(FileState.DELETE_BOTH, 0)

    def test_push_000_delete_1(self):
        self.__push(FileState.DELETE_REMOTE, 0)

    def test_push_000_delete_2(self):
        with self.fs.open("mem://remote/test.txt", "wb") as wb:
            wb.write(b"hello world")
        self.__push(FileState.DELETE_LOCAL, 0)

    def __pull(self, state, variant):

        root = "mem"
        remote_base = ""
        local_base = "mem://local"
        name = "test.txt"
        local_path = "mem://local/test.txt"
        remote_path = "test.txt"
        remote_abs_path = "mem://remote/test.txt"
        content = b"hello world"
        final_state = self.transition_pull[state]

        createTestFile(self.storageDao, self.fs, state, variant,
            name, remote_base, local_base, content)

        result = _check(self.ctxt, remote_base, local_base)
        fent = result.files[0]
        self.assertTrue(fent.state().startswith(state))

        _sync_file_impl(self.ctxt, fent, False, True, True)

        if final_state is None:
            self.assertFalse(self.fs.exists(local_path))
            self.assertTrue(self.storageDao.file_info(remote_path) is None)
            self.assertFalse(self.fs.exists(remote_abs_path),
                MemoryFileSystemImpl._mem_store.keys())
        else:
            result2 = _check(self.ctxt, remote_base, local_base)
            fent2 = result2.files[0]
            self.assertTrue(fent2.state().startswith(final_state), fent2.state())
            self.assertTrue(self.fs.exists(local_path),
                MemoryFileSystemImpl._mem_store.keys())

    def test_pull_000_same_0(self):
        with self.fs.open("mem://remote/test.txt", "wb") as wb:
            wb.write(b"hello world")
        self.__pull(FileState.SAME, 0)

    def test_pull_000_push_0(self):
        # variant 0, remote does not yet exist
        self.__pull(FileState.PUSH, 0)

    def test_pull_000_push_1(self):
        # variant 1, overwrite remote
        with self.fs.open("mem://remote/test.txt", "wb") as wb:
            wb.write(b"hello world")
        self.__pull(FileState.PUSH, 1)

    def test_pull_000_pull_0(self):
        with self.fs.open("mem://remote/test.txt", "wb") as wb:
            wb.write(b"hello world")
        self.__pull(FileState.PULL, 0)

    def test_pull_000_pull_1(self):
        with self.fs.open("mem://remote/test.txt", "wb") as wb:
            wb.write(b"hello world")
        self.__pull(FileState.PULL, 1)

    def test_pull_000_conflict_0(self):
        with self.fs.open("mem://remote/test.txt", "wb") as wb:
            wb.write(b"hello world")
        self.__pull(FileState.CONFLICT_MODIFIED, 0)

    def test_pull_000_conflict_1(self):
        with self.fs.open("mem://remote/test.txt", "wb") as wb:
            wb.write(b"hello world")
        self.__pull(FileState.CONFLICT_CREATED, 0)

    def test_pull_000_conflict_2(self):
        with self.fs.open("mem://remote/test.txt", "wb") as wb:
            wb.write(b"hello world")
        self.__pull(FileState.CONFLICT_VERSION, 0)

    def test_pull_000_conflict_3(self):
        with self.fs.open("mem://remote/test.txt", "wb") as wb:
            wb.write(b"hello world")
        self.__pull(FileState.CONFLICT_VERSION, 1)

    def test_pull_000_delete_0(self):
        self.__pull(FileState.DELETE_BOTH, 0)

    def test_pull_000_delete_1(self):
        self.__pull(FileState.DELETE_REMOTE, 0)

    def test_pull_000_delete_2(self):
        with self.fs.open("mem://remote/test.txt", "wb") as wb:
            wb.write(b"hello world")
        self.__pull(FileState.DELETE_LOCAL, 0)

    def __sync(self, state, variant):

        root = "mem"
        remote_base = ""
        local_base = "mem://local"
        name = "test.txt"
        local_path = "mem://local/test.txt"
        remote_path = "test.txt"
        remote_abs_path = "mem://remote/test.txt"
        content = b"hello world"
        final_state = self.transition_sync[state]

        createTestFile(self.storageDao, self.fs, state, variant,
            name, remote_base, local_base, content)

        result = _check(self.ctxt, remote_base, local_base)
        fent = result.files[0]
        self.assertTrue(fent.state().startswith(state))

        _sync_file_impl(self.ctxt, fent, True, True, True)

        if final_state is None:
            self.assertFalse(self.fs.exists(local_path))
            self.assertTrue(self.storageDao.file_info(remote_path) is None)
            self.assertFalse(self.fs.exists(remote_abs_path),
                MemoryFileSystemImpl._mem_store.keys())
        else:
            result2 = _check(self.ctxt, remote_base, local_base)
            fent2 = result2.files[0]
            self.assertTrue(fent2.state().startswith(final_state), fent2.state())
            self.assertTrue(self.fs.exists(local_path),
                MemoryFileSystemImpl._mem_store.keys())

    def test_sync_000_same_0(self):
        self.fs.open("mem://remote/test.txt", "wb").close()
        self.__sync(FileState.SAME, 0)

    def test_sync_000_push_0(self):
        # variant 0, remote does not yet exist
        self.__sync(FileState.PUSH, 0)

    def test_sync_000_push_1(self):
        # variant 1, overwrite remote
        with self.fs.open("mem://remote/test.txt", "wb") as wb:
            wb.write(b"hello world")
        self.__sync(FileState.PUSH, 1)

    def test_sync_000_pull_0(self):
        with self.fs.open("mem://remote/test.txt", "wb") as wb:
            wb.write(b"hello world")
        self.__sync(FileState.PULL, 0)

    def test_sync_000_pull_1(self):
        with self.fs.open("mem://remote/test.txt", "wb") as wb:
            wb.write(b"hello world")
        self.__sync(FileState.PULL, 1)

    def test_sync_000_conflict_0(self):
        with self.fs.open("mem://remote/test.txt", "wb") as wb:
            wb.write(b"hello world")
        self.__sync(FileState.CONFLICT_MODIFIED, 0)

    def test_sync_000_conflict_1(self):
        with self.fs.open("mem://remote/test.txt", "wb") as wb:
            wb.write(b"hello world")
        self.__sync(FileState.CONFLICT_CREATED, 0)

    def test_sync_000_conflict_2(self):
        with self.fs.open("mem://remote/test.txt", "wb") as wb:
            wb.write(b"hello world")
        self.__sync(FileState.CONFLICT_VERSION, 0)

    def test_sync_000_delete_0(self):
        self.__sync(FileState.DELETE_BOTH, 0)

    def test_sync_000_delete_1(self):
        self.__sync(FileState.DELETE_REMOTE, 0)

    def test_sync_000_delete_2(self):
        with self.fs.open("mem://remote/test.txt", "wb") as wb:
            wb.write(b"hello world")
        self.__sync(FileState.DELETE_LOCAL, 0)

if __name__ == '__main__':
    main_test(sys.argv, globals())

