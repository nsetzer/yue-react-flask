
"""

git inspired sync tool.

todo: create a stat cache to avoid making os calls for the same file

# todo: 500 errors should stop everything
#       400 errors are user errors and should proceed to the next file

add resolve-remote / resolve-local / resolve-fetch commands to fix conflicts
    resolve-fetch to download a specific file as `${filename}.remote`
    provide the opportunity to view the remote file, overwrite local
    and then resolve-local
    possibly sub commands e.g. `sync resolve <action> <action-args>`


add threading model
    for example _sync_impl and _sync_file_impl are replaced by methods
    that append tasks to a queue. the context then has a set of worker threads
    pulling from that queue.
    also create a logging queue / thread to synchronize logging.
    allowing for update logs similar today (instead, number of tasks)
    user_data can have a setting for thread parallel.
    set to num cores by default

neither or these cases are handled by _check:
    remote directory, local file with same name
    local directory, remote file with same name

implement `syn mv`
    - accept two arguments, first is either a file or folder
    - if the first is a folder, second must be a folder and not exist.
    - if first is a folder, second must not exist
      (but can be a folder and the path interpolated)
    - when moving a folder compute the set of changes server side
    - then perform a bulk update

implement `syn rm`
    --local : remove the local file, and db entry, but preserve remote
    --remote : remove the remote file, and db entry, but preserve local

"""
import os, sys
import argparse
import posixpath
import logging
import json
import datetime, time
import getpass
import threading

from fnmatch import fnmatch

import yueserver
from yueserver.tools.upload import S3Upload
from yueserver.dao.search import regexp
from yueserver.app import connect
from yueserver.framework.client import split_auth
from yueserver.framework.crypto import CryptoManager
from yueserver.tools.sync import SyncManager
from yueserver.dao.filesys.filesys import FileSystem
from yueserver.dao.filesys.crypt import cryptkey, decryptkey, recryptkey, \
    validatekey, FileEncryptorReader, FileDecryptorWriter, HEADER_SIZE

from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm.session import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy.schema import Table, Column
from sqlalchemy.types import Integer, String
from sqlalchemy import and_, or_, not_, select, column, \
    update, insert, delete, asc, desc
from sqlalchemy.sql.expression import bindparam

class SyncException(Exception):
    pass

class SyncUserException(SyncException):
    pass

def osname():
    """
    returns an equivalent to 'os.name'

    os.name returns 'nt', 'posix', or 'darwin'.
    under Windows Subsystem for Linux (WSL) it returns 'posix'
    this method will detect WSL and return 'nt' instead

    on nt, file permissions are not fully supported and should default to 644
    """
    name = os.name
    if name == "posix":
        try:
            release = os.uname().release.lower()
        except Exception as e:
            pass
        if 'microsoft' in release:
            name = "nt"
    return name

def get_pass(prompt="password: "):

    if sys.stdin.isatty():
        if os.environ.get('YUE_ECHO_PASSWORD', None):
            return input(prompt)
        else:
            return getpass.getpass(prompt)
    else:
        return sys.stdin.readline().rstrip('\n')

def LocalStorageTable(metadata):
    """
    local_*: the value at the time of the last push pull
             if this differs from reality, the file was changed locally
    remote_*: the value on the remote server

    by comparing the local, remote, and real values it can be determined
    whether a file should be pushed or pulled. if the local version
    is zero, the file has never been pushed
    """
    return Table('filesystem_storage', metadata,
        Column('rel_path', String, primary_key=True, nullable=False),

        Column('local_version', Integer, default=0),
        Column('remote_version', Integer, default=0),
        Column('local_size', Integer, default=0),
        Column('remote_size', Integer, default=0),
        Column('local_permission', Integer, default=0),
        Column('remote_permission', Integer, default=0),
        Column('remote_public', String, default=""),
        Column('remote_encryption', String, default=""),

        Column('local_mtime', Integer, default=0),
        Column('remote_mtime', Integer, default=0)
    )

def DirectoryStatusTable(metadata):
    return Table('directory_status', metadata,
        Column('rel_path', String, primary_key=True, nullable=False),
        Column('valid', Integer, default=0),
        Column('status', String, default=""),
    )

class DatabaseTables(object):
    def __init__(self, metadata):
        super(DatabaseTables, self).__init__()
        self.LocalStorageTable = LocalStorageTable(metadata)
        self.DirectoryStatusTable = DirectoryStatusTable(metadata)

class LocalStorageDao(object):
    def __init__(self, db, dbtables):
        super(LocalStorageDao, self).__init__()
        self.db = db
        self.dbtables = dbtables

    def splitScheme(self, path):
        scheme = "file://localhost/"
        i = path.find("://")
        if "://" in path:
            i += len("://")
            scheme = path[:i]
            path = path[i:]
        return scheme, path

    def insert(self, rel_path, record, commit=True):

        record['rel_path'] = rel_path

        query = self.dbtables.LocalStorageTable.insert() \
            .values(record)

        self.db.session.execute(query)

        if commit:
            self.db.session.commit()

    def update(self, rel_path, record, commit=True):

        query = update(self.dbtables.LocalStorageTable) \
            .values(record) \
            .where(self.dbtables.LocalStorageTable.c.rel_path == rel_path)

        self.db.session.execute(query)

        if commit:
            self.db.session.commit()

    def upsert(self, rel_path, record, commit=True):

        where = self.dbtables.LocalStorageTable.c.rel_path == rel_path
        query = select(['*']) \
            .select_from(self.dbtables.LocalStorageTable) \
            .where(where)
        result = self.db.session.execute(query)
        item = result.fetchone()

        if item is None:
            self.insert(rel_path, record, commit)
            return "insert"
        else:
            self.update(rel_path, record, commit)
            return "update"

    def remove(self, rel_path, commit=True):

        query = delete(self.dbtables.LocalStorageTable) \
            .where(self.dbtables.LocalStorageTable.c.rel_path == rel_path)

        result = self.db.session.execute(query)

        if commit:
            self.db.session.commit()

        return result.rowcount > 0

    def listdir(self, path_prefix="", limit=None, offset=None, delimiter='/'):

        dirs = set()
        files = []

        for item in self.listdir_files(path_prefix, limit, offset, delimiter):
            item = dict(item)
            path = item['rel_path'][len(path_prefix):]

            if delimiter in path:
                name, _ = path.split(delimiter, 1)
                dirs.add(name)
            else:
                item['rel_path'] = path
                files.append(item)

        return dirs, files

    def listdir_files(self, path_prefix="", limit=None, offset=None, delimiter='/'):
        """
        returns all files, including files in subdirectory
        for a given path_prefix
        """

        FsTab = self.dbtables.LocalStorageTable

        if not path_prefix:
            query = select(['*']).select_from(FsTab)
        else:
            if not path_prefix.endswith(delimiter):
                path_prefix += delimiter

            where = FsTab.c.rel_path.startswith(bindparam('path', path_prefix))

            query = select(['*']) \
                .select_from(FsTab) \
                .where(where)

        if limit is not None:
            query = query.limit(limit)

        if offset is not None:
            query = query.offset(offset).order_by(asc(FsTab.c.rel_path))

        return self.db.session.execute(query).fetchall()

    def isDir(self, path):
        """
        return true if a given remote oath represents a directory
            that exists on the remote server
        """
        FsTab = self.dbtables.LocalStorageTable

        if not path:
            return True

        if not path.endswith("/"):
            path += "/"

        where = FsTab.c.rel_path.startswith(bindparam('path', path))

        query = FsTab.select().where(where).limit(1)

        result = self.db.session.execute(query)
        item = result.fetchone()

        return item is not None

    def file_info(self, rel_path):

        FsTab = self.dbtables.LocalStorageTable

        query = select(['*']) \
            .select_from(FsTab) \
            .where(FsTab.c.rel_path == rel_path)

        item = self.db.session.execute(query).fetchone()

        if item is None:
            return None

        item = dict(item)
        # item['rel_path'] = posixpath.split(rel_path)[1]
        return item

    def clearRemote(self, commit=True):
        """ prior to a fetch, all remote files must have the version set to 0
        This will allow the _check method to determine if a remote file
        was deleted. Fetch will update the version for all files that
        exist remotely
        """
        query = update(self.dbtables.LocalStorageTable) \
            .values({"remote_version": 0})

        self.db.session.execute(query)

        if commit:
            self.db.session.commit()

    def markedForDelete(self):
        tab = self.dbtables.LocalStorageTable
        query = tab.select() \
            .where(tab.c.remote_version == 0)
        return self.db.session.execute(query)

class SyncContext(object):

    def __init__(self, client, storageDao, fs, root, remote_base, local_base, verbose=0):
        super(SyncContext, self).__init__()
        self.client = client
        self.storageDao = storageDao
        self.fs = fs
        self.root = root
        self.remote_base = remote_base
        self.local_base = local_base
        self.current_remote_base = remote_base
        self.current_local_base = local_base
        self.verbose = verbose

        self.encryption_server_password = None
        self.encryption_client_key = None

        self.showHiddenNames = False

    def attr(self, directory):
        return DirAttr.openDir(self.local_base, directory)

    def getPassword(self, kind):

        return get_pass("%s password: " % kind)

    def getEncryptionServerPassword(self):
        if self.encryption_server_password is None:
            self.encryption_server_password = self.getPassword('server')
        return self.encryption_server_password

    def getEncryptionClientKey(self):
        # return the key used for client side encryption
        # the key should exist on the remote server if it
        # does not exist locally,
        # fail if the key cannot be found, or if the password
        # is incorrect
        # cache the key for subsequent files
        if self.encryption_client_key is None:
            response = self.client.files_user_key(mode='CLIENT')
            if response.status_code == 404:
                raise SyncUserException("client key not set")
            if response.status_code != 200:
                raise SyncException("Unable to retreive key: %s" %
                    response.status_code)
            key = response.json()['result']['key']

            client_key = None

            for i in range(3):
                try:
                    password = self.getPassword('client')
                    client_key = decryptkey(password, key)
                    break;
                except ValueError:
                    pass

            if client_key is None:
                raise ValueError("invalid password")

            self.encryption_client_key = client_key

        return self.encryption_client_key

    def normPath(self, path):
        """return (abspath, relpath)"""
        return _norm_path(
            self.fs, self.remote_base, self.local_base,
            path)

    def clone(self):

        db = db_connect(self.storageDao.db.url)

        storageDao = LocalStorageDao(db, db.tables)

        ctxt = SyncContext(self.client, storageDao, self.fs,
            self.root, self.remote_base, self.local_base, self.verbose)

        return ctxt

    def close(self):

        self.storageDao.db.conn.close()
        self.storageDao.db.session.close()
        self.storageDao.db.engine.dispose()

    def sameThread(self):
        """
        this object must be cloned() if this returns false
        database can only be accessed from the thread that created the connection
        """
        current_ident = threading.current_thread().ident
        return self.storageDao.db.thread_ident == current_ident

class RecordBuilder(object):
    """docstring for RecordBuilder"""

    def __init__(self, rel_path=None):
        super(RecordBuilder, self).__init__()

        self.rel_path = rel_path

        self.lf = {
            "local_version": 0,
            "local_size": 0,
            "local_mtime": 0,
            "local_permission": 0,
        }

        self.rf = {
            "remote_version": 0,
            "remote_size": 0,
            "remote_mtime": 0,
            "remote_permission": 0,
            "remote_public": None,
            "remote_encryption": None,
        }

    def _update_int(self, obj, key, value):
        if value is not None:
            obj[key] = value

    def _update_null(self, obj, key, value):
        obj[key] = value

    def localFromInfo(self, info):
        return self.local(info.version, info.size, info.mtime, info.permission)

    def local(self, version=None, size=None, mtime=None, permission=None, **kwargs):

        self._update_int(self.lf, "local_version", version)
        self._update_int(self.lf, "local_size", size)
        self._update_int(self.lf, "local_mtime", mtime)
        self._update_int(self.lf, "local_permission", permission)

        return self

    def remoteFromInfo(self, info):
        return self.remote(info.version, info.size, info.mtime, info.permission)

    def remote(self, version=None, size=None, mtime=None, permission=None, **kwargs):

        self._update_int(self.rf, "remote_version", version)
        self._update_int(self.rf, "remote_size", size)
        self._update_int(self.rf, "remote_mtime", mtime)
        self._update_int(self.rf, "remote_permission", permission)
        self._update_null(self.rf, "remote_public", kwargs.get('public', None))
        self._update_null(self.rf, "remote_encryption",
            kwargs.get('encryption', None))

        return self

    def build(self):
        record = {}
        if self.rel_path is not None:
            record['rel_path'] = self.rel_path
        record.update(self.lf)
        record.update(self.rf)
        return record

class FileState(object):
    SAME = "same"
    PUSH = "push"
    PULL = "pull"
    ERROR = "error"
    CONFLICT_MODIFIED = "conflict-modified"
    CONFLICT_CREATED = "conflict-created"
    CONFLICT_VERSION = "conflict-version"
    CONFLICT_TYPE = "conflict-type"
    DELETE_BOTH = "delete-both"
    DELETE_REMOTE = "delete-remote"
    DELETE_LOCAL = "delete-local"
    IGNORE = "ignore"

    @staticmethod
    def symbol_short(state):
        if FileState.SAME == state:
            sym = "--"
        if FileState.PUSH == state:
            sym = "=>"
        if FileState.PULL == state:
            sym = "<="
        if FileState.ERROR == state:
            sym = "ee"
        if FileState.CONFLICT_MODIFIED == state:
            sym = "mm"
        if FileState.CONFLICT_CREATED == state:
            sym = "cc"
        if FileState.CONFLICT_VERSION == state:
            sym = "vv"
        if FileState.CONFLICT_TYPE == state:
            sym = "tt"
        if FileState.DELETE_BOTH == state:
            sym = "xx"
        if FileState.DELETE_REMOTE == state:
            sym = "-x"
        if FileState.DELETE_LOCAL == state:
            sym = "x-"
        if FileState.IGNORE == state:
            sym = "??"
        return sym

    @staticmethod
    def symbol_verbose(state):
        if FileState.SAME == state:
            sym = "SAME"
        if FileState.PUSH == state:
            sym = "PUSH"
        if FileState.PULL == state:
            sym = "PULL"
        if FileState.ERROR == state:
            sym = "ERR_"
        if FileState.CONFLICT_MODIFIED == state:
            sym = "CMOD"
        if FileState.CONFLICT_CREATED == state:
            sym = "CCRE"
        if FileState.CONFLICT_VERSION == state:
            sym = "CVER"
        if FileState.CONFLICT_TYPE == state:
            sym = "CTYP"
        if FileState.DELETE_BOTH == state:
            sym = "DEL_"
        if FileState.DELETE_REMOTE == state:
            sym = "DREM"
        if FileState.DELETE_LOCAL == state:
            sym = "DLOC"
        if FileState.IGNORE == state:
            sym = "IGN_"
        return sym

    @staticmethod
    def symbol(state, verbose=False):
        if verbose:
            return FileState.symbol_verbose(state)
        return FileState.symbol_short(state)

    @staticmethod
    def states():
        return [
            FileState.SAME,
            FileState.PUSH,
            FileState.PULL,
            FileState.ERROR,
            FileState.CONFLICT_MODIFIED,
            FileState.CONFLICT_CREATED,
            FileState.CONFLICT_VERSION,
            FileState.CONFLICT_TYPE,
            FileState.DELETE_BOTH,
            FileState.DELETE_REMOTE,
            FileState.DELETE_LOCAL,
            FileState.IGNORE,
        ]

class DirEnt(object):
    """docstring for DirEnt"""

    def __init__(self, name, remote_base, local_base, state=None):
        super(DirEnt, self).__init__()
        self.remote_base = remote_base
        self.local_base = local_base
        self._name = name
        self._state = state or FileState.ERROR
        self._permission = 0
        self._mtime = 0

    def state(self):
        # if self.remote_base is None and self.local_base is None:
        #    return FileState.ERROR
        # elif self.remote_base is None and self.local_base is not None:
        #    return FileState.PUSH
        # elif self.remote_base is not None and self.local_base is None:
        #    return FileState.PULL
        # elif self.remote_base is not None and self.local_base is not None:
        #    return FileState.SAME
        return self._state

    def name(self):
        return self._name

    def __str__(self):
        return "<DirEnt(%s,%s,%s)>" % (
            self.remote_base, self.local_base, self._state)

    def __repr__(self):
        return "<DirEnt(%s,%s,%s)>" % (
            self.remote_base, self.local_base, self._state)

    def local_url(self):
        # deprecated
        # TODO: remove this

        if self.local_base:
            if osname() == 'nt':
                return "file:///%s" % self.local_base
            else:
                return "file://%s" % self.local_base
        return None

class FileEnt(object):
    def __init__(self, remote_path, local_path, lf, rf, af):
        super(FileEnt, self).__init__()
        self.remote_path = remote_path
        self.local_path = local_path

        self.lf = lf
        self.rf = rf
        self.af = af

        self._state = None

        self.state()  # set af version

    def __str__(self):
        return "FileEnt<%s,%s>" % (self.remote_path, self.local_path)

    def __repr__(self):
        return "FileEnt<%s,%s>" % (self.remote_path, self.local_path)

    def name(self):
        if self.remote_path is not None:
            return posixpath.split(self.remote_path)[1]
        else:
            return os.path.split(self.local_path)[1]

    def _samefile(self, af, bf):
        b = af['mtime'] == bf['mtime'] and af['size'] == bf['size']
        # todo: not all file systems implement permissions...
        #  af['permission'] == bf['permission']
        return b

    def _check_threeway_compare(self):
        # given three data-dicts representing a file
        # for local, remote, and actual state
        # determines whether the file should be pushed or pulled to sync

        if self.lf['version'] < self.rf['version']:
            if self._samefile(self.lf, self.af):
                return FileState.PULL + ":3a"
            else:
                return FileState.CONFLICT_MODIFIED + ":3a"
        elif self.lf['version'] > self.rf['version']:
            return FileState.CONFLICT_VERSION + ":3a"
        else:
            if self._samefile(self.lf, self.af):
                # file has not been changed locally
                if self._samefile(self.lf, self.rf):
                    # file has not been changed on remote
                    return FileState.SAME + ":3a"
                else:
                    # locally is the same but remote is different
                    # this is a weird state
                    return FileState.CONFLICT_VERSION + ":3b"
            else:
                # file has changed locally
                if self._samefile(self.lf, self.rf):
                    # local is newer
                    self.af['version'] = self.lf['version'] + 1
                    return FileState.PUSH + ":3a"
                else:
                    # both modified
                    return FileState.CONFLICT_MODIFIED + ":3b"

            return FileState.ERROR + ":3b"

    def _get_state(self):

        # this assumes that fetch properly updates the database
        # fetch needs to clear the remote version for files that are
        # found locally but not returned from the api call

        # | N | _LF_ | _RF_ | _AF_
        # | 0 | none | none | none | error
        # | 1 | none | none | true | push
        # | 2 | none | true | none | pull
        # | 3 | none | true | true | conflict : created both
        # | 4 | true | none | none | delete both remotely and locally (run gc)
        # | 5 | true | none | true | deleted remote
        # | 6 | true | true | none | deleted locally
        # | 7 | true | true | true | compare metadata and decide

        lfnull = self.lf is None
        rfnull = self.rf is None
        afnull = self.af is None

        lfe = self.lf is not None
        rfe = self.rf is not None
        afe = self.af is not None

        if afe and lfe:
            self.af['version'] = self.lf['version']

        # 0: error
        # Note: one way to get into the error state is to:
        #  in ctxt A: push files to remote
        #  in ctxt B: fetch
        #  in ctxt A: delete those files
        #  in ctxt B: fetch
        # ctxt B now has files with local version = 0
        # that also do no exist on remote or locally
        if lfnull and rfnull and afnull:
            return FileState.ERROR

        # 1 : push
        elif lfnull and rfnull and afe:
            self.af['version'] = 1
            return FileState.PUSH + ":1"

        # 2 : pull
        elif lfnull and rfe and afnull:
            return FileState.PULL + ":1"

        # 3 : conflict
        elif lfnull and rfe and afe:
            return FileState.CONFLICT_CREATED + ":1"

        # 4 : collect garbage
        elif lfe and rfnull and afnull:
            return FileState.DELETE_BOTH + ":1"

        # 5 : delete remote
        elif lfe and rfnull and afe:
            return FileState.DELETE_REMOTE + ":1"

        # 6 : delete local
        elif lfe and rfe and afnull:
            return FileState.DELETE_LOCAL + ":1"

        # 7 : file exists both
        elif lfe and rfe and afe:
            return self._check_threeway_compare()

        return FileState.ERROR

    def state(self):
        if not self._state:
            self._state = self._get_state()
        return self._state

    def data(self):
        lv = ("%2d" % self.lf.get('version', 0)) if self.lf else "--"
        rv = ("%2d" % self.rf.get('version', 0)) if self.rf else "--"
        av = ("%2d" % self.af.get('version', 0)) if self.af else "--"

        lm = ("%10d" % self.lf.get('mtime', 0)) if self.lf else ("-" * 10)
        rm = ("%10d" % self.rf.get('mtime', 0)) if self.rf else ("-" * 10)
        am = ("%10d" % self.af.get('mtime', 0)) if self.af else ("-" * 10)

        _ls = ("%10d" % self.lf.get('size', 0)) if self.lf else ("-" * 10)
        _rs = ("%10d" % self.rf.get('size', 0)) if self.rf else ("-" * 10)
        _as = ("%10d" % self.af.get('size', 0)) if self.af else ("-" * 10)

        lp = ("%5s" % oct(self.lf.get('permission', 0))) if self.lf else ("-" * 5)
        rp = ("%5s" % oct(self.rf.get('permission', 0))) if self.rf else ("-" * 5)
        ap = ("%5s" % oct(self.af.get('permission', 0))) if self.af else ("-" * 5)

        if self.rf:
            public = self.rf.get('public', None) or ""
        else:
            public = ""

        triple = [
            ("L", "R", "A"),
            (lv, rv, av),
            (lm, rm, am),
            (_ls, _rs, _as),
            (lp, rp, ap),
        ]
        return "/".join(["%s,%s,%s" % t for t in triple]) + ' ' + public

    def stat(self):
        """
        return stat information for this entry

        format:
            version size permission mtime encryption

        version: version number of the local file
        size: local file size
        permission: octal representation of the version
        mtime: last modified time
        encryption: 6 character representation of encryption scheme

        """

        st_lv = ("%4d" % self.lf.get('version', 0)) if self.lf else "----"
        #st_am = ("%11d" % self.af.get('mtime', 0)) if self.af else ("-"*11)
        mtime = self.af.get('mtime', 0) if self.af else 0
        if mtime > 0:
            st_am = time.strftime('%y-%m-%d %H:%M:%S', time.localtime(mtime))
        else:
            st_am = "-" * 17
        st_ap = ("%5s" % oct(self.af.get('permission', 0))) if self.af else ("-" * 5)
        st_as = ("%12d" % self.af.get('size', 0)) if self.af else ("-" * 12)

        if self.rf:
            enc = self.rf.get("encryption", None)
            if not enc:
                enc = "------"
            if len(enc) < 6:
                enc += '-' * (6 - len(enc))
            if len(enc) > 6:
                enc = enc[:6]
            enc = enc.lower()
        else:
            enc = "------"

        return "%s %s %s %s %s" % (st_lv, st_as, st_ap[2:], st_am, enc)

    def local_directory(self):
        return os.path.split(self.local_path)[0]

    def local_url(self):
        if self.local_base:
            if osname() == 'nt':
                return "file:///%s" % self.local_base
            else:
                return "file://%s" % self.local_base
        return None

class DirAttr(object):
    """collection of meta directory attributes

    Directories have a set of attributes, found in a .yueattr file.
    Attributes control syncing behavior of files found in the directory
    Attributes are automatically inherited by child directories

    'encryption_mode': none, client, server, system
        the encryption mode to apply to files that are uploaded
        in this directory and child directories

    'public': Not implemented
        intended to automatically make files public on push
    """
    _cache = dict()

    def __init__(self, settings, patterns):
        """
        settings: map str => str. a collection of settings for this
            directory. that are automatically inherited by children
        patterns: set str. a collection of unix-style glob patterns
            used to blacklist certain files by name
        """
        super(DirAttr, self).__init__()
        self.blacklist_patterns = set()
        self.settings = {
            "encryption_mode": 'none',
            "public": False,
        }
        self._init(settings, patterns)

        # keep a reference to original values
        self._settings = settings
        self._patterns = patterns

    def _init(self, settings, patterns):
        _bool = lambda n: settings[n].lower() == "true"
        _mode1 = lambda n: settings[n].lower()

        for keyname in settings:
            if keyname == 'encryption_mode':
                self.settings['encryption_mode'] = _mode1('encryption_mode')
                modes = {'none', 'client', 'server', 'system'}
                if self.settings['encryption_mode'] not in modes:
                    raise SyncException(
                        "invalid encryption mode: %s" %
                        self.settings['encryption_mode'])

            elif keyname == 'public':
                self.settings['public'] = _bool('public')

            else:
                raise SyncException("unkown setting: %s" % keyname)

        self.blacklist_patterns = self.blacklist_patterns | patterns

    def encryptionMode(self):
        return self.settings['encryption_mode']

    def doGeneratePublicPath(self):
        return self.generate_public

    def match(self, name):
        """ return true if the file should be excluded from status/upload """
        for pattern in self.blacklist_patterns:
            if fnmatch(name, pattern):
                return True
        return False

    def update(self, settings, patterns):
        """return a new DirAttr representing an immediate descendant"""

        # clone this object
        attr = DirAttr({}, self.blacklist_patterns)
        attr.settings = dict(self.settings)

        # apply the new configuration
        attr._init(settings, patterns)
        attr._settings = settings
        attr._patterns = patterns

        return attr

    @staticmethod
    def openDir(local_root, directory):
        """open """

        directory = directory.rstrip('/')

        if not os.path.isabs(directory):
            directory = os.path.join(local_root, directory)

        # return the cached version
        if directory in DirAttr._cache:
            return DirAttr._cache[directory]

        # open attr file, update the parent directory
        attr_file = os.path.join(directory, ".yueattr")
        settings, patterns = DirAttr.openAttrFile(attr_file)

        # TODO: this check seems to be error prone
        # but os.path.samefile uses os.stat
        if local_root == directory or directory == "":
            # construct the root attr
            patterns = patterns | {'.yue'}
            attr = DirAttr(settings, patterns)
        else:
            parent, name = os.path.split(directory)
            if parent == directory:
                raise SyncException(parent)
            attr = DirAttr.openDir(local_root, parent)
            attr = attr.update(settings, patterns)

        # cache for later
        DirAttr._cache[directory] = attr

        return attr

    @staticmethod
    def openAttrFile(attr_file):
        settings = {}
        patterns = set()

        if os.path.exists(attr_file):

            with open(attr_file, "r") as rf:
                mode = 0
                for line in rf:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if line == '[settings]':
                        mode = 1
                    elif line == '[blacklist]':
                        mode = 0
                    elif mode == 0:
                        patterns.add(line)
                    elif mode == 1:
                        key, val = line.split('=', 1)
                        settings[key] = val
        return settings, patterns

class CheckResult(object):
    def __init__(self, remote_base, local_base, dirs, files):
        super(CheckResult, self).__init__()
        self.remote_base = remote_base
        self.local_base = local_base
        self.dirs = dirs
        self.files = files

    def __str__(self):
        return "CheckResult<%s,%d,%d>" % (self.remote_base, len(self.dirs), len(self.files))

    def __repr__(self):
        return "CheckResult<%s, %d,%d>" % (self.remote_base, len(self.dirs), len(self.files))

class ProgressFileReaderWrapper(object):
    def __init__(self, fs, path, remote_path, key=None):
        super(ProgressFileReaderWrapper, self).__init__()
        self.fs = fs
        self.path = path
        self.remote_path = remote_path
        self.info = self.fs.file_info(path)
        self.bytes_read = 0
        self.key = key
        self._read = False
        self._size = self.info.size
        if self.key is not None:
            self._size += HEADER_SIZE

    def __iter__(self):

        with self.fs.open(self.path, 'rb') as rb:

            if self.key is not None:
                # support for client encryption upload
                rb = FileEncryptorReader(rb, self.key)

            for i, chunk in enumerate(iter(lambda: rb.read(2048), b"")):
                yield chunk
                self.bytes_read += len(chunk)
                # percent = 100 * self.bytes_read / self.info.size
                # send an update approximately every quarter MB
                if i % 256 == 0:
                    sys.stderr.write("\r%10d/%10d - %s  " % (
                        self.bytes_read, self._size, self.remote_path))
            sys.stderr.write("\r%10d - %s             \n" % (
                self.bytes_read, self.remote_path))

    def __len__(self):
        # two strange bugs
        # if not implemented requests will read the whole file
        # to determine the size before sending
        # if the value reported is incorrect, then requests
        # will send all bytes, or the size reported, which ever is lower
        return self._size

class ProgressStreamReaderWrapper(object):
    def __init__(self, stream, remote_path, size):
        super(ProgressStreamReaderWrapper, self).__init__()
        self.stream = stream
        self.remote_path = remote_path
        self.size = size if size > 0 else 1
        self.bytes_read = 0
        self.percent = -1

    def __iter__(self):

        for chunk in self.stream:
            self.bytes_read += len(chunk)

            yield chunk

            # integer here controls the maximum number of updates
            percent = int(4 * self.bytes_read / self.size)
            if percent != self.percent:
                self.percent = percent
                sys.stderr.write("\r%10d/%10d - %s  " % (
                    self.bytes_read, self.size, self.remote_path))

        sys.stderr.write("\r%10d - %s             \n" % (
            self.bytes_read, self.remote_path))

def db_connect(connection_string):

    if connection_string is None or connection_string == ":memory:":
        connection_string = 'sqlite://'

    engine = create_engine(connection_string)
    Session = scoped_session(sessionmaker(bind=engine))

    db = lambda: None
    db.engine = engine
    db.metadata = MetaData()
    db.session = Session
    db.tables = DatabaseTables(db.metadata)
    db.connection_string = connection_string
    db.kind = lambda: connection_string.split(":")[0]
    db.conn = db.session.bind.connect()
    db.conn.connection.create_function('REGEXP', 2, regexp)
    db.create_all = lambda: db.metadata.create_all(engine)
    db.delete = lambda table: db.session.execute(delete(table))
    db.url = connection_string
    db.thread_ident = threading.current_thread().ident

    path = connection_string[len("sqlite:///"):]
    if path and not os.access(path, os.W_OK):
        logging.warning("database at %s not writable" % connection_string)

    return db

def get_cfg(directory):

    cwd = directory

    relpath = ""  # the relative path / remote base

    names = os.listdir(directory)
    while '.yue' not in names:
        temp, t = os.path.split(directory)
        if relpath:
            relpath = t + "/" + relpath
        else:
            relpath = t
        if temp == directory:
            break
        directory = temp
        names = os.listdir(directory)

    cfgdir = os.path.join(directory, '.yue')
    if not os.path.exists(cfgdir):
        raise SyncException("not found: %s" % cfgdir)

    pemkey_path = os.path.join(cfgdir, 'rsa.pem')
    with open(pemkey_path, "rb") as rb:
        pemkey = rb.read()

    userdata_path = os.path.join(cfgdir, 'userdata.json')
    with open(userdata_path, "r") as rf:
        userdata = json.load(rf)

    cm = CryptoManager()
    userdata['password'] = cm.decrypt64(pemkey,
        userdata['password']).decode("utf-8")

    userdata['cfgdir'] = cfgdir
    userdata['local_base'] = directory
    userdata['current_local_base'] = cwd
    userdata['current_remote_base'] = posixpath.join(userdata['remote_base'], relpath)
    return userdata

def get_ctxt(directory):

    userdata = get_cfg(os.getcwd())

    db = db_connect(userdata['dburl'])

    client = connect(userdata['hostname'],
        userdata['username'], userdata['password'])

    storageDao = LocalStorageDao(db, db.tables)

    fs = FileSystem()

    ctxt = SyncContext(client, storageDao, fs,
        userdata['root'], userdata['remote_base'], userdata['local_base'])

    ctxt.current_local_base = userdata['current_local_base']
    ctxt.current_remote_base = userdata['current_remote_base']

    return ctxt

def _fetch_iter(ctxt):

    # TODO: fetch can be sped up by increasing the limit
    #       possibly use a dynamic limit to keep request time
    #       under 5 seconds
    page = 0
    limit = 500

    try:
        ctxt.storageDao.clearRemote(False)

        while True:
            params = {'limit': limit, 'page': page}
            try:
                response = ctxt.client.files_get_index(
                    ctxt.root, ctxt.remote_base, **params)
            except Exception as e:
                logging.error("unable to fetch: %s" % e)
                break

            if response.status_code != 200:
                sys.stderr.write("fetch error [%d] %s" % (
                    response.status_code, response.text))
                break

            try:
                files = response.json()['result']
            except Exception as e:
                logging.exception(response.text)
                raise e

            for f in files:
                record = {
                    "remote_size": f['size'],
                    "remote_mtime": f['mtime'],
                    "remote_permission": f['permission'],
                    "remote_version": f['version'],
                    "remote_public": f['public'],
                    "remote_encryption": f['encryption'],
                }

                # support partial checkouts
                if ctxt.remote_base:
                    f['path'] = ctxt.fs.join(ctxt.remote_base, f['path'])

                mode = ctxt.storageDao.upsert(f['path'], record, commit=False)

                # important: yield at a point in time when
                # not calling next on the generator would not
                # case data loss

                yield (f['path'], record, mode)

                # indicate there are new files to pull
                if mode == 'insert':
                    sys.stdout.write("+ %s\n" % f['path'])

            page += 1
            if len(files) != limit:
                break

        # indicate that there are files to delete on pull
        for item in ctxt.storageDao.markedForDelete():
            yield (item['rel_path'], None, delete)
            sys.stdout.write("- %s\n" % item['rel_path'])

    except Exception as e:
        logging.exception(e)
        ctxt.storageDao.db.session.rollback()
    else:
        ctxt.storageDao.db.session.commit()

def _fetch(ctxt):

    for _ in _fetch_iter(ctxt):
        pass

def _check(ctxt, remote_base, local_base):
    if remote_base and not remote_base.endswith("/"):
        remote_base += "/"

    if '\\' in remote_base:
        print("warning: %s" % remote_base)

    attr = ctxt.attr(local_base)

    dirs = []
    files = []
    _dirs, _files = ctxt.storageDao.listdir(remote_base)

    # TODO: looks like memfs impl for exists is broken for dirs
    try:
        if not ctxt.fs.islocal(local_base) or ctxt.fs.exists(local_base):
            _records = set(ctxt.fs.scandir(local_base))
        else:
            _records = set()
    except NotADirectoryError:
        _records = set()

    _names = {r.name: r for r in _records}

    for d in _dirs:

        remote_path = posixpath.join(remote_base, d)
        local_path = ctxt.fs.join(local_base, d)
        # check that the directory exists locally

        permission = 0
        mtime = 0

        if d in _names:
            permission = _names[d].permission
            mtime = _names[d].mtime

        if attr.match(d):
            if ctxt.showHiddenNames:
                state = FileState.IGNORE
            else:
                continue
        elif d in _names:

            if _names[d].isDir:
                state = FileState.SAME
            else:
                state = FileState.CONFLICT_TYPE

            del _names[d]
        else:
            state = FileState.PULL

        ent = DirEnt(d, remote_path, local_path, state)
        ent._permission = permission
        ent._mtime = mtime
        dirs.append(ent)

    for f in _files:
        name = f['rel_path']
        remote_path = posixpath.join(remote_base, f['rel_path'])
        local_path = ctxt.fs.join(local_base, f['rel_path'])

        if name in _names:
            if _names[name].isDir:
                state = FileState.CONFLICT_TYPE
                dirs.append(DirEnt(name, remote_path, local_path, state))
                del _names[name]
                continue
            else:
                del _names[name]

        # local (Cached) database info
        if f['local_version'] == 0:
            lf = None
        else:
            lf = {
                "version": f['local_version'],
                "size": f['local_size'],
                "mtime": f['local_mtime'],
                "permission": f['local_permission'],
            }

        # remote database info
        if f['remote_version'] == 0:
            rf = None
        else:
            rf = {
                "version": f['remote_version'],
                "size": f['remote_size'],
                "mtime": f['remote_mtime'],
                "permission": f['remote_permission'],
                "public": f['remote_public'],
                "encryption": f['remote_encryption'],
            }

        # local (Actual) file info
        try:
            record = ctxt.fs.file_info(local_path)

            af = {
                "version": record.version,
                "size": record.size,
                "mtime": record.mtime,
                "permission": record.permission,
            }
        except FileNotFoundError:
            af = None
        except NotADirectoryError:
            af = None

        files.append(FileEnt(remote_path, local_path, lf, rf, af))

    for n in _names:
        remote_path = posixpath.join(remote_base, n)
        local_path = ctxt.fs.join(local_base, n)
        record = ctxt.fs.file_info(local_path)

        state = None

        if attr.match(n):
            if ctxt.showHiddenNames:
                state = FileState.IGNORE
            else:
                continue
        else:
            state = FileState.PUSH

        if record.isDir:
            ent = DirEnt(n, remote_path, local_path, state)
            ent._permission = _names[n].permission
            ent._mtime = _names[n].mtime
            dirs.append(ent)
        else:
            af = {
                "version": record.version,
                "size": record.size,
                "mtime": record.mtime,
                "permission": record.permission,
            }
            ent = FileEnt(remote_path, local_path, None, None, af)
            ent._state = state
            files.append(ent)

    return CheckResult(remote_base, local_base, dirs, files)

def _check_file(ctxt, remote_path, local_path):
    """
    returns a FileEnt for a given path

    remote_path: the relative path on the remote file system
    local_path: the absolute path on the local file system

    the returned FileEnt will indicate the state of the file,
    whether it exists, in the local database, or remotely.

    """

    item = ctxt.storageDao.file_info(remote_path)

    try:
        record = ctxt.fs.file_info(local_path)

        af = {
            "version": record.version,
            "size": record.size,
            "mtime": record.mtime,
            "permission": record.permission,
        }
    except OSError:
        af = None
    except FileNotFoundError:
        af = None

    if item is not None:

        if item['local_version'] == 0:
            lf = None
        else:

            lf = {
                "version": item['local_version'],
                "size": item['local_size'],
                "mtime": item['local_mtime'],
                "permission": item['local_permission'],
            }

        if item['remote_version'] == 0:
            rf = None
        else:
            rf = {
                "version": item['remote_version'],
                "size": item['remote_size'],
                "mtime": item['remote_mtime'],
                "permission": item['remote_permission'],
                "public": item['remote_public'],
                "encryption": item['remote_encryption'],
            }

        ent = FileEnt(remote_path, local_path, lf, rf, af)
    else:
        # TODO: I could add extra context information,
        # since this is causes a CONFLICT_TYPE state
        # when the remote contains a directory named the same
        # as a local file
        if ctxt.storageDao.isDir(remote_path):
            af = None
        ent = FileEnt(remote_path, local_path, None, None, af)

    return ent

def _check_recursive_impl(ctxt, remote_dir, local_dir, recursive):

    result = _check(ctxt, remote_dir, local_dir)

    results = [result]

    while len(results) > 0:
        result = results.pop(0)

        for ent in result.dirs:
            yield ent

            if recursive:
                rbase = posixpath.join(result.remote_base, ent.name())
                lbase = ctxt.fs.join(result.local_base, ent.name())
                results.append(_check(ctxt, rbase, lbase))

        for ent in result.files:
            yield ent

def _norm_path(fs, remote_base, local_base, path):

    if not os.path.isabs(path):
        abspath = os.path.normpath(os.path.join(os.getcwd(), path))
    else:
        abspath = path

    if not abspath.startswith(local_base):
        raise FileNotFoundError("path spec does not match")

    relpath = os.path.relpath(path, local_base)
    if relpath == ".":
        relpath = ""

    if osname() == 'nt':
        relpath = relpath.replace("\\", "/")
    relpath = posixpath.join(remote_base, relpath)

    return abspath, relpath

def _parse_path_args(fs, remote_base, local_base, args_paths):
    """
    returns a collection of DirEnt {name, relpath, abspath}
    """
    paths = []

    for path in args_paths:
        # if not fs.exists(path):
        #    raise FileNotFoundError(path)
        abspath, relpath = _norm_path(fs, remote_base, local_base, path)
        name = fs.split(abspath)[1]
        paths.append(DirEnt(name, relpath, abspath))

    paths.sort(key=lambda x: x.local_base)

    return paths

###############################################################################
# CLI implementations

def _status_dir_impl(ctxt, remote_dir, local_dir, recursive):

    """
    for ent in _check_recursive_impl(ctxt, remote_dir, local_dir, recursive):

        if isinstance(ent, DirEnt):
            _status_directory_impl(ctxt, ent)
        else:
            _status_file_impl(ctxt, ent)
    """

    result = _check(ctxt, remote_dir, local_dir)

    ents = list(result.dirs) + list(result.files)

    for ent in sorted(ents, key=lambda x: x.name()):

        if isinstance(ent, DirEnt):

            _status_directory_impl(ctxt, ent)

            if recursive:
                rbase = posixpath.join(remote_dir, ent.name())
                lbase = ctxt.fs.join(local_dir, ent.name())
                _status_dir_impl(ctxt, rbase, lbase, recursive)
        else:
            _status_file_impl(ctxt, ent)

def _status_directory_impl(ctxt, ent):
    state = ent.state()

    if not (state == FileState.SAME and ctxt.verbose == 0):

        sym = FileState.symbol(state, ctxt.verbose > 2)
        path = ctxt.fs.relpath(ent.local_base, ctxt.current_local_base)

        if ctxt.verbose > 1:
            sys.stdout.write("d%s %s %s/\n" % (sym, " " * 46, path))
        else:
            sys.stdout.write("d%s %s/\n" % (sym, path))

def _status_file_impl(ctxt, ent):
    state = ent.state().split(':')[0]
    if state == FileState.SAME and ctxt.verbose == 0:
        return
    sym = FileState.symbol(state, ctxt.verbose > 2)
    path = ctxt.fs.relpath(ent.local_path, ctxt.current_local_base)
    if ctxt.verbose > 1:
        sys.stdout.write("f%s %s %s\n" % (sym, ent.stat(), path))
    else:
        sys.stdout.write("f%s %s\n" % (sym, path))
    # in testing, it can be useful to see lf/rf/af state
    if ctxt.verbose > 3:
        sys.stdout.write("%s\n" % ent.data())

class SyncResult(object):
    def __init__(self, ent, state, message):
        super(SyncResult, self).__init__()
        self.ent = ent
        self.state = state
        self.message = message

def _sync_file_push(ctxt, attr, ent):

    # next version is 1 + current version

    # todo:
    #    server should reject if the version is less than expected
    #    server response should include new version
    #    force flag to disable server side version check
    #    if only perm_ changed, send a metadata update instead

    versions = []
    for df in [ent.lf, ent.rf, ent.af]:
        if ent.lf:
            versions.append(ent.lf['version'])
        else:
            versions.append(0)

    version = ent.af['version']

    mtime = ent.af['mtime']
    perm_ = ent.af['permission']

    key = None
    crypt = None
    headers = {}

    if attr.encryptionMode().lower() == 'client':
        crypt = 'client'
        key = ctxt.getEncryptionClientKey()

    elif attr.encryptionMode().lower() == 'server':
        crypt = 'server'
        headers = {'X-YUE-PASSWORD': ctxt.getEncryptionServerPassword()}

    elif attr.encryptionMode().lower() == 'system':
        crypt = 'system'

    f = ProgressFileReaderWrapper(
        ctxt.fs, ent.local_path, ent.remote_path, key)
    #f = ctxt.fs.open(ent.local_path, 'rb')

    # if public attr set, subsequent call to set a public path if not set
    # public password attr should be be an encrypted string

    # TODO: send version, use response to update parameters from remote
    response = ctxt.client.files_upload(ctxt.root, ent.remote_path, f,
        mtime=mtime, version=version, permission=perm_, crypt=crypt, headers=headers)

    if response.status_code == 409:
        msg = "local database out of date. fetch first"
        msg += "\n%s" % response.text
        msg += "\n%s" % ent.local_path
        msg += "\n%s" % ent.remote_path
        msg += "\n%s" % versions
        raise SyncUserException(msg)

    if response.status_code != 200 and response.status_code != 201:
        raise SyncException("unexpected error: %s" % response.status_code)

    data =  response.json()

    ent.af['version'] = data['file_info']['version']

    record = RecordBuilder().local(**ent.af).remote(**ent.af).build()
    record['remote_encryption'] = crypt
    ctxt.storageDao.upsert(ent.remote_path, record)

def _sync_file_pull(ctxt, attr, ent):
    # todo:
    #   server should return metadata (perm, version) in headers
    #          X-YUE-PERMISSION
    #          X-YUE-VERSION
    #   if the version does not match rf, fail with an error indicating
    #       the user must fetch first
    #   the current version on the server. (user must fetch first)
    #   if only a perm_ change, request metadata instead of file
    #   response headers should contain meta data about the file
    #     - size, mtime, perm

    version = ent.rf['version']

    headers = {}

    encryption_mode = ent.rf['encryption']
    if encryption_mode:
        encryption_mode = encryption_mode.lower()

    if encryption_mode == 'server':
        headers = {'X-YUE-PASSWORD': ctxt.getEncryptionServerPassword()}

    elif encryption_mode == 'system':
        pass

    response = ctxt.client.files_get_path(ctxt.root, ent.remote_path,
        stream=True, headers=headers)

    if response.status_code != 200:
        logging.error("error %d for file %s/%s" % (
            response.status_code, ctxt.root, ent.remote_path))

        raise SyncException("error %d for file %s/%s" % (
            response.status_code, ctxt.root, ent.remote_path))

    rv = int(response.headers.get('X-YUE-VERSION', "0"))
    rp = int(response.headers.get('X-YUE-PERMISSION', "0"))
    rm = int(response.headers.get('X-YUE-MTIME', "0"))

    if ent.rf['version'] != rv or \
       ent.rf['permission'] != rp or \
       ent.rf['mtime'] != rm:
        logging.error("error fetching metadata for %s/%s" % (
            ctxt.root, ent.remote_path))
        raise SyncException("local database out of date. fetch first")

    dpath = ctxt.fs.split(ent.local_path)[0]
    if not ctxt.fs.exists(dpath):
        ctxt.fs.makedirs(dpath)

    bytes_written = 0
    try:
        with ctxt.fs.open(ent.local_path, "wb") as wb:

            if encryption_mode == 'client':
                key = ctxt.getEncryptionClientKey()
                wb = FileDecryptorWriter(wb, key)

            stream = ProgressStreamReaderWrapper(response.stream(),
                ent.remote_path, ent.rf['size'])

            for chunk in stream:
                bytes_written += len(chunk)
                wb.write(chunk)
    except NotADirectoryError:
        sys.stderr.write("conflict: not a directory: %s\n" % ent.remote_path)
        return

    ctxt.fs.set_mtime(ent.local_path, ent.rf['mtime'])
    record = RecordBuilder().local(**ent.rf).remote(**ent.rf).build()
    ctxt.storageDao.update(ent.remote_path, record)

def _sync_file_impl(ctxt, ent, push=False, pull=False, force=False):

    state = ent.state().split(':')[0]

    attr = ctxt.attr(ent.local_directory())

    message = None

    if attr.match(ent.name()):
        if not force:
            return SyncResult(ent, state, "force not enabled")

    if FileState.SAME == state:
        pass
    elif FileState.IGNORE == state:
        pass

    elif (FileState.PULL == state and push and not pull and not force):
        # remote changes to the file will be overwritten
        # ask the user to confirm they want to override
        sys.stdout.write("use force to push %s\n" % ent.remote_path)

    elif (FileState.PUSH == state and push) or \
         (FileState.PULL == state and push and force) or \
         (FileState.DELETE_REMOTE == state and not pull and push) or \
         (FileState.CONFLICT_MODIFIED == state and not pull and push) or \
         (FileState.CONFLICT_CREATED == state and not pull and push) or \
         (FileState.CONFLICT_VERSION == state and not pull and push):

        if FileState.PUSH != state and not force:
            message = "%s is in a conflict state.\n" % ent.remote_path
            sys.stdout.write(message)

        _sync_file_push(ctxt, attr, ent)

    elif (FileState.PUSH == state and pull and not push and not force):
        # local changes to the file will be overwritten
        # ask the user to confirm they want to override
        sys.stdout.write("use force to pull %s\n" % ent.remote_path)

    elif (FileState.PULL == state and pull) or \
         (FileState.PUSH == state and pull and force) or \
         (FileState.DELETE_LOCAL == state and pull and not push) or \
         (FileState.CONFLICT_MODIFIED == state and pull and not push) or \
         (FileState.CONFLICT_CREATED == state and pull and not push) or \
         (FileState.CONFLICT_VERSION == state and pull and not push):

        if FileState.PULL != state and not force:
            message = "%s is in a conflict state.\n" % ent.remote_path
            sys.stdout.write(message)

        _sync_file_pull(ctxt, attr, ent)

    elif FileState.ERROR == state:
        message = "delete error %s\n" % ent.remote_path
        sys.stdout.write(message)
        ctxt.storageDao.remove(ent.remote_path)
    elif FileState.CONFLICT_MODIFIED == state:
        message = "conflict modified - %s\n" % ent.remote_path
        sys.stdout.write(message)
    elif FileState.CONFLICT_CREATED == state:
        message = "conflict created - %s\n" % ent.remote_path
        sys.stdout.write(message)
    elif FileState.CONFLICT_VERSION == state:
        message = "conflict version - %s\n" % ent.remote_path
        sys.stdout.write(message)
    elif FileState.DELETE_BOTH == state:
        message = "delete both   - %s\n" % ent.remote_path
        sys.stdout.write(message)
        ctxt.storageDao.remove(ent.remote_path)
    elif FileState.DELETE_REMOTE == state and pull:
        message = "delete local  - %s\n" % ent.remote_path
        ctxt.fs.remove(ent.local_path)
        ctxt.storageDao.remove(ent.remote_path)
    elif FileState.DELETE_LOCAL == state and push:
        message = "delete remote - %s\n" % ent.remote_path
        sys.stdout.write(message)
        response = ctxt.client.files_remove_file(ctxt.root, ent.remote_path)
        if (response.status_code == 200):
            ctxt.storageDao.remove(ent.remote_path)
    else:
        message = "unknown %s %s %s %s %s\n" % (state, push, pull, force, ent.remote_path)
        sys.stdout.write(message)

    return SyncResult(ent, state, message)

def _sync_impl_iter(ctxt, paths, push=False, pull=False, force=False, recursive=False):
    """ An iterator for syncing directories

    yields a file entry followed by a boolean after syncing completes
    i.e.
        g = _sync_file_impl(...)
        fent = next(g)
        success = next(g)
    """
    paths = list(paths)
    while len(paths) > 0:
        dent = paths.pop(0)

        if (ctxt.storageDao.isDir(dent.remote_base)) or (
           ctxt.fs.exists(dent.local_base) and ctxt.fs.isdir(dent.local_base)):

            check_result = _check(ctxt, dent.remote_base, dent.local_base)

            for fent in check_result.files:
                yield fent
                result = _sync_file_impl(ctxt, fent, push, pull, force)
                yield result

            if recursive:
                paths.extend(check_result.dirs)

        else:
            fent = _check_file(ctxt, dent.remote_base, dent.local_base)
            yield fent

            result = _sync_file_impl(ctxt, fent, push, pull, force)
            yield result

# TODO: deprecate this one
def _sync_impl(ctxt, paths, push=False, pull=False, force=False, recursive=False):

    for dent in paths:

        if (ctxt.storageDao.isDir(dent.remote_base)) or (
           ctxt.fs.exists(dent.local_base) and ctxt.fs.isdir(dent.local_base)):

            result = _check(ctxt, dent.remote_base, dent.local_base)

            for fent in result.files:
                _sync_file_impl(ctxt, fent, push, pull, force)

            if recursive:
                _sync_impl(ctxt, result.dirs, push, pull,
                    force, recursive)

        else:

            fent = _check_file(ctxt, dent.remote_base, dent.local_base)
            _sync_file_impl(ctxt, fent, push, pull, force)

def _sync_get_file_impl(ctxt, rpath, lpath):

    response = ctxt.client.files_get_path(ctxt.root, rpath, stream=True)
    rv = int(response.headers['X-YUE-VERSION'])
    rp = int(response.headers['X-YUE-PERMISSION'])
    rm = int(response.headers['X-YUE-MTIME'])

    dpath = ctxt.fs.split(lpath)[0]
    if not ctxt.fs.exists(dpath):
        ctxt.fs.makedirs(dpath)

    bytes_written = 0
    with ctxt.fs.open(lpath, "wb") as wb:
        for chunk in response.stream():
            bytes_written += len(chunk)
            wb.write(chunk)

def _sync_put_file_impl(ctxt, lpath, rpath):

    record = ctxt.fs.file_info(local_path)

    f = ProgressFileReaderWrapper(ctxt.fs, lpath, rpath)
    response = ctxt.client.files_upload(ctxt.root, rpath, f,
        mtime=record.mtime, permission=record.permission)

    if response.status_code == 409:
        raise SyncException("local database out of date. fetch first")

    if response.status_code > 201:
        raise SyncException(response.text)

def _copy_impl(ctxt, src, dst):
    """
    copy from the remote server to a local path, or from a local path
    to a remote server.

    src: either "server://${root}/${remote_path}" or a local file
    dst: either "server://${root}/${remote_path}" or a local file

    both src and dst cannot be both remote or local paths
    """

    tag = "server://"
    if src.startswith(tag):
        root, remote_path = src[len(tag):].split("/", 1)

        if dst.startswith(tag):
            raise SyncException("invalid path: %s" % dst)

        response = ctxt.client.files_get_path(root, remote_path, stream=True)
        with ctxt.fs.open(dst, "wb") as wb:
            for chunk in response.stream():
                wb.write(chunk)

    elif dst.startswith(tag):
        root, remote_path = dst[len(tag):].split("/", 1)

        if src.startswith(tag) or not os.access(src, os.R_OK):
            raise SyncException("invalid path: %s" % src)

        info = ctxt.fs.file_info(src)

        f = ProgressFileReaderWrapper(ctxt.fs, src, remote_path)
        response = client.files_upload(root, remote_path, f,
            mtime=info.mtime, permission=info.permission)

    else:

        with ctxt.fs.open(src, "rb") as rb:
            with ctxt.fs.open(dst, "wb") as wb:
                chunk = rb.read(2048)
                while chunk:
                    wb.write(chunk)
                    chunk = rb.read(2048)

def _list_impl(ctxt, root, path, verbose=False):
    """
    list contents of a remote directory
    """

    response = ctxt.client.files_get_path(root, path, list=True)

    if response.status_code == 404:
        sys.stderr.write("not found: %s\n" % path)
        sys.exit(1)

    elif response.headers['content-type'] != "application/json":
        raise SyncException("Server responded with unexpected type: %s" %
            response.headers['content-type'])
    else:
        data = response.json()['result']

        for dirname in sorted(data['directories']):
            if verbose:
                sys.stdout.write("%s%s/\n" % (" " * (41), dirname))
            else:
                sys.stdout.write("%s/\n" % dirname)

        for item in sorted(data['files'], key=lambda item: item['name']):

            if verbose:
                fvers = "%3d" % item['version']
                fperm = oct(item.get('permission', 0))[2:].zfill(3)
                ftime = time.localtime(item['mtime'])
                fdate = time.strftime('%Y-%m-%d %H:%M:%S', ftime)

                sys.stdout.write("%s %s %12d %s %s\n" % (
                    fvers, fdate, int(item['size']), fperm, item['name']))
            else:
                sys.stdout.write("%s\n" % (item['name']))

def _move_get_actions(ctxt, ents, dst):
    """
    determines what actions, if any, to take given a list
    of paths and a target directory or file location

    returns two lists of items to act upon
        dir_actions: a list of directory paths to move
        file_actions: a list of file paths to move
    """
    _d_actions = []
    _f_actions = []

    if ctxt.fs.isdir(dst.local_base):
        for ent in ents:
            if not ent.remote_base:
                sys.stderr.write("cannot move root directory\n")
                continue
            if not ctxt.fs.exists(ent.local_base):
                sys.stderr.write("path spec not found: %s\n" % ent.local_base)
                continue

            _, name = ctxt.fs.split(ent.local_base)
            item = (
                ent,
                DirEnt(name,
                       ctxt.fs.join(dst.remote_base, name),
                       ctxt.fs.join(dst.local_base, name))
            )
            if ctxt.fs.isdir(ent.local_base):
                _d_actions.append(item)
            elif ctxt.fs.isfile(ent.local_base):
                _f_actions.append(item)

    elif not ctxt.fs.exists(dst.local_base):

        if len(ents) > 1:
            sys.stderr.write("destination is a file\n")
        else:
            ent = ents[0]
            _, name = ctxt.fs.split(ent.local_base)
            item = (
                ent,
                DirEnt(name,
                       dst.remote_base,
                       dst.local_base)
            )
            _f_actions.append(item)

    return _d_actions, _f_actions

def _move_file_impl(ctxt, src, dst):
    """
    src: a DirEnt containing the remote and local path for an existing file
    dst: a Dirent containing the remote and local path after a move operation
    """
    print("f", src, dst)

def _move_dir_impl(ctxt, src, dst):
    """
    src: a DirEnt containing the remote and local path for an existing dir
    dst: a Dirent containing the remote and local path after a move operation
    """
    print("d", src, dst)

def _move_impl(ctxt, ents, dst):

    _d_actions, _f_actions = _move_get_actions(ctxt, ents, dst)

    for src, dst in _d_actions:
        _move_dir_impl(ctxt, src, dst)

    for src, dst in _f_actions:
        _move_file_impl(ctxt, src, dst)

def _remove_impl_local(ctxt, ent):
    """remove db entry and local file"""
    s1 = ctxt.storageDao.remove(ent.remote_base)

    if os.path.exists(ent.local_base):
        ctxt.fs.remove(ent.local_base)
        s3 = True
    else:
        s3 = False

    return s1 and s3

def _remove_impl_remote(ctxt, ent):
    """remove db entry and remote file"""

    s1 = ctxt.storageDao.remove(ent.remote_base)

    response = ctxt.client.files_remove_file(ctxt.root, ent.remote_base)
    s2 = response.status_code == 200

    return s1 and s2

def _remove_impl_both(ctxt, ent):
    """remove db entry, local file, and remote file"""

    s1 = ctxt.storageDao.remove(ent.remote_base)

    response = ctxt.client.files_remove_file(ctxt.root, ent.remote_base)
    s2 = response.status_code == 200
    if not s2:
        print("%s: %s" % (response.status_code, response.text.strip()))

    if os.path.exists(ent.local_base):
        ctxt.fs.remove(ent.local_base)
        s3 = True
    else:
        s3 = False

    return s1 and s2 and s3

def _remove_impl(ctxt, ents, local, remote):
    """
    mode:
           delete both local and remote
    local: delete local file and local db entry
           the resulting state is as if the file had
           never been pulled before
    remote:delete remote file and local db entry
           the resulting state is as if the file had
           never been pushed before.
    """

    if local and remote:
        raise ValueError()
    elif local:
        rm = _remove_impl_local
    elif remote:
        rm = _remove_impl_remote
    else:
        rm = _remove_impl_both

    while len(ents) > 0:
        ent = ents.pop(0)

        # recursion on directories is hard

        if ctxt.storageDao.isDir(ent.remote_base):
            for item in ctxt.storageDao.listdir_files(ent.remote_base):
                abs_path = ctxt.fs.join(ctxt.local_base, item.rel_path)
                ents.append(DirEnt(None, item.rel_path, abs_path))
            # ent is a directory
            print("dir not implemented", ent)
        elif ctxt.storageDao.file_info(ent.remote_base):
            # ent is a file and exists on remote
            if rm(ctxt, ent):
                print(ent.remote_base)
            else:
                print("error removing: %s" % ent.remote_base)

        elif ctxt.fs.exists(ent.local_base):
            # ent is a file and exists locally
            print("not tracked", ent)
        else:
            # ent does not exist locally
            print("fail", ent)

def _merge_get_path(fent):
    # insert the filename version before the file extension
    # unless the file does not have an extension
    path, name = os.path.split(fent.local_path)
    name, ext = os.path.splitext(name)
    if not name:
        name = ext
        ext = ""

    # regex: '^~(.*)\.[lr]@(\d+)(.*$)'
    # original filename is group[0] + group[2]
    lver = "%s/~%s.l@%d%s" % (path, name, fent.lf['version'], ext)
    rver = "%s/~%s.r@%d%s" % (path, name, fent.rf['version'], ext)

    return lver, rver

def _merge_checkout_file_impl(ctxt, fent):
    """
    checkout the remote version and copy the local version
    return the file path, and allow the user to choose their
    own merge tool.
    """

    lver, rver = _merge_get_path(fent)

    _sync_get_file_impl(ctxt, fent.remote_path, rver)

    _copy_impl(ctxt, fent.local_path, lver)

    return lver, rver

def _merge_local_file_impl(ctxt, fent):
    """
    resolve the conflict by taking the remote version
    including any user modifications
    """

    lver, rver = _merge_get_path(fent)

    if os.path.exists(lver):
        _copy_impl(ctxt, lver, fent.local_path)
        ctxt.fs.remove(lver)

    if os.path.exists(rver):
        ctxt.fs.remove(rver)

    return fent.local_path

def _merge_remote_file_impl(ctxt, fent):
    """
    resolve the conflict by taking the local version
    including any user modifications
    """

    lver, rver = _merge_get_path(fent)

    if os.path.exists(rver):
        _copy_impl(ctxt, rver, fent.local_path)
        ctxt.fs.remove(rver)

    if os.path.exists(lver):
        ctxt.fs.remove(lver)

    return fent.local_path

def _merge_impl(ctxt, paths, action):

    for dent in paths:
        if (ctxt.storageDao.isDir(dent.remote_base)) or (ctxt.fs.exists(dent.local_base) and ctxt.fs.isdir(dent.local_base)):
            print("error, directory", dent.remote_base)
        else:
            fent = _check_file(ctxt, dent.remote_base, dent.local_base)
            action(ctxt, fent)

def _attr_impl(ctxt, path):

    attr = ctxt.attr(path)

    sys.stdout.write("[settings]\n")
    for keyname, value in attr.settings.items():
        sys.stdout.write("%s=%s\n" % (keyname, value))

    sys.stdout.write("\n[blacklist]\n")
    for pattern in attr.blacklist_patterns:
        sys.stdout.write("%s\n" % pattern)

def _setpass_impl(ctxt):

    response = ctxt.client.files_user_key(mode='SERVER')

    if response.status_code == 200:

        sys.stdout.write("Changing the Password for Server Side Encryption\n")
        sys.stdout.write("Enter the current Server Password\n")
        sys.stdout.write(
            "Then enter the new password twice to confirm the change\n")
        sys.stdout.write(
                "Do not forget this password. It cannot be recovered!\n\n")

        svr_password = get_pass('server password: ')
        new_password = get_pass('   new password: ')
        chk_password = get_pass('retype password: ')

    elif response.status_code == 404:
        sys.stdout.write("Set the Password for Server Side Encryption\n")
        sys.stdout.write(
            "Type the new password twice to confirm setting the password\n")
        sys.stdout.write(
                "Do not forget this password. It cannot be recovered!\n\n")

        svr_password = ""
        new_password = get_pass('server password: ')
        chk_password = get_pass('retype password: ')
        svr_password = new_password

    else:
        sys.stderr.write("Unexpected server error!\n")
        sys.exit(1)

    if new_password != chk_password:
        sys.stderr.write("password do not match!\n")
        sys.exit(1)

    headers = {'X-YUE-PASSWORD': svr_password}
    bpass = new_password.encode("utf-8")
    response = ctxt.client.files_change_password(bpass, headers=headers)

    if response.status_code != 200:
        sys.stderr.write("Failed to change password!\n")
        sys.exit(1)
    else:
        sys.stderr.write("Successfully changed password.\n")

def _setkey_impl(ctxt, workfactor):

    response = ctxt.client.files_user_key(mode='CLIENT')

    if response.status_code == 200:

        sys.stdout.write(
            "Changing the Password for Client Side Encryption Key\n")
        sys.stdout.write("Enter the current password\n")
        sys.stdout.write(
            "Then type the new password twice to confirm the change\n")
        sys.stdout.write(
            "Do not forget this password. It cannot be recovered!\n\n")

        current_key = response.json()['result']['key']
        validatekey(current_key)

        cnt_password = get_pass('client password: ')
        new_password = get_pass('   new password: ')
        chk_password = get_pass('retype password: ')

        if new_password != chk_password:
            sys.stderr.write("password do not match!\n")
            sys.exit(1)

        new_key = recryptkey(cnt_password,
            new_password, current_key, workfactor=workfactor)
        bkey = new_key.encode("utf-8")

        response = ctxt.client.files_set_user_key(bkey)
        if response.status_code != 200:
            sys.stderr.write("Failed to update key!\n")
        else:
            sys.stderr.write("Successfully changed key.\n")

    elif response.status_code == 404:

        sys.stdout.write("Set the Client Side Encryption Key\n")
        sys.stdout.write(
            "Type the password twice to confirm setting the key\n")
        sys.stdout.write(
            "Do not forget this password. It cannot be recovered!\n\n")

        cnt_password = get_pass('client password: ')
        chk_password = get_pass('retype password: ')

        if cnt_password != chk_password:
            sys.stderr.write("password do not match!\n")
            sys.exit(1)

        new_key = cryptkey(cnt_password, workfactor=workfactor)
        bkey = new_key.encode("utf-8")

        response = ctxt.client.files_set_user_key(bkey)
        if response.status_code != 200:
            sys.stderr.write("Failed to update key!\n")
        else:
            sys.stderr.write("Successfully changed key.\n")
    else:
        sys.stderr.write("Unexpected server error!\n")
        sys.exit(1)

def _setpublic_impl(ctxt, paths, password, revoke):

    headers = {}
    if password:
        headers = {'X-YUE-PASSWORD': password}

    for ent in paths:

        if not ctxt.fs.isfile(ent.local_base):
            sys.stderr.write("error is directory: %s\n" % ent.remote_base)
            continue

        info = ctxt.storageDao.file_info(ent.remote_base)

        if not info or info['remote_version'] == 0:
            sys.stderr.write("error: push '%s' first\n" % ent.remote_base)
            continue

        if info['remote_encryption'] in ('client', 'server'):
            sys.stderr.write("error: '%s' is encrypted by %s\n" % (
                ent.remote_base, info['remote_encryption']))
            continue

        response = ctxt.client.files_make_public(
            ctxt.root, ent.remote_base,
            revoke=revoke, headers=headers)

        if response.status_code != 200:
            sys.stderr.write("error: %s\n" % ent.remote_base)
        else:

            res_id = response.json()['result']['id']

            ctxt.storageDao.update(ent.remote_base,
                {'remote_public': res_id})

            url = "api/fs/public/%s" % res_id

            sys.stdout.write("%s/%s\n" % (ctxt.client.host(), url))

def _getpublic_impl(ctxt, paths):

    for ent in paths:

        if not ctxt.fs.isfile(ent.local_base):
            sys.stderr.write("error is directory: %s\n" % ent.remote_base)
            continue

        info = ctxt.storageDao.file_info(ent.remote_base)

        if not info or not info['remote_public']:
            sys.stderr.write(
                "error: '%s' not publicly accessible\n" % ent.remote_base)
            continue

        res_id = info['remote_public']

        if res_id:
            url = "api/fs/public/%s" % res_id
            sys.stdout.write("%s/%s\n" % (ctxt.client.host(), url))
        else:
            sys.stderr.write("error: %s\n" % ent.remote_base)

class CLI(object):
    def __init__(self):
        super(CLI, self).__init__()

    def register(self, parser):
        pass

    def execute(self, args):
        pass

class RootsCLI(CLI):
    """
    retrieve which buckets are available for a user
    """

    def register(self, parser):
        subparser = parser.add_parser('roots', aliases=['buckets'],
            help="list available buckets which can be accessed")
        subparser.set_defaults(func=self.execute, cli=self)

        subparser.add_argument('-u', '--username',
            default=None)

        subparser.add_argument('-p', '--password',
            default=None)

        subparser.add_argument('hostname')

    def execute(self, args):

        client = connect(args.hostname, args.username, args.password)

        response = client.files_get_roots()

        if response.status_code != 200:
            raise SyncException("unexpected error: %s" % response.status_code)

        roots = response.json()['result']
        for root in roots:
            sys.stdout.write("%s\n" % root)

class InitCLI():
    def register(self, parser):

        subparser = parser.add_parser('init',
            help="initialize a directory")
        subparser.set_defaults(func=self.execute, cli=self)

        subparser.add_argument('-u', '--username',
            default=None)

        subparser.add_argument('-p', '--password',
            default=None)

        subparser.add_argument('-b', '--local_base', dest="local_base",
            default=os.getcwd(),
            help="the directory to checkout to (pwd)")

        subparser.add_argument('-r', '--remote_base', dest="remote_base",
            default="",
            help="the relative path-prefix to checkout ("")")

        subparser.add_argument('-f', '--force', action='store_true',
            help="initialize even if the directory is not empty")

        subparser.add_argument('hostname')
        subparser.add_argument('root', nargs="?", default="default")

    def execute(self, args):
        # get the user apikey before creating any resources,
        # validate the user. use the apikey instead of a password
        # to prevent storing the password on disk

        client = connect(args.hostname, args.username, args.password)
        try:
            userinfo = client.user_get_user().json()['result']
        except Exception as e:
            logging.error("unable to validate user: %s" % e)
            return
        api_password = "APIKEY " + userinfo['apikey']

        if len(os.listdir(args.local_base)) and not args.force:
            sys.stderr.write("error: current directory is not empty\n")
            return

        # create a database
        cfgdir = os.path.join(args.local_base, ".yue")
        dbpath = os.path.abspath(os.path.join(cfgdir, "database.sqlite"))
        userpath = os.path.abspath(os.path.join(cfgdir, "userdata.json"))
        if not os.path.exists(cfgdir):
            os.makedirs(cfgdir)

        dburl = "sqlite:///" + dbpath
        db = db_connect(dburl)
        db.create_all()

        cm = CryptoManager()

        private_key, public_key = cm.generate_key(cfgdir, "rsa", 2048)

        enc_password = cm.encrypt64(public_key, api_password.encode("utf-8"))
        userdata = {
            "username": args.username,
            "password": enc_password,
            "hostname": args.hostname,
            "root": args.root,
            "remote_base": args.remote_base,
            "dburl": dburl,
        }

        with open(userpath, "w") as wf:
            json.dump(userdata, wf, indent=4, sort_keys=True)

        storageDao = LocalStorageDao(db, db.tables)

        fs = FileSystem()

        ctxt = SyncContext(client, storageDao, fs,
            args.root, args.remote_base, args.local_base)

        _fetch(ctxt)

class FetchCLI(object):

    def register(self, parser):
        subparser = parser.add_parser('fetch',
            help="update the local database")
        subparser.set_defaults(func=self.execute, cli=self)

    def execute(self, args):

        ctxt = get_ctxt(os.getcwd())

        _fetch(ctxt)

class StatusCLI(object):
    """
    status supports up to 4 levels of verbosity
    """

    def register(self, parser):

        subparser = parser.add_parser('status', aliases=['st'],
            help="check for changes")
        subparser.set_defaults(func=self.execute, cli=self)

        subparser.add_argument("-v", "--verbose", default=0,
            action="count",
            help="show detailed information")

        subparser.add_argument("-r", "--recursion",
            action="store_true",
            help="check the status for sub directories")

        subparser.add_argument("paths", nargs="*",
            help="list of paths to check the status on")

    def execute(self, args):

        ctxt = get_ctxt(os.getcwd())
        ctxt.verbose = args.verbose

        # ---

        paths = _parse_path_args(ctxt.fs,
            ctxt.remote_base, ctxt.local_base, args.paths)

        first = True
        for dent in paths:
            if not first:
                sys.stdout.write("\n")

            if ctxt.fs.isdir(dent.local_base):
                if "" != dent.remote_base or len(paths) > 1:
                    sys.stdout.write("%s/\n" % dent.local_base)

                _status_dir_impl(ctxt, dent.remote_base, dent.local_base,
                    args.recursion)
            else:
                ent = _check_file(ctxt, dent.remote_base, dent.local_base)
                _status_file_impl(ctxt, ent)

            first = False
        end = time.time()
        return

class SyncCLI(object):

    def register(self, parser):

        data = [
            ('sync', True, True, "sync local and remote files"),
            ('push', True, False, "push local changes to remote"),
            ('pull', False, True, "pull remote changes")
        ]
        for name, push, pull, doc in data:

            subparser = parser.add_parser(name, help=doc)
            subparser.set_defaults(
                func=self.execute, cli=self, push=push, pull=pull)

            subparser.add_argument('-u', "--update",
                action="store_true",
                help="fetch prior to sync")

            subparser.add_argument('-f', "--force",
                action="store_true",
                help="overwrite conflicts")

            subparser.add_argument("-r", "--recursion",
                action="store_true",
                help="check the status for sub directories")

            subparser.add_argument("paths", nargs="*",
                help="list of paths to check the status on")

    def execute(self, args):

        ctxt = get_ctxt(os.getcwd())

        # todo: consider disabling delete on SYNC by default
        #       leave on for push and pull

        if args.update:
            # TODO: consider a quite option, no logging
            _fetch(ctxt)

        paths = _parse_path_args(ctxt.fs, ctxt.remote_base,
            ctxt.local_base, args.paths)

        _sync_impl(ctxt, paths, push=args.push, pull=args.pull,
            force=args.force, recursive=args.recursion)

class MergeCheckoutCLI(object):

    def register(self, parser):

        subparser = parser.add_parser('checkout', aliases=['co'],
            help="checkout both remote and local versions for merging")
        subparser.set_defaults(func=self.execute, cli=self)

        # TODO: sub-sub parser checkout, merge-local, merge-remote, revert
        # last three commands clean up two files created by checkout
        # merge-local and merge-remote fail if the expected file does not exist
        # all commands require a user to fetch/pull prior and push after
        subparser.add_argument("paths", nargs="*",
            help="list of paths to check the status on")

    def execute(self, args):
        ctxt = get_ctxt(os.getcwd())
        paths = _parse_path_args(ctxt.fs, ctxt.remote_base,
            ctxt.local_base, args.paths)
        # TODO: if no args or for args that are directories -
        #        scan for unique set of conflicted files and checkout

        def action(ctxt, fent):
            lver, rver = _merge_checkout_file_impl(ctxt, fent)
            print(lver)
            print(rver)

        _merge_impl(ctxt, paths, action)

class MergeLocalCLI(object):

    def register(self, parser):

        subparser = parser.add_parser('local',
            help="resolve a merge by taking the local file")
        subparser.set_defaults(func=self.execute, cli=self)

        subparser.add_argument("paths", nargs="*",
            help="list of paths to check the status on")

    def execute(self, args):
        ctxt = get_ctxt(os.getcwd())
        paths = _parse_path_args(ctxt.fs, ctxt.remote_base,
            ctxt.local_base, args.paths)

        def action(ctxt, fent):

            path = _merge_local_file_impl(ctxt, fent)
            print("local", path)

        _merge_impl(ctxt, paths, action)


class MergeRemoteCLI(object):

    def register(self, parser):

        subparser = parser.add_parser('remote',
            help="resolve a merge by taking the remote file")
        subparser.set_defaults(func=self.execute, cli=self)

        subparser.add_argument("paths", nargs="*",
            help="list of paths to check the status on")

    def execute(self, args):
        ctxt = get_ctxt(os.getcwd())
        paths = _parse_path_args(ctxt.fs, ctxt.remote_base,
            ctxt.local_base, args.paths)

        def action(ctxt, fent):
            path = _merge_local_file_impl(ctxt, fent)
            print("local", path)

        _merge_impl(ctxt, paths, action)

class MergeCLI(object):

    def register(self, parser):

        subparser = parser.add_parser('merge',
            help="merge utility")

        parser = subparser.add_subparsers()
        MergeCheckoutCLI().register(parser)
        MergeLocalCLI().register(parser)
        MergeRemoteCLI().register(parser)

    def execute(self, args):

        print("test")

class InfoCLI(object):
    """
    print file count and quota information

    verbose logging will print bytes instead of megabytes
    """

    def register(self, parser):

        subparser = parser.add_parser('info',
            help="view user information")
        subparser.add_argument("-v", "--verbose", default=0,
            action="count",
            help="show detailed information")
        subparser.set_defaults(func=self.execute, cli=self)

    def execute(self, args):

        ctxt = get_ctxt(os.getcwd())

        sys.stdout.write("hostname:    %s\n" % ctxt.client.host())
        sys.stdout.write("root:        %s\n" % ctxt.root)
        sys.stdout.write("remote_base: %s\n" % ctxt.remote_base)
        sys.stdout.write("local_base:  %s\n" % ctxt.local_base)
        sys.stdout.write("\n")

        response = ctxt.client.files_quota()

        obj = response.json()['result']

        usage = obj['nbytes']
        cap = obj['quota']
        if args.verbose == 0:
            cap = "%.1f MB" % (cap / 1024 / 1024)
            usage = "%.1f MB" % (usage / 1024 / 1024)

        sys.stdout.write("file_count:  %d\n" % obj['nfiles'])
        sys.stdout.write("usage:       %s\n" % usage)
        sys.stdout.write("capacity:    %s\n" % cap)

class ListCLI(object):

    def register(self, parser):

        subparser = parser.add_parser('list', aliases=['ls'],
            help="list contents of a remote directory")
        subparser.set_defaults(func=self.execute, cli=self)

        subparser.add_argument("-v", "--verbose", action='store_true',
            help="show detailed file information")

        subparser.add_argument("--root", default=None,
            help="file system root to list")

        subparser.add_argument('path', nargs="?", default="",
            help="relative remote path")

    def execute(self, args):

        ctxt = get_ctxt(os.getcwd())

        root = args.root or ctxt.root
        _list_impl(ctxt, root, args.path.strip("/"), args.verbose)

class MoveCLI(object):

    def register(self, parser):

        subparser = parser.add_parser('move', aliases=['mv'],
            help="move files or directories")
        subparser.set_defaults(func=self.execute, cli=self)

        subparser.add_argument('paths', nargs="+",
            help="relative remote path")

        subparser.add_argument('destination',
            help="relative remote path")

    def execute(self, args):

        ctxt = get_ctxt(os.getcwd())

        paths = _parse_path_args(ctxt.fs, ctxt.remote_base,
            ctxt.local_base, args.paths)

        destination = _parse_path_args(ctxt.fs, ctxt.remote_base,
            ctxt.local_base, [args.destination])[0]

        _move_impl(ctxt, paths, destination)

class RemoveCLI(object):

    def register(self, parser):

        subparser = parser.add_parser('remove', aliases=['rm'],
            help="move files or directories")
        subparser.set_defaults(func=self.execute, cli=self)

        group = subparser.add_mutually_exclusive_group()
        group.add_argument('--local', action='store_true')
        group.add_argument('--remote', action='store_true')

        subparser.add_argument('paths', nargs="+",
            help="relative remote path")

    def execute(self, args):

        ctxt = get_ctxt(os.getcwd())

        paths = _parse_path_args(ctxt.fs, ctxt.remote_base,
            ctxt.local_base, args.paths)

        _remove_impl(ctxt, paths, args.local, args.remote)

class AttrCLI(object):

    def register(self, parser):

        subparser = parser.add_parser('attr',
            help="print directory attributes")
        subparser.set_defaults(func=self.execute, cli=self)

        subparser.add_argument('path', nargs="?", default="",
            help="local directory path")

    def execute(self, args):
        cwd = os.getcwd()
        ctxt = get_ctxt(cwd)
        _attr_impl(ctxt, args.path or cwd)

class SetPassCLI(object):

    def register(self, parser):

        subparser = parser.add_parser('setpass',
            help="set or change encryption server password")
        subparser.set_defaults(func=self.execute, cli=self)

    def execute(self, args):

        cwd = os.getcwd()
        ctxt = get_ctxt(cwd)

        _setpass_impl(ctxt)

class SetKeyCLI(object):

    def register(self, parser):

        subparser = parser.add_parser('setkey',
            help="set or change encryption client key")
        subparser.set_defaults(func=self.execute, cli=self)

        subparser.add_argument('-w', '--workfactor', type=int, default=12,
            help="bcrypt workfactor")

    def execute(self, args):

        cwd = os.getcwd()
        ctxt = get_ctxt(cwd)

        _setkey_impl(ctxt, args.workfactor)

class SetPublicCLI(object):

    def register(self, parser):

        subparser = parser.add_parser('setpublic',
            help="set or revoke public access to a file")
        subparser.set_defaults(func=self.execute, cli=self)

        subparser.add_argument("--password", default=None, type=str,
            help="use as a password for public access")

        subparser.add_argument("--revoke", action='store_true',
            help="revoke public access")

        subparser.add_argument("paths", nargs="*",
            help="paths to modify")

    def execute(self, args):

        cwd = os.getcwd()
        ctxt = get_ctxt(cwd)

        paths = _parse_path_args(ctxt.fs,
            ctxt.remote_base, ctxt.local_base, args.paths)

        _setpublic_impl(ctxt, paths, args.password, args.revoke)

class GetPublicCLI(object):

    def register(self, parser):

        subparser = parser.add_parser('getpublic',
            help="set or revoke public access to a file")
        subparser.set_defaults(func=self.execute, cli=self)

        subparser.add_argument("paths", nargs="*",
            help="paths to get information for")

    def execute(self, args):

        cwd = os.getcwd()
        ctxt = get_ctxt(cwd)

        paths = _parse_path_args(ctxt.fs,
            ctxt.remote_base, ctxt.local_base, args.paths)

        _getpublic_impl(ctxt, paths)

class GetCLI(object):

    def register(self, parser):

        subparser = parser.add_parser('get',
            help="copy a remote file locally")
        subparser.set_defaults(func=self.execute, cli=self)

        subparser.add_argument("remote_path",
            help="path to a remote file")

        subparser.add_argument("local_path", default=None, nargs="?",
            help="path to a local file")

    def execute(self, args):
        ctxt = get_ctxt(os.getcwd())

        args.local_path = os.path.abspath(args.local_path)

        _sync_get_file_impl(ctxt, args.remote_path, args.local_path)

class PutCLI(object):

    def register(self, parser):

        subparser = parser.add_parser('put',
            help="copy a local file to remote")
        subparser.set_defaults(func=self.execute, cli=self)

        subparser.add_argument("local_path",
            help="path to a local file")

        subparser.add_argument("remote_path",
            help="path to a remote file")

    def execute(self, args):
        ctxt = get_ctxt(os.getcwd())

        _sync_put_file_impl(ctxt, args.local_path, args.remote_path)

class CopyCLI(object):

    def register(self, parser):

        subparser = parser.add_parser('copy', aliases=['cp'],
            help="copy a file up or down")
        subparser.set_defaults(func=self.execute, cli=self)

        subparser.add_argument('src', help="source file to copy")
        subparser.add_argument('dst', help="destination path")

    def execute(self, args):
        ctxt = get_ctxt(os.getcwd())

        _copy_impl(ctxt, ctxt, args.src, args.dst)

def _register_parsers(parser):

    RootsCLI().register(parser)
    InitCLI().register(parser)
    FetchCLI().register(parser)
    StatusCLI().register(parser)
    SyncCLI().register(parser)
    MergeCLI().register(parser)
    InfoCLI().register(parser)
    ListCLI().register(parser)
    MoveCLI().register(parser)
    RemoveCLI().register(parser)
    AttrCLI().register(parser)
    SetPassCLI().register(parser)
    SetKeyCLI().register(parser)
    SetPublicCLI().register(parser)
    GetPublicCLI().register(parser)

    # GetCLI().register(parser)
    # PutCLI().register(parser)
    # CopyCLI().register(parser)

def main():

    parser = argparse.ArgumentParser(
        description='sync utility',
        epilog="The environment variable YUE_ECHO_PASSWORD can be set"
        " to echo passwords that are typed in.")
    subparsers = parser.add_subparsers()
    _register_parsers(subparsers)
    args = parser.parse_args()

    if hasattr(args, "username"):
        if args.username is None:
            args.password = input("username:")

        if args.password is None and ':' in args.username:
            args.username, args.password = args.username.split(':', 1)
        elif args.password is None:
            args.password = get_pass("password:")

    if hasattr(args, "paths"):
        if len(args.paths) == 0:
            args.paths.append(os.getcwd())

    FORMAT = '%(levelname)-8s - %(message)s'
    logging.basicConfig(level=logging.INFO, format=FORMAT)

    if not hasattr(args, 'func'):
        parser.print_help()
    else:
        args.func(args)


if __name__ == '__main__':
    main()

