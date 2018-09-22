

from sqlalchemy.orm import relationship
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import func
from sqlalchemy import and_, or_, not_, select, column, update, insert, delete

from sqlalchemy.sql.expression import bindparam
from .search import SearchGrammar, ParseError, Rule
from .filesys.filesys import FileSystem
from .filesys.util import FileRecord
from .exception import BackendException

import os
import sys
import datetime, time
import uuid
import posixpath

# taken from werkzeug.util.secure_file
_windows_device_files = ('CON', 'AUX', 'COM1', 'COM2', 'COM3', 'COM4', 'LPT1',
                         'LPT2', 'LPT3', 'PRN', 'NUL')

class StorageException(BackendException):
    pass

class StorageNotFoundException(StorageException):
    HTTP_STATUS = 404

class StorageDao(object):
    """

    a file path takes on different meaning if it ends with a delimiter.
    A path which does not end with a delimiter is assumed to be an
    absolute file path. Otherwise it is consumed as a path prefix, which
    means it
    """
    def __init__(self, db, dbtables):
        super(StorageDao, self).__init__()
        self.db = db
        self.dbtables = dbtables
        self.fs = FileSystem()

    # FileSystem util

    def localPathToNormalPath(self, local_path):
        """ convert an absolute local path (on the local file system)
        into a normalized path which can be stored in the database

        this prefix the path with a scheme (file://)
        on windows this will also convert back slash (\\) to forward slash (/)

        this is purely a path computation
        """

        if not local_path.startswith("file://"):
            local_path = "file://" + local_path

        if sys.platform == 'win32':
            local_path.replace("\\", "/")

        return local_path

    def NormalPathTolocalPath(self, normal_path):
        """
        this is purely a path computation
        """

        _, path = self.splitScheme(normal_path)

        if sys.platform == 'win32':
            path.replace("/", "\\")

        return path

    def splitScheme(self, path):
        scheme = "file://localhost/"
        i = path.find("://")
        if "://" in path:
            i += len("://")
            scheme = path[:i]
            path = path[i:]
        return scheme, path

    # FileSystem Operations

    def insert_path(self, user_id, path):

        name, is_dir, size, mtime = self.fs.file_info()

        return self.insert(user_id, path, size, mtime)

    def insert(self, user_id, path, size, mtime, commit=True):

        # TODO: required?
        #if path.endswith(delimiter):
        #    raise StorageException("invalid directory path")

        record = {
            'user_id': user_id,
            'version': 1,
            'path': path,
            'mtime': mtime,
            'size': size,
        }

        query = self.dbtables.FileSystemStorageTable.insert() \
            .values(record)

        ex = None
        try:
            self.db.session.execute(query)

            if commit:
                self.db.session.commit()
        except IntegrityError as e:
            ex = StorageException("%s" % e.args[0])

        if ex is not None:
            raise ex

    def update(self, user_id, path, size=None, mtime=None, commit=True):

        record = {
            'version': self.dbtables.FileSystemStorageTable.c.version + 1,
        }

        if mtime is not None:
            record['mtime'] = mtime

        if size is not None:
            record['size'] = size

        query = update(self.dbtables.FileSystemStorageTable) \
            .values(record) \
            .where(
                and_(self.dbtables.FileSystemStorageTable.c.user_id == user_id,
                     self.dbtables.FileSystemStorageTable.c.path == path,
                     ))

        self.db.session.execute(query)

        if commit:
            self.db.session.commit()

    def rename(self, user_id, src_path, dst_path, commit=True):

        record = {
            'path': dst_path,
        }

        query = update(self.dbtables.FileSystemStorageTable) \
            .values(record) \
            .where(
                and_(self.dbtables.FileSystemStorageTable.c.user_id == user_id,
                     self.dbtables.FileSystemStorageTable.c.path == src_path,
                     ))

        ex = None
        try:
            self.db.session.execute(query)

            if commit:
                self.db.session.commit()
        except IntegrityError as e:
            ex = StorageException("%s" % e.args[0])

        if ex is not None:
            raise ex

    def remove(self, user_id, path, commit=True):

        query = delete(self.dbtables.FileSystemStorageTable) \
            .where(
                and_(self.dbtables.FileSystemStorageTable.c.user_id == user_id,
                     self.dbtables.FileSystemStorageTable.c.path == path,
                     ))

        self.db.session.execute(query)

        if commit:
            self.db.session.commit()

    def _item2record(self, item, path_prefix, delimiter):
        item_path = item['path'].replace(path_prefix, "")
        if delimiter in item_path:
            name, _ = item_path.split(delimiter, 1)
            return FileRecord(name, True, 0, 0)
        else:
            return FileRecord(item_path, False, item['size'], item['mtime'])

    def list(self):
        FsTab = self.dbtables.FileSystemStorageTable
        query = select(['*']).select_from(FsTab)

        return self.db.session.execute(query).fetchall()

    def listdir(self, user_id, path_prefix, delimiter='/'):
        # search for persistent objects with prefix, that also do not contain
        # the delimiter

        FsTab = self.dbtables.FileSystemStorageTable

        if not path_prefix.endswith(delimiter):
            raise StorageException("invalid directory path. must end with `%s`" % delimiter)

        where = FsTab.c.path.startswith(bindparam('path', path_prefix))
        where = and_(FsTab.c.user_id == user_id, where)

        query = select(['*']) \
            .select_from(FsTab) \
            .where(where)

        dirs = set()
        count = 0
        for item in self.db.session.execute(query).fetchall():
            rec = self._item2record(item, path_prefix, delimiter)

            if rec.isDir:
                if rec.name not in dirs:
                    dirs.add(rec.name)
                    yield rec
                    count += 1
            else:
                yield rec
                count += 1

        # TODO: this disallows empty directories, which seems
        # to be required in order to support s3, mem
        if count == 0:
            raise StorageNotFoundException("[listdir] not found: %s" % path_prefix)

    def file_info(self, user_id, path_prefix, delimiter='/'):
        FsTab = self.dbtables.FileSystemStorageTable

        scheme, base_path = self.splitScheme(path_prefix)

        if not base_path:
            raise StorageException("empty path component")

        if path_prefix.endswith(delimiter):
            where = FsTab.c.path.startswith(bindparam('path', path_prefix))
            where = and_(FsTab.c.user_id == user_id, where)
            exact = False
        else:
            where = FsTab.c.path == path_prefix
            exact = True

        query = select(['*']) \
            .select_from(FsTab) \
            .where(where).limit(1)

        result = self.db.session.execute(query)
        item = result.fetchone()

        if item is None:
            raise StorageNotFoundException("[file_info] not found: %s" % path_prefix)
        elif exact:
            # an exact match for a file record
            name = path_prefix.split(delimiter)[-1]
            return FileRecord(name, False, item['size'], item['mtime'], item['version'])
        else:
            name = base_path.rstrip(delimiter).split(delimiter)[-1]
            return FileRecord(name, True, 0, 0, 0)

    def rootPath(self, user_id, role_id, root_name):

        FsTab = self.dbtables.FileSystemTable
        FsPermissionTab = self.dbtables.FileSystemPermissionTable

        query = select([column("path"), ]) \
            .select_from(
                FsTab.join(
                    FsPermissionTab,
                    FsTab.c.id == FsPermissionTab.c.file_id,
                    isouter=True)) \
            .where(and_(FsPermissionTab.c.role_id == role_id,
                        FsTab.c.name == root_name))

        result = self.db.session.execute(query)
        item = result.fetchone()

        if item is None:
            raise StorageException(
                "FileSystem %s not defined or permission denied" % root_name)

        # allow substitutions on only the user id, and only on the
        # part of the path stored in the database. this allows
        # for a configuration file to specify a user sandbox
        root_path = item.path.format(user_id=user_id, pwd=os.getcwd())

        return root_path

    def absolutePath(self, user_id, role_id, root_name, rel_path):
        """ compose an absolute file path given a role and named directory base

        For example, a service could be written allowing any user read
        and write access to a directory. the user only knows the path of
        their file, while the service translates that path into:
             $root/$user_id/$filepath/$filename
        this function would be given "$userid/$filepath/$filename" and
        returns the complete path (with $root) if the user is authorized
        to access that file
        """

        if self.fs.isabs(rel_path):
            raise StorageException("path must not be absolute")

        root_path = self.rootPath(user_id, role_id, root_name)

        if not rel_path.strip():
            return root_path

        # sanitize the input string to prevent a user from creating
        # a path that can break out of the root directory taken
        # from the database
        rel_path = rel_path.replace("\\", "/")

        scheme, parts = self.fs.parts(rel_path)
        if any([p in (".", "..") for p in parts]):
            # path must be relative to root_path...
            raise StorageException("relative paths not allowed")

        if any([(not p.strip()) for p in parts]):
            raise StorageException("empty path component")

        if self.fs.islocal(root_path) and os.name == 'nt':
            if any([p in _windows_device_files for p in parts]):
                raise StorageException("invalid windows path name")

        return self.fs.join(root_path, rel_path)

    def userDiskUsage(self, user_id):
        """ returns the number of files and bytes consumed by a user
        """
        columns = [func.count(column("size")), func.sum(column("size"))]
        query = select(columns) \
            .select_from(self.dbtables.FileSystemStorageTable) \
            .where(self.dbtables.FileSystemStorageTable.c.user_id == user_id)
        result = self.db.session.execute(query)
        _count, _sum = result.fetchone()
        return _count, (_sum or 0)

    def userDiskQuota(self, user_id, role_id):
        # todo: set default quota based on role_id, allow for individual
        #       users to exceed that quota, a value of zero is no limit
        return 0
