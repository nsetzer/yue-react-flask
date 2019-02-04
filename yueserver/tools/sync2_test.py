import os
import sys
import logging
import posixpath
import unittest

from base64 import b64encode

from ..dao.db import main_test
from ..dao.filesys.filesys import FileSystem, MemoryFileSystemImpl

from ..app import TestApp
from ..framework.client import FlaskAppClient
from ..framework.application import AppTestClientWrapper

from ..dao.filesys.crypt import HEADER_SIZE

from .sync2 import db_connect, \
    DatabaseTables, LocalStorageDao, SyncContext, DirAttr, FileEnt, \
    _check, RecordBuilder, FileState, _sync_file, _sync_file_impl, \
    _fetch, _sync_file_push, _sync_file_pull, LocalStorageTable, _check_file

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

class TestSyncContext(SyncContext):
    def __init__(self, *args, **kwargs):
        super(TestSyncContext, self).__init__(*args, **kwargs)

    def attr(self, directory):
        return DirAttr({}, {".yue"})

    def getEncryptionServerPassword(self):
        return "password"

    def getEncryptionClientKey(self):
        return b"0" * 32

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

        storageDao = LocalStorageDao(db, db.tables)

        fs = FileSystem()

        ctxt = TestSyncContext(None, storageDao, fs, "mem", "local", "mem://local")

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

    def files_upload(self, root, relpath, rb, mtime=None,
      permission=None, crypt=None, headers=None):

        path = "mem://remote/%s" % (relpath)

        with self.fs.open(path, "wb") as wb:
            # for buf in iter(lambda: rb.read(2048), b""):
            #    wb.write(buf)
            for buf in rb:
                wb.write(buf)
        # todo set perm
        # todo assert version
        self.fs.set_mtime(path, mtime)

        response = lambda: None
        response.status_code = 201
        return response

    def files_get_path(self, root, rel_path, stream=False, headers=None):
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

        storageDao = LocalStorageDao(db, db.tables)

        fs = FileSystem()

        client = TestClient(fs, storageDao)

        ctxt = TestSyncContext(client, storageDao, fs,
            "mem", "", "mem://local")
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

class SyncApplicationTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """
        constructs a shared memory database
        construct a true functioning application client,
        and connect the local context to this client
        """

        cls.app = TestApp(cls.__name__)
        cls.db = cls.app.db
        cls.tables = cls.app.db.tables
        cls.tables.LocalStorageTable = LocalStorageTable(cls.db.metadata)
        cls.tables.LocalStorageTable.create(bind=cls.db.engine)

        cls.remoteStorageDao = cls.app.filesys_service.storageDao
        cls.userDao = cls.app.filesys_service.userDao

        cls.localStorageDao = LocalStorageDao(cls.app.db, cls.app.db.tables)

        cls.fs = cls.app.filesys_service.fs

        # a test_client is a client which supports http methods
        # e.g. .get, .post, etc
        cls.token = 'Basic ' + b64encode(b"admin:admin").decode("utf-8")
        cls.test_client = cls.app.test_client(cls.token)
        # a client supports application methods
        # e.g. .files_upload
        cls.client = FlaskAppClient(cls.test_client,
            cls.app._registered_endpoints)

        cls.ctxt = TestSyncContext(cls.client, cls.localStorageDao, cls.fs,
            "mem", "", "mem://local")

    def setUp(self):
        self.db.delete(self.tables.LocalStorageTable)
        self.db.delete(self.tables.FileSystemStorageTable)
        MemoryFileSystemImpl.clear()

    def test_000_fetch(self):

        # upload a file, outside of the sync application context
        # a fetch will need to be run for the sync application
        # to know about the file
        url = '/api/fs/default/path/test/upload.txt'
        response = self.test_client.post(url, data=b"abc123")
        self.assertEqual(response.status_code, 200, response.status_code)

        # show the file is not found locally
        statement = self.tables.LocalStorageTable.select()
        result = self.db.session.execute(statement)
        self.assertEqual(len(result.fetchall()), 0)

        # fetch, updating the local database
        _fetch(self.ctxt)

        # check that fetch succeeded
        # the local database should be updated to contain the remote file
        statement = self.tables.LocalStorageTable.select()
        result = self.db.session.execute(statement)
        items = result.fetchall()
        self.assertEqual(len(items), 1)

        item = items[0]
        self.assertEqual(item['rel_path'], 'test/upload.txt')

    def test_001_fetch_download(self):

        # upload a file, outside of the sync application context
        # fetch, then pull the file down

        url = '/api/fs/default/path/test/upload.txt'
        response = self.test_client.post(url, data=b"abc123")
        self.assertEqual(response.status_code, 200, response.status_code)

        # show the file is not found locally
        statement = self.tables.LocalStorageTable.select()
        result = self.db.session.execute(statement)
        self.assertEqual(len(result.fetchall()), 0)

        # fetch, updating the local database
        _fetch(self.ctxt)

        ent = _check_file(self.ctxt, 'test/upload.txt',
            'mem://local/test/upload.txt')
        print(ent, ent.af, ent.lf, ent.rf)
        _sync_file_pull(self.ctxt, DirAttr({}, {".yue"}), ent)

        # show the file was downloaded successfully
        self.assertTrue('mem://local/test/upload.txt' in self.fs._mem())

        data = self.fs._mem()['mem://local/test/upload.txt'][0].getvalue()
        self.assertEqual(data, b"abc123")

    def _upload_download(self, attr, encryption_mode):

        # construct a local file in memory, and an entry
        remote_path = 'test/upload.txt'
        local_path = 'mem://local/test/upload.txt'
        af = {'size': 11, 'mtime': 1234567890, 'version': 1, 'permission': 420}
        lf = {'size': 11, 'mtime': 1234567890, 'version': 1, 'permission': 420}
        rf = None
        ent = FileEnt(remote_path, local_path, lf, rf, af)
        original_data = b"hello world"
        with self.fs.open(local_path, "wb") as wb:
            wb.write(original_data)

        # the remote table should be empty
        statement = self.db.tables.FileSystemStorageTable.select()
        result = self.db.session.execute(statement)
        self.assertEqual(len(result.fetchall()), 0)

        # upload the file
        _sync_file_push(self.ctxt, attr, ent)

        # check the remote table
        statement = self.db.tables.FileSystemStorageTable.select()
        result = self.db.session.execute(statement)
        item = result.fetchone()

        # validate the settings are correct
        self.assertEqual(item.size, len(original_data))
        self.assertEqual(item.encryption, encryption_mode)
        self.assertTrue(item.mtime, 1234567890)
        self.assertTrue(item.permission, 420)
        self.assertTrue(item.version, 1)
        with self.fs.open(item.storage_path, 'rb') as rb:
            dat = rb.read()
            if encryption_mode is None:
                self.assertEqual(item.size, len(dat))
                self.assertEqual(dat, original_data)
            else:
                self.assertEqual(HEADER_SIZE + item.size, len(dat))
                self.assertEqual(dat[:4], b'EYUE')

        local_path = 'mem://local/test/download.txt'
        af = None
        lf = None
        rf = {'size': 11, 'mtime': 1234567890, 'version': 1, 'permission': 420}
        ent2 = FileEnt(remote_path, local_path, lf, rf, af)

        _sync_file_pull(self.ctxt, attr, ent2)

        with self.fs.open(local_path, 'rb') as rb:
            dat = rb.read()
            self.assertEqual(original_data, dat)

    def test_002_encrypt_none(self):
        attr = DirAttr({}, {'.yue'})
        self._upload_download(attr, None)

    def test_002_encrypt_system(self):
        attr = DirAttr({'encryption_mode': 'SYSTEM'}, {'.yue'})
        self._upload_download(attr, 'system')

    def test_002_encrypt_server(self):

        url = '/api/fs/change_password'
        response = self.test_client.put(url, data=b"password",
            headers={'X-YUE-PASSWORD': 'password'})
        self.assertEqual(response.status_code, 200, response.status_code)

        attr = DirAttr({'encryption_mode': 'SERVER'}, {'.yue'})
        self._upload_download(attr, 'server')

    def test_002_encrypt_client(self):
        attr = DirAttr({'encryption_mode': 'CLIENT'}, {'.yue'})
        self._upload_download(attr, 'client')

if __name__ == '__main__':
    main_test(sys.argv, globals())

