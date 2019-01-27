#! python $this init -u admin:admin localhost:4200

"""
todo: create a stat cache to avoid making os calls for the same file

add resolve-remote / resolve-local / resolve-fetch commands to fix conflicts
    resolve-fetch to download a specific file as `${filename}.remote`
    provide the oportunity to view the remote file, overwrite local
    and then resolve-local
    possibly sub commands e.g. `sync resolve <action> <action-args>`

"""
import os, sys
import argparse
import posixpath
import logging
import json
import datetime, time

import yueserver
from yueserver.tools.upload import S3Upload
from yueserver.dao.search import regexp
from yueserver.app import connect
from yueserver.framework.client import split_auth
from yueserver.framework.crypto import CryptoManager
from yueserver.tools.sync import SyncManager
from yueserver.dao.filesys.filesys import FileSystem

from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm.session import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy.schema import Table, Column
from sqlalchemy.types import Integer, String
from sqlalchemy import and_, or_, not_, select, column, \
    update, insert, delete, asc, desc
from sqlalchemy.sql.expression import bindparam

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
        except:
            pass
        if 'microsoft' in release:
            name = "nt"
    return name

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
        # text
        Column('rel_path', String, primary_key=True, nullable=False),

        # number
        Column('local_version', Integer, default=0),
        Column('remote_version', Integer, default=0),
        Column('local_size', Integer, default=0),
        Column('remote_size', Integer, default=0),
        Column('local_permission', Integer, default=0),
        Column('remote_permission', Integer, default=0),

        # date
        Column('local_mtime', Integer, default=0),
        Column('remote_mtime', Integer, default=0)
    )

class DatabaseTables(object):
    def __init__(self, metadata):
        super(DatabaseTables, self).__init__()
        self.LocalStorageTable = LocalStorageTable(metadata)

class LocalStoragDao(object):
    def __init__(self, db, dbtables):
        super(LocalStoragDao, self).__init__()
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
        else:
            self.update(rel_path, record, commit)

    def remove(self, rel_path, commit=True):

        query = delete(self.dbtables.LocalStorageTable) \
            .where(self.dbtables.LocalStorageTable.c.rel_path == rel_path)

        self.db.session.execute(query)

        if commit:
            self.db.session.commit()

    def listdir(self, path_prefix="", limit=None, offset=None, delimiter='/'):

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

        dirs = set()
        files = []

        # todo replace fetchall with paging
        for item in self.db.session.execute(query).fetchall():
            item = dict(item)
            path = item['rel_path'][len(path_prefix):]

            if delimiter in path:
                name, _ = path.split(delimiter, 1)
                dirs.add(name)
            else:
                item['rel_path'] = path
                files.append(item)

        return dirs, files

    def isDir(self, path):
        FsTab = self.dbtables.LocalStorageTable

        if not path:
            return True

        if not path.endswith("/"):
            path += "/"

        where = FsTab.c.rel_path.startswith(bindparam('path', path))

        query = select(['*']) \
            .select_from(FsTab) \
            .where(where).limit(1)

        result = self.db.session.execute(query)
        item = result.fetchone()

        return item is not None

    def file_info(self, path):

        FsTab = self.dbtables.LocalStorageTable

        query = select(['*']) \
            .select_from(FsTab) \
            .where(FsTab.c.rel_path == path)

        item = self.db.session.execute(query).fetchone()

        if item is None:
            return None

        item = dict(item)
        item['rel_path'] = posixpath.split(path)[1]
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

class SyncContext(object):
    """docstring for SyncContext"""
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
        self.blacklist = set()

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
        }

    def _update_int(self, obj, key, value):
        if value is not None:
            obj[key] = value

    def localFromInfo(self, info):
        return self.local(info.version, info.size, info.mtime, info.permission)

    def local(self, version=None, size=None, mtime=None, permission=None):

        self._update_int(self.lf, "local_version", version)
        self._update_int(self.lf, "local_size", size)
        self._update_int(self.lf, "local_mtime", mtime)
        self._update_int(self.lf, "local_permission", permission)

        return self

    def remoteFromInfo(self, info):
        return self.remote(info.version, info.size, info.mtime, info.permission)

    def remote(self, version=None, size=None, mtime=None, permission=None):

        self._update_int(self.rf, "remote_version", version)
        self._update_int(self.rf, "remote_size", size)
        self._update_int(self.rf, "remote_mtime", mtime)
        self._update_int(self.rf, "remote_permission", permission)

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
    DELETE_BOTH = "delete-both"
    DELETE_REMOTE = "delete-remote"
    DELETE_LOCAL = "delete-local"

    @staticmethod
    def symbol(state):
        if FileState.SAME == state:
            sym = "--"
        if FileState.PUSH == state:
            sym = ">-"
        if FileState.PULL == state:
            sym = "-<"
        if FileState.ERROR == state:
            sym = "ee"
        if FileState.CONFLICT_MODIFIED == state:
            sym = "mm"
        if FileState.CONFLICT_CREATED == state:
            sym = "cc"
        if FileState.CONFLICT_VERSION == state:
            sym = "vv"
        if FileState.DELETE_BOTH == state:
            sym = "xx"
        if FileState.DELETE_REMOTE == state:
            sym = "-x"
        if FileState.DELETE_LOCAL == state:
            sym = "x-"
        return sym

class DirEnt(object):
    """docstring for DirEnt"""
    def __init__(self, name, remote_base, local_base, state=None):
        super(DirEnt, self).__init__()
        self.remote_base = remote_base
        self.local_base = local_base
        self._name = name
        self._state = state or FileState.ERROR

    def state(self):
        #if self.remote_base is None and self.local_base is None:
        #    return FileState.ERROR
        #elif self.remote_base is None and self.local_base is not None:
        #    return FileState.PUSH
        #elif self.remote_base is not None and self.local_base is None:
        #    return FileState.PULL
        #elif self.remote_base is not None and self.local_base is not None:
        #    return FileState.SAME
        return self._state

    def name(self):
        return self._name

    def __str__(self):
        return "DirEnt<%s,%s>" % (self.remote_base, self._state)

    def __repr__(self):
        return "DirEnt<%s,%s>" % (self.remote_base, self._state)

class FileEnt(object):
    def __init__(self, remote_path, local_path, lf, rf, af):
        super(FileEnt, self).__init__()
        self.remote_path = remote_path
        self.local_path = local_path

        self.lf = lf
        self.rf = rf
        self.af = af

    def __str__(self):
        return "FileEnt<%s,%s>" % (self.remote_path, self.local_path)

    def __repr__(self):
        return "FileEnt<%s,%s>" % (self.remote_path, self.local_path)

    def name(self):
        return posixpath.split(self.remote_path)[1]

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
                    return FileState.PUSH + ":3a"
                else:
                    # both modified
                    return FileState.CONFLICT_MODIFIED + ":3b"

            return FileState.ERROR + ":3b"

    def state(self):

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

        # TODO: _del|local and _del|remote how to handle?

        lfnull = self.lf is None
        rfnull = self.rf is None
        afnull = self.af is None

        lfe = self.lf is not None
        rfe = self.rf is not None
        afe = self.af is not None

        # 0: error
        if lfnull and rfnull and afnull:
            return FileState.ERROR

        # 1 : push
        if lfnull and rfnull and afe:
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

    def data(self):
        lv = ("%2d" % self.lf.get('version', 0)) if self.lf else "--"
        rv = ("%2d" % self.rf.get('version', 0)) if self.rf else "--"
        av = ("%2d" % self.af.get('version', 0)) if self.af else "--"

        lm = ("%10d" % self.lf.get('mtime', 0)) if self.lf else ("-"*10)
        rm = ("%10d" % self.rf.get('mtime', 0)) if self.rf else ("-"*10)
        am = ("%10d" % self.af.get('mtime', 0)) if self.af else ("-"*10)

        _ls = ("%10d" % self.lf.get('size', 0)) if self.lf else ("-"*10)
        _rs = ("%10d" % self.rf.get('size', 0)) if self.rf else ("-"*10)
        _as = ("%10d" % self.af.get('size', 0)) if self.af else ("-"*10)

        lp = ("%5s"%oct(self.lf.get('permission', 0))) if self.lf else ("-"*5)
        rp = ("%5s"%oct(self.rf.get('permission', 0))) if self.rf else ("-"*5)
        ap = ("%5s"%oct(self.af.get('permission', 0))) if self.af else ("-"*5)

        triple = [
            (lv, rv, av),
            (lm, rm, am),
            (_ls, _rs, _as),
            (lp, rp, ap),
        ]
        return "/".join(["%s,%s,%s" % t for t in triple])

    def stat(self):

        st_lv = ("%2d" % self.lf.get('version', 0)) if self.lf else "--"
        #st_am = ("%11d" % self.af.get('mtime', 0)) if self.af else ("-"*11)
        mtime = self.af.get('mtime', 0) if self.af else 0
        if mtime > 0:
            st_am = time.strftime('%y-%m-%d %H:%M:%S', time.localtime(mtime))
        else:
            st_am = "-" * 17
        st_ap = ("%5s"%oct(self.af.get('permission', 0))) if self.af else ("-"*5)
        st_as = ("%12d" % self.af.get('size', 0)) if self.af else ("-"*12)

        return "%s %s %s %s" % (st_lv, st_as, st_ap[2:], st_am)

class CheckResult(object):
    def __init__(self, remote_base, dirs, files):
        self.remote_base = remote_base
        super(CheckResult, self).__init__()
        self.dirs = dirs
        self.files = files

    def __str__(self):
        return "CheckResult<%s,%d,%d>" % (self.remote_base, len(self.dirs), len(self.files))

    def __repr__(self):
        return "CheckResult<%s, %d,%d>" % (self.remote_base, len(self.dirs), len(self.files))

class ProgressFileReaderWrapper(object):
    def __init__(self, fs, path, remote_path):
        super(ProgressFileReaderWrapper, self).__init__()
        self.fs = fs
        self.path = path
        self.remote_path = remote_path
        self.info = self.fs.file_info(path)
        self.bytes_read = 0

    def __iter__(self):
        with self.fs.open(self.path, 'rb') as rb:
            for i, chunk in enumerate(iter(lambda: rb.read(2048), b"")):
                yield chunk
                self.bytes_read += len(chunk)
                #percent = 100 * self.bytes_read / self.info.size
                # send an update approximately every quarter MB
                if i % 256 == 0:
                    sys.stderr.write("\r%s - %d/%d     " % (
                        self.remote_path, self.bytes_read, self.info.size))
            sys.stderr.write("\r%s - %d/%d\n" % (
                self.remote_path, self.bytes_read, self.info.size))

    def __len__(self):
        return self.info.size

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

    path = connection_string[len("sqlite:///"):]
    if path and not os.access(path, os.W_OK):
        logging.warning("database at %s not writable" % connection_string)

    return db

def get_blacklist(directory, default=None):

    blacklist_file = os.path.join(directory, ".yueignore")
    if default is None:
        blacklist = set([".yue"])
    else:
        blacklist = set(default)
    if os.path.exists(blacklist_file):
        with open(blacklist_file, "r") as rf:
            for line in rf:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                blacklist.add(line)
    return blacklist

def get_cfg(directory):

    cwd = directory

    relpath = ""

    blacklist = get_blacklist(directory)
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
        blacklist |= get_blacklist(directory)
        names = os.listdir(directory)

    cfgdir = os.path.join(directory, '.yue')
    if not os.path.exists(cfgdir):
        raise Exception("not found: %s" % cfgdir)

    pemkey_path = os.path.join(cfgdir, 'rsa.pem')
    with open(pemkey_path, "rb") as rb:
        pemkey = rb.read()

    userdata_path = os.path.join(cfgdir, 'userdata.json')
    with open(userdata_path, "r") as rf:
        userdata = json.load(rf)

    cm = CryptoManager()
    userdata['password'] = cm.decrypt64(pemkey,
        userdata['password']).decode("utf-8")

    userdata['cfgdir'] = directory
    userdata['local_base'] = directory
    userdata['current_local_base'] = cwd
    userdata['current_remote_base'] = posixpath.join(userdata['remote_base'], relpath)
    userdata['blacklist'] = blacklist
    return userdata

def get_ctxt(directory):

    userdata = get_cfg(os.getcwd())

    db = db_connect(userdata['dburl'])

    client = connect(userdata['hostname'],
        userdata['username'], userdata['password'])

    storageDao = LocalStoragDao(db, db.tables)

    fs = FileSystem()

    ctxt = SyncContext(client, storageDao, fs,
        userdata['root'], userdata['remote_base'], userdata['local_base'])

    ctxt.blacklist = userdata['blacklist']
    ctxt.current_local_base = userdata['current_local_base']
    ctxt.current_remote_base = userdata['current_remote_base']

    return ctxt

def _fetch(ctxt):

    page = 0
    limit = 500
    while True:
        params = {'limit': limit, 'page': page}
        try:
            response = ctxt.client.files_get_index(
                ctxt.root, ctxt.remote_base, **params)
        except Exception as e:
            logging.error("unable to fetch: %s" % e)
            return
        if response.status_code != 200:
            sys.stderr.write("fetch error...")
            return

        try:
            files = response.json()['result']
        except Exception as e:
            print(response.text)
            raise e
        for f in files:
            record = {
                "remote_size": f['size'],
                "remote_mtime": f['mtime'],
                "remote_permission": f['permission'],
                "remote_version": f['version']
            }
            ctxt.storageDao.upsert(f['path'], record, commit=False)
        page += 1
        if len(files) != limit:
            break

    ctxt.storageDao.db.session.commit()

def _check(ctxt, remote_base, local_base, blacklist=None):

    if remote_base and not remote_base.endswith("/"):
        remote_base += "/"

    if blacklist is None:
        blacklist = {".yue"}

    dirs = []
    files = []
    _dirs, _files = ctxt.storageDao.listdir(remote_base)
    # TODO: looks like memfs impl for exists is broken for dirs
    if not ctxt.fs.islocal(local_base) or ctxt.fs.exists(local_base):
        _names = set(ctxt.fs.listdir(local_base))
    else:
        _names = set()

    # neither or these cases are handled:
    #   TODO: remote directory, local file with same name
    #   TODO: local directory, remote file with same name

    for d in _dirs:

        if d in blacklist:
            continue

        remote_path = posixpath.join(remote_base, d)
        local_path = ctxt.fs.join(local_base, d)
        # check that the directory exists locally
        if d in _names:
            _names.remove(d)
            state = FileState.SAME
        else:
            state = FileState.PULL

        dirs.append(DirEnt(d, remote_path, local_path, state))

    for f in _files:
        if f['rel_path'] in _names:
            _names.remove(f['rel_path'])

        if f['local_version'] == 0:
            lf = None
        else:
            lf = {
                "version": f['local_version'],
                "size": f['local_size'],
                "mtime": f['local_mtime'],
                "permission": f['local_permission'],
            }

        if f['remote_version'] == 0:
            rf = None
        else:
            rf = {
                "version": f['remote_version'],
                "size": f['remote_size'],
                "mtime": f['remote_mtime'],
                "permission": f['remote_permission'],
            }

        remote_path = posixpath.join(remote_base, f['rel_path'])
        local_path = ctxt.fs.join(local_base, f['rel_path'])

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

        files.append(FileEnt(remote_path, local_path, lf, rf, af))

    for n in _names:
        remote_path = posixpath.join(remote_base, n)
        local_path = ctxt.fs.join(local_base, n)
        record = ctxt.fs.file_info(local_path)

        if n in blacklist:
            continue

        if record.isDir:
            dirs.append(DirEnt(n, remote_path, local_path, FileState.PUSH))
        else:
            af = {
                "version": record.version,
                "size": record.size,
                "mtime": record.mtime,
                "permission": record.permission,
            }
            files.append(FileEnt(remote_path, local_path, None, None, af))

    return CheckResult(remote_base, dirs, files)

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
            }

        ent = FileEnt(remote_path, local_path, lf, rf, af)
    else:
        ent = FileEnt(remote_path, local_path, None, None, af)

    return ent

def _status_dir_impl(ctxt, remote_dir, local_dir, recursive, blacklist):
    # TODO: move recursive to the ctxt
    blacklist = get_blacklist(local_dir, blacklist)

    result = _check(ctxt, remote_dir, local_dir, blacklist)

    ents = list(result.dirs) + list(result.files)

    for ent in sorted(ents, key=lambda x: x.name()):

        if isinstance(ent, DirEnt):

            state = ent.state()
            sym = FileState.symbol(state)
            path = ctxt.fs.relpath(ent.local_base, ctxt.current_local_base)

            if ctxt.verbose:
                print("d%s %s %s/" % (sym, " " * 37, path))
            else:
                print("d%s %s/" % (sym, path))

            if recursive:
                rbase = posixpath.join(remote_dir, ent.name())
                lbase = ctxt.fs.join(local_dir, ent.name())
                _status_dir_impl(ctxt, rbase, lbase, recursive, blacklist)
        else:
            state = ent.state().split(':')[0]
            sym = FileState.symbol(state)
            path = ctxt.fs.relpath(ent.local_path, ctxt.current_local_base)
            if ctxt.verbose:
                print("f%s %s %s" % (sym, ent.stat(), path))
            else:
                print("f%s %s" % (sym, path))
            # in testing, it can be useful to see lf/rf/af state
            if ctxt.verbose > 1:
                print(ent.data())

def _status_file_impl(ctxt, relpath, abspath):

    ent = _check_file(ctxt, relpath, abspath)
    state = ent.state().split(':')[0]
    sym = FileState.symbol(state)
    path = ctxt.fs.relpath(ent.local_path, ctxt.current_local_base)
    if ctxt.verbose:
        print("f%s %s %s" % (sym, ent.stat(), path))
    else:
        print("f%s %s" % (sym, path))
    # in testing, it can be useful to see lf/rf/af state
    if ctxt.verbose > 1:
        print(ent.data())

def _sync_file(ctxt, relpath, abspath, push=False, pull=False, force=False, blacklist=None):

    ent = _check_file(ctxt, relpath, abspath)

    if ent.af is None and ent.rf is None and ent.lf is None:
        sys.stderr.write("not found: %s\n" % ent.remote_path)
        return

    _sync_file_impl(ctxt, ent, push, pull, force, blacklist)

def _sync_file_impl(ctxt, ent, push=False, pull=False, force=False, blacklist=None):

    state = ent.state().split(':')[0]
    sym = FileState.symbol(state)

    if blacklist and ent.name() in blacklist:
        if not force:
            return

    if FileState.SAME == state:
        pass
    elif (FileState.PUSH == state and push) or \
       (FileState.DELETE_REMOTE == state and not pull and push) or \
       (FileState.CONFLICT_MODIFIED == state and not pull and push) or \
       (FileState.CONFLICT_CREATED == state and not pull and push) or \
       (FileState.CONFLICT_VERSION == state and not pull and push):

        if FileState.PUSH != state and not force:
            print("%s is in a conflict state." % ent.remote_path)

        # next version is 1 + current version

        # todo:
        #    server should reject if the version is less than expected
        #    server response should include new version
        #    force flag to disable server side version check
        #    if only perm_ changed, send a metadata update instead
        version = ent.af['version']
        if ent.lf is not None:
            version = max(ent.lf['version'], version)
        ent.af['version'] = version + 1

        mtime = ent.af['mtime']
        perm_ = ent.af['permission']
        f = ProgressFileReaderWrapper(ctxt.fs, ent.local_path, ent.remote_path)
        response = ctxt.client.files_upload(ctxt.root, ent.remote_path, f,
            mtime=mtime, permission=perm_)

        if response.status_code == 409:
            raise Exception("local database out of date. fetch first")

        record = RecordBuilder().local(**ent.af).remote(**ent.af).build()
        ctxt.storageDao.upsert(ent.remote_path, record)
    elif (FileState.PULL == state and pull) or \
       (FileState.DELETE_LOCAL == state and pull and not push) or \
       (FileState.CONFLICT_MODIFIED == state and pull and not push) or \
       (FileState.CONFLICT_CREATED == state and pull and not push) or \
       (FileState.CONFLICT_VERSION == state and pull and not push):

        if FileState.PULL != state and not force:
            print("%s is in a conflict state." % ent.remote_path)

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

        print("pull: %s" % (ent.remote_path))
        response = ctxt.client.files_get_path(ctxt.root, ent.remote_path, stream=True)
        rv = int(response.headers['X-YUE-VERSION'])
        rp = int(response.headers['X-YUE-PERMISSION'])
        rm = int(response.headers['X-YUE-MTIME'])
        if ent.rf['version'] != rv or \
           ent.rf['permission'] != rp or \
           ent.rf['mtime'] != rm:
            raise Exception("local database out of date. fetch first")

        dpath = ctxt.fs.split(ent.local_path)[0]
        if not ctxt.fs.exists(dpath):
            ctxt.fs.makedirs(dpath)

        bytes_written = 0
        with ctxt.fs.open(ent.local_path, "wb") as wb:
            for chunk in response.stream():
                bytes_written += len(chunk)
                wb.write(chunk)

        ctxt.fs.set_mtime(ent.local_path, ent.rf['mtime'])
        record = RecordBuilder().local(**ent.rf).remote(**ent.rf).build()
        ctxt.storageDao.update(ent.remote_path, record)
    elif FileState.ERROR == state:
        print("error %s" % ent.remote_path)
    elif FileState.CONFLICT_MODIFIED == state:
        pass
    elif FileState.CONFLICT_CREATED == state:
        pass
    elif FileState.CONFLICT_VERSION == state:
        pass
    elif FileState.DELETE_BOTH == state:
        ctxt.storageDao.remove(ent.remote_path)
    elif FileState.DELETE_REMOTE == state and pull:
        ctxt.fs.remove(ent.local_path)
        ctxt.storageDao.remove(ent.remote_path)
    elif FileState.DELETE_LOCAL == state and push:
        ctxt.client.files_delete(ctxt.root, ent.remote_path)
        ctxt.storageDao.remove(ent.remote_path)
    else:
        print("unknown %s" % ent.remote_path)

def _sync_impl(ctxt, paths, push=False, pull=False, force=False, recursive=False, blacklist=None):

    for dent in paths:

        if (ctxt.storageDao.isDir(dent.remote_base)) or (
           ctxt.fs.exists(dent.local_base) and ctxt.fs.isdir(dent.local_base)):

            result = _check(ctxt, dent.remote_base, dent.local_base)

            for fent in result.files:
                _sync_file_impl(ctxt, fent, push, pull, force, blacklist)

            if recursive:
                _sync_impl(ctxt, result.dirs, push, pull,
                    force, recursive, blacklist)

        else:
            # todo: load blacklist from directory containing this file
            #   only push if force is given
            _sync_file(ctxt, dent.remote_base, dent.local_base,
                push, pull, force, blacklist)

def _sync_get_file(ctxt, rpath, lpath):

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

def _sync_put_file(ctxt, lpath, rpath):

    record = ctxt.fs.file_info(local_path)

    f = ProgressFileReaderWrapper(ctxt.fs, lpath, rpath)
    response = ctxt.client.files_upload(ctxt.root, rpath, f,
        mtime=record.mtime, permission=record.permission)

    if response.status_code == 409:
        raise Exception("local database out of date. fetch first")

    if response.status_code > 201:
        raise Exception(response.text)

def _copy_impl(client, fs, src, dst):
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
            raise Exception("invalid path: %s" % dst)

        response = client.files_get_path(root, remote_path, stream=True)
        with fs.open(dst, "wb") as wb:
            for chunk in response.stream():
                wb.write(chunk)

    elif dst.startswith(tag):
        root, remote_path = dst[len(tag):].split("/", 1)

        if src.startswith(tag) or not os.access(src, os.R_OK):
            raise Exception("invalid path: %s" % src)

        info = fs.file_info(src)

        f = ProgressFileReaderWrapper(fs, src, remote_path)
        response = client.files_upload(root, remote_path, f,
            mtime=info.mtime, permission=info.permission)

    else:
        raise Exception("invalid source and destiniation path")

def _list_impl(client, root, path):
    """
    list contents of a remote directory
    """

    response = client.files_get_path(root, path, list=True)

    if response.status_code == 404:
        sys.stderr.write("not found: %s\n" % path)
        sys.exit(1)

    elif response.headers['content-type'] != "application/json":
        raise Exception("Server responded with unexpected type: %s" %
            response.headers['content-type'])
    else:
        data = response.json()['result']

        for dirname in sorted(data['directories']):
            sys.stdout.write("%s%s/\n" % (" " * (41), dirname))

        for item in sorted(data['files'], key=lambda item: item['name']):

            fvers = "%3d" % item['version']
            fperm = oct(item.get('permission', 0))[2:].zfill(3)
            ftime = time.localtime(item['mtime'])
            fdate = time.strftime('%Y-%m-%d %H:%M:%S', ftime)

            sys.stdout.write("%s %s %12d %s %s\n" % (
                fvers, fdate, int(item['size']), fperm, item['name']))

def _parse_path_args(fs, remote_base, local_base, args_paths):

    paths = []

    for path in args_paths:
        #if not fs.exists(path):
        #    raise FileNotFoundError(path)
        if not os.path.isabs(path):
            abspath = os.path.normpath(os.path.join(os.getcwd(), path))
        else:
            abspath = path

        if not abspath.startswith(local_base):
            raise FileNotFoundError("path spec does not match")

        relpath = os.path.relpath(path, local_base)
        if relpath == ".":
            relpath = ""
        relpath = posixpath.join(remote_base, relpath)

        name = fs.split(abspath)[1]
        paths.append(DirEnt(name, relpath, abspath))

    paths.sort(key=lambda x: x.local_base)

    return paths

def cli_roots(args):

    ctxt = get_ctxt(os.getcwd())

    client = connect(args.hostname, args.username, args.password)

    response = client.files_get_roots()

    roots = response.json()['result']

    for root in roots:
        print(root)

def cli_init(args):

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

    #TODO: pwd should be empty

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

    storageDao = LocalStoragDao(db, db.tables)

    fs = FileSystem()

    ctxt = SyncContext(client, storageDao, fs,
        args.root, args.remote_base, args.local_base)

    _fetch(ctxt)

def cli_fetch(args):

    ctxt = get_ctxt(os.getcwd())

    _fetch(ctxt)

def cli_status(args):

    ctxt = get_ctxt(os.getcwd())
    ctxt.verbose = args.verbose

    # ---

    paths = _parse_path_args(ctxt.fs, ctxt.remote_base, ctxt.local_base, args.paths)

    first = True
    for dent in paths:

        if not first:
            print("")

        if os.path.isdir(dent.local_base):
            if "" != dent.remote_base or len(paths) > 1:
                print("%s/" % dent.local_base)

            _status_dir_impl(ctxt, dent.remote_base, dent.local_base,
                args.recursion, ctxt.blacklist)
        else:

            _status_file_impl(ctxt, dent.remote_base, dent.local_base)

        first = False
    end = time.time()
    # print(end - start)
    return

def cli_sync(args):

    ctxt = get_ctxt(os.getcwd())

    paths = _parse_path_args(ctxt.fs, ctxt.remote_base, ctxt.local_base, args.paths)

    _sync_impl(ctxt, paths, push=args.push, pull=args.pull,
        force=args.force, recursive=args.recursion, blacklist=ctxt.blacklist)

def cli_get(args):

    ctxt = get_ctxt(os.getcwd())

    args.local_path = os.path.abspath(args.local_path)

    _sync_get_file(ctxt, args.remote_path, args.local_path)

def cli_put(args):

    ctxt = get_ctxt(os.getcwd())

    _sync_put_file(ctxt, args.local_path, args.remote_path)

def cli_info(args):

    ctxt = get_ctxt(os.getcwd())

    response = ctxt.client.files_quota()

    obj = response.json()['result']

    print("file_count: %d" % obj['nfiles'])
    print("usage: %.1f MB" % (obj['nbytes'] / 1024 / 1024))
    print("capacity: %.1f MB" % (obj['quota'] / 1024 / 1024))

def cli_copy(args):

    ctxt = get_ctxt(os.getcwd())

    _copy_impl(ctxt.client, ctxt.fs, args.src, args.dst)

def cli_list(args):

    ctxt = get_ctxt(os.getcwd())

    root = args.root or ctxt.root
    _list_impl(ctxt.client, root, args.path)

def main():

    parser = argparse.ArgumentParser(description='sync utility')
    subparsers = parser.add_subparsers()

    ###########################################################################
    # Roots

    parser_roots = subparsers.add_parser('roots',
        help="list available buckets which can be accessed")
    parser_roots.set_defaults(func=cli_roots)

    parser_roots.add_argument('-u', '--username',
        default=None)

    parser_roots.add_argument('-p', '--password',
        default=None)

    parser_roots.add_argument('hostname')

    ###########################################################################
    # Init

    parser_init = subparsers.add_parser('init',
        help="initialize a directory")
    parser_init.set_defaults(func=cli_init)

    parser_init.add_argument('-u', '--username',
        default=None)

    parser_init.add_argument('-p', '--password',
        default=None)

    parser_init.add_argument('-b', '--local_base', dest="local_base",
        default=os.getcwd())
    parser_init.add_argument('-r', '--remote_base', dest="remote_base",
        default="")

    parser_init.add_argument('hostname')
    parser_init.add_argument('root', nargs="?", default="default")

    ###########################################################################
    # Info

    parser_fetch = subparsers.add_parser('info',
        help="view user information")
    parser_fetch.set_defaults(func=cli_info)

    ###########################################################################
    # Fetch

    parser_fetch = subparsers.add_parser('fetch',
        help="update the local database")
    parser_fetch.set_defaults(func=cli_fetch)

    ###########################################################################
    # Status

    parser_status = subparsers.add_parser('status',
        help="check for changes")
    parser_status.set_defaults(func=cli_status)

    parser_status.add_argument("-v", "--verbose", default=0,
        action="count",
        help="show detailed information")

    parser_status.add_argument("-r", "--recursion",
        action="store_true",
        help="check the status for sub directories")

    parser_status.add_argument("paths", nargs="*",
        help="list of paths to check the status on")

    ###########################################################################
    # Sync

    parser_sync = subparsers.add_parser('sync',
        help="sync local and remote files")
    parser_sync.set_defaults(func=cli_sync)
    parser_sync.set_defaults(push=True)
    parser_sync.set_defaults(pull=True)

    parser_sync.add_argument('-f', "--force",
        action="store_true",
        help="overwrite conflicts")

    parser_sync.add_argument("-r", "--recursion",
        action="store_true",
        help="check the status for sub directories")

    parser_sync.add_argument("paths", nargs="*",
        help="list of paths to check the status on")

    ###########################################################################
    # Get

    parser_get = subparsers.add_parser('get',
        help="copy a remote file locally")
    parser_get.set_defaults(func=cli_get)

    parser_get.add_argument("remote_path",
        help="path to a remote file")

    parser_get.add_argument("local_path", default=None, nargs="?",
        help="path to a local file")

    ###########################################################################
    # Put

    parser_put = subparsers.add_parser('put',
        help="copy a local file to remote")
    parser_put.set_defaults(func=cli_put)

    parser_put.add_argument("local_path",
        help="path to a local file")

    parser_put.add_argument("remote_path",
        help="path to a remote file")

    ###########################################################################
    # Pull

    parser_pull = subparsers.add_parser('pull',
        help="retrieve remote files")
    parser_pull.set_defaults(func=cli_sync)
    parser_pull.set_defaults(push=False)
    parser_pull.set_defaults(pull=True)

    parser_pull.add_argument('-f', "--force",
        action="store_true",
        help="overwrite conflicts")

    parser_pull.add_argument("-r", "--recursion",
        action="store_true",
        help="check the status for sub directories")

    parser_pull.add_argument("paths", nargs="*",
        help="list of paths to check the status on")

    ###########################################################################
    # Push

    parser_push = subparsers.add_parser('push',
        help="push local files")
    parser_push.set_defaults(func=cli_sync)
    parser_push.set_defaults(push=True)
    parser_push.set_defaults(pull=False)

    parser_push.add_argument('-f', "--force",
        action="store_true",
        help="overwrite conflicts")

    parser_push.add_argument("-r", "--recursion",
        action="store_true",
        help="check the status for sub directories")

    parser_push.add_argument("paths", nargs="*",
        help="list of paths to check the status on")

    ###########################################################################
    # Copy

    parser_copy = subparsers.add_parser('copy', aliases=['cp'],
        help="copy a file up or down")
    parser_copy.set_defaults(func=cli_copy)

    parser_copy.add_argument('src', help="source file to copy")
    parser_copy.add_argument('dst', help="destination path")

    ###########################################################################
    # List

    parser_list = subparsers.add_parser('list', aliases=['ls'],
        help="list contents of a remote directory")
    parser_list.set_defaults(func=cli_list)

    parser_list.add_argument("--root", default=None,
        help="file system root to list")

    parser_list.add_argument('path', nargs="?", default="", help="relative remote path")
    ###########################################################################
    args = parser.parse_args()

    if hasattr(args, "username"):
        if args.username is None:
            args.password = input("username:")

        if args.password is None and ':' in args.username:
            args.username, args.password = args.username.split(':', 1)
        elif args.password is None:
            args.password = input("password:")

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

