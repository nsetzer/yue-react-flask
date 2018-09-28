#! python $this init -u admin:admin localhost:4200

"""
todo: create a stat cache to avoid making os calls for the same file
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

class LocalStoragDao(object):
    def __init__(self, db, dbtables):
        super(LocalStoragDao, self).__init__()
        self.db = db
        self.dbtables = dbtables

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

def get_cfg(directory):

    local_base = directory

    relpath = ""
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
    userdata['local_base'] = local_base
    userdata['default_remote_base'] = userdata['remote_base']
    userdata['remote_base'] = posixpath.join(userdata['remote_base'], relpath)

    return userdata

def get_mgr(directory, dryrun=False):

    userdata = get_cfg(directory)

    client = connect(userdata['hostname'],
        userdata['username'], userdata['password'])

    mgr = SyncManager(client, userdata['root'], userdata['cfgdir'], dryrun)
    mgr.setDirectory(userdata['local_base'])

    return mgr

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
            sym = "= "
        if FileState.PUSH == state:
            sym = "> "
        if FileState.PULL == state:
            sym = "< "
        if FileState.ERROR == state:
            sym = "x "
        if FileState.CONFLICT_MODIFIED == state:
            sym = "cm"
        if FileState.CONFLICT_CREATED == state:
            sym = "cc"
        if FileState.CONFLICT_VERSION == state:
            sym = "cv"
        if FileState.DELETE_BOTH == state:
            sym = "d="
        if FileState.DELETE_REMOTE == state:
            sym = "d<"
        if FileState.DELETE_LOCAL == state:
            sym = "d>"
        return sym

class DirEnt(object):
    """docstring for DirEnt"""
    def __init__(self, name, remote_base, local_base):
        super(DirEnt, self).__init__()
        self.remote_base = remote_base
        self.local_base = local_base
        self._name = name

    def state(self):
        if self.remote_base is None and self.local_base is None:
            return FileState.ERROR
        elif self.remote_base is None and self.local_base is not None:
            return FileState.PUSH
        elif self.remote_base is not None and self.local_base is None:
            return FileState.PULL
        elif self.remote_base is not None and self.local_base is not None:
            return FileState.SAME

    def name(self):
        return self._name

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

        # 7 : delete local
        elif lfe and rfe and afe:
            return _check_threeway_compare(self.lf, self.rf, self.af)

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

def _check(storageDao, fs, root, remote_base, local_base):

    if remote_base and not remote_base.endswith("/"):
        remote_base += "/"

    dirs = []
    files = []
    _dirs, _files = storageDao.listdir(remote_base)
    # TODO: looks like memfs impl for exists is broken for dirs
    if not fs.islocal(local_base) or fs.exists(local_base):
        _names = set(fs.listdir(local_base))
    else:
        _names = set()

    for d in _dirs:
        remote_path = posixpath.join(remote_base, d)
        if d in _names:
            _names.remove(d)
            local_path = fs.join(local_base, d)
        else:
            local_path = None
        dirs.append(DirEnt(d, remote_path, local_path))

    for f in _files:

        if f['rel_path'] in _names:
            _names.remove(f['rel_path'])

        remote_path = posixpath.join(remote_base, f['rel_path'])
        local_path = fs.join(local_base, f['rel_path'])

        lf = {
            "version": f['local_version'],
            "size": f['local_size'],
            "mtime": f['local_mtime'],
            "permission": f['local_permission'],
        }

        if lf['version'] == 0:
            lf = None

        rf = {
            "version": f['remote_version'],
            "size":    f['remote_size'],
            "mtime":   f['remote_mtime'],
            "permission": f['remote_permission'],
        }

        if rf['version'] == 0:
            rf = None

        try:
            record = fs.file_info(local_path)

            af = {
                "version": record.version,
                "size": record.size,
                "mtime": record.mtime,
                "permission": record.permission,
            }
        except FileNotFoundError:
            af = None
        rel_path = remote_path
        files.append(FileEnt(remote_path, local_path, lf, rf, af))

    for n in _names:
        remote_path = posixpath.join(remote_base, n)
        local_path = fs.join(local_base, n)
        record = fs.file_info(local_path)

        if record.isDir:
            dirs.append(DirEnt(n, None, local_path))
        else:
            af = {
                "version": record.version,
                "size": record.size,
                "mtime": record.mtime,
                "permission": record.permission,
            }
            files.append(FileEnt(remote_path, local_path, None, None, af))

    return CheckResult(remote_base, dirs, files)

def _check_file(storageDao, fs, root, remote_path, local_path):

    item = storageDao.file_info(remote_path)

    try:
        record = fs.file_info(local_path)

        af = {
            "version": record.version,
            "size": record.size,
            "mtime": record.mtime,
            "permission": record.permission,
        }
    except FileNotFoundError:
        af = None

    if item is not None:
        lf = {
            "version": item['local_version'],
            "size": item['local_size'],
            "mtime": item['local_mtime'],
            "permission": item['local_permission'],
        }

        if lf['version'] == 0:
            lf = None

        rf = {
            "version": item['remote_version'],
            "size":    item['remote_size'],
            "mtime":   item['remote_mtime'],
            "permission": item['remote_permission'],
        }

        if rf['version'] == 0:
            rf = None

        ent = FileEnt(remote_path, local_path, lf, rf, af)
    else:

        ent = FileEnt(remote_path, local_path, None, None, af)

    return ent

def _check_threeway_compare(lf, rf, af):
    # given three data-dicts representing a file
    # for local, remote, and actual state
    # determines whether the file should be pushed or pulled to sync

    def samefile(a, b):
        b = a['mtime'] == b['mtime'] and \
            a['size'] == b['size'] and \
            a['permission'] == b['permission']
        return b

    if lf['version'] < rf['version']:
        if samefile(lf, af):
            return FileState.PULL + ":3a"
        else:
            return FileState.CONFLICT_MODIFIED + ":3a"
    elif lf['version'] > rf['version']:
        return FileState.CONFLICT_VERSION + ":3a"
    else:
        if samefile(lf, af):
            # file has not been changed locally
            if samefile(lf, rf):
                # file has not been changed on remote
                return FileState.SAME + ":3a"
            else:
                # locally is the same but remote is different
                # this is a weird state
                return FileState.CONFLICT_VERSION + ":3b"
        else:
            # file has changed locally
            if samefile(lf, rf):
                # local is newer
                return FileState.PUSH + ":3a"
            else:
                # both modified
                return FileState.CONFLICT_MODIFIED + ":3b"

        return FileState.ERROR + ":3b"

def _status_dir_impl(storageDao, fs, root,
  remote_base, remote_dir, local_base, local_dir, recursive):

    result = _check(storageDao, fs, root, remote_dir, local_dir)

    ents = list(result.dirs) + list(result.files)

    for ent in sorted(ents, key=lambda x: x.name()):

        if isinstance(ent, DirEnt):

            state = ent.state()
            sym = FileState.symbol(state)
            if ent.local_base:
                path = fs.relpath(ent.local_base, local_base)
            else:
                path = posixpath.relpath(ent.remote_base, remote_base)
            print("d%s %s/" % (sym, path))

            if recursive and state != FileState.PULL:
                rbase = posixpath.join(remote_base, ent.name())
                lbase = fs.join(local_base, ent.name())
                _status_dir_impl(storageDao, fs, root,
                    remote_base, rbase, local_base, lbase, recursive)
        else:

            state = ent.state().split(':')[0]
            sym = FileState.symbol(state)
            path = fs.relpath(ent.local_path, local_base)
            data = ent.data()
            print("f%s %s\n  %s" % (sym, path, data))

def _status_file_impl(storageDao, fs, root, local_base, relpath, abspath):

    ent = _check_file(storageDao, fs, root, relpath, abspath)
    state = ent.state().split(':')[0]
    sym = FileState.symbol(state)
    path = fs.relpath(ent.local_path, local_base)
    print("f%s %s" % (sym, path))

def _sync_file_impl(client, storageDao, fs, root, local_base, relpath,
    abspath, push=False, pull=False, force=False):

    ent = _check_file(storageDao, fs, root, relpath, abspath)

    state = ent.state().split(':')[0]
    sym = FileState.symbol(state)
    if FileState.SAME == state:
        print("nothing to do")
    if FileState.PUSH == state and push:
        print("pull %s" % relpath)

        # next version is 1 + current version

        # todo:
        #    server should reject if the version is less than expected
        #    server response should include new version
        #    force flag to disable server side version check
        #    if only perm_ changed, send a metadata update instead
        version = ent.af['version']
        if ent.lf is not None:
            version = max(ent.lf['version'], version)
        af['version'] = version + 1

        mtime = ent.af['mtime']
        perm_ = ent.af['permission']
        with fs.open(abspath, "rb") as rb:
            response = client.files_upload(root, relpath, rb,
                mtime=mtime, permission=perm_)

        record = RecordBuilder().local(**ent.af).remote(**ent.af).build()
        storageDao.upsert(relpath, record)
    elif (FileState.PULL == state and pull) or \
       (FileState.DELETE_LOCAL == state and pull and not push):
        print("pull %s" % relpath)

        # todo:
        #   server should return error if requested version does not match
        #   the current version on the server. (user must fetch first)
        #   if only a perm_ change, request metadata instead of file

        version = ent.rf['version']

        response = client.files_get_path(root, relpath, stream=True)
        with open(abspath, "wb") as wb:
            for chunk in response.stream():
                wb.write(chunk)

        fs.set_mtime(abspath, ent.rf['mtime'])
        record = RecordBuilder().local(**ent.rf).build()
        storageDao.update(relpath, record)
    elif FileState.ERROR == state:
        print("error %s" % relpath)
    elif FileState.CONFLICT_MODIFIED == state:
        print("conflict %s" % relpath)
    elif FileState.CONFLICT_CREATED == state:
        print("conflict %s" % relpath)
    elif FileState.CONFLICT_VERSION == state:
        print("conflict %s" % relpath)
    elif FileState.DELETE_BOTH == state:
        print("delete %s" % relpath)
    elif FileState.DELETE_REMOTE == state:
        print("delete %s" % relpath)
    elif FileState.DELETE_LOCAL == state:
        print("delete %s" % relpath)

def _parse_path_args(fs, local_base, args_paths):

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
        paths.append((abspath, relpath))

    paths.sort()

    return paths

def cli_init(args):

    #TODO: pwd should be empty
    cfgdir = os.path.join(args.local_base, ".yue")
    dbpath = os.path.abspath(os.path.join(cfgdir, "database.sqlite"))
    userpath = os.path.abspath(os.path.join(cfgdir, "userdata.json"))
    if not os.path.exists(cfgdir):
        os.makedirs(cfgdir)

    dburl = "sqlite:///" + dbpath
    db = db_connect(dburl)
    db.create_all()

    if args.username is None:
        args.password = input("username:")
    if args.password is None and ':' in args.username:
        args.username, args.password = args.username.split(':', 1)
    elif args.password is None:
        args.password = input("password:")

    cm = CryptoManager()

    private_key, public_key = cm.generate_key(cfgdir, "rsa", 2048)

    enc_password = cm.encrypt64(public_key, args.password.encode("utf-8"))
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

def cli_fetch(args):

    userdata = get_cfg(os.getcwd())

    db = db_connect(userdata['dburl'])

    client = connect(userdata['hostname'],
        userdata['username'], userdata['password'])

    storageDao = LocalStoragDao(db, db.tables)

    storageDao.clearRemote(False)

    page = 0
    limit = 500
    while True:
        params = {'limit': limit, 'page': page}
        response = client.files_get_index(
            userdata['root'], userdata['default_remote_base'], **params)
        if response.status_code != 200:
            sys.stderr.write("fetch error...")
            return

        files = response.json()['result']
        for f in files:
            record = {
                "remote_size": f['size'],
                "remote_mtime": f['mtime'],
                "remote_permission": f['permission'],
                "remote_version": f['version']
            }
            print(record)
            storageDao.upsert(f['path'], record, commit=False)
            print(f['path'])

        page += 1
        if len(files) != limit:
            break

    db.session.commit()

def cli_status(args):

    start = time.time()
    if len(args.paths) == 0:
        args.paths.append(os.getcwd())

    userdata = get_cfg(os.getcwd())

    client = connect(userdata['hostname'],
        userdata['username'], userdata['password'])

    db = db_connect(userdata['dburl'])

    fs = FileSystem()

    storageDao = LocalStoragDao(db, db.tables)

    # ---

    paths = _parse_path_args(fs, userdata['local_base'], args.paths)

    first = True
    for abspath, relpath in paths:

        if not first:
            print("")

        if os.path.isdir(abspath):
            if "" != relpath or len(paths) > 1:
                print("%s/" % abspath)

            _status_dir_impl(storageDao, fs, userdata['root'],
                relpath, relpath,
                abspath, abspath, args.recursion)
        else:

            _status_file_impl(storageDao, fs, userdata['root'],
                os.getcwd(), relpath, abspath)

        first = False
    end = time.time()
    # print(end - start)
    return

def cli_pull(args):

    start = time.time()
    if len(args.paths) == 0:
        args.paths.append(os.getcwd())

    userdata = get_cfg(os.getcwd())

    client = connect(userdata['hostname'],
        userdata['username'], userdata['password'])

    db = db_connect(userdata['dburl'])

    fs = FileSystem()

    storageDao = LocalStoragDao(db, db.tables)

    # ---

    paths = _parse_path_args(fs, userdata['local_base'], args.paths)

    first = True
    for abspath, relpath in paths:

        if not first:
            print("")

        #if os.path.isdir(abspath):
        #    if "" != relpath or len(paths) > 1:
        #        print("%s/" % abspath)
        #    #_status_dir_impl(storageDao, fs, userdata['root'],
        #    #    relpath, relpath,
        #    #    abspath, abspath, args.recursion)
        #else:

        _sync_file_impl(client, storageDao, fs, userdata['root'],
            os.getcwd(), relpath, abspath, pull=True, force=args.force)

        first = False
    end = time.time()
    # print(end - start)
    return

def cli_push(args):

    start = time.time()
    if len(args.paths) == 0:
        args.paths.append(os.getcwd())

    userdata = get_cfg(os.getcwd())

    client = connect(userdata['hostname'],
        userdata['username'], userdata['password'])

    db = db_connect(userdata['dburl'])

    fs = FileSystem()

    storageDao = LocalStoragDao(db, db.tables)

    # ---

    paths = _parse_path_args(fs, userdata['local_base'], args.paths)

    first = True
    for abspath, relpath in paths:

        if not first:
            print("")

        if os.path.isdir(abspath):
            if "" != relpath or len(paths) > 1:
                print("%s/" % abspath)

            #_status_dir_impl(storageDao, fs, userdata['root'],
            #    relpath, relpath,
            #    abspath, abspath, args.recursion)
        else:

            _sync_file_impl(client, storageDao, fs, userdata['root'],
                os.getcwd(), relpath, abspath, push=True, force=args.force)

        first = False
    end = time.time()
    # print(end - start)
    return

def main():

    parser = argparse.ArgumentParser(description='sync utility')
    subparsers = parser.add_subparsers()

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
    # Fetch

    parser_fetch = subparsers.add_parser('fetch',
        help="update the local database")
    parser_fetch.set_defaults(func=cli_fetch)

    ###########################################################################
    # status

    parser_status = subparsers.add_parser('status',
        help="check for changes")
    parser_status.set_defaults(func=cli_status)

    parser_status.add_argument("-r", "--recursion",
        action="store_true",
        help="check the status for sub directories")

    parser_status.add_argument("paths", nargs="*",
        help="list of paths to check the status on")

    ###########################################################################
    # Pull

    parser_pull = subparsers.add_parser('pull',
        help="retrieve remote files")
    parser_pull.set_defaults(func=cli_pull)

    parser_pull.add_argument("--force",
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
    parser_push.set_defaults(func=cli_push)

    parser_push.add_argument("--force",
        action="store_true",
        help="overwrite conflicts")

    parser_push.add_argument("-r", "--recursion",
        action="store_true",
        help="check the status for sub directories")

    parser_push.add_argument("paths", nargs="*",
        help="list of paths to check the status on")

    ###########################################################################
    args = parser.parse_args()

    FORMAT = '%(levelname)-8s - %(message)s'
    logging.basicConfig(level=logging.INFO, format=FORMAT)

    if not hasattr(args, 'func'):
        parser.print_help()
    else:
        args.func(args)

if __name__ == '__main__':
    main()

