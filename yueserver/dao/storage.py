

from sqlalchemy.orm import relationship
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, not_, select, column, update, insert, delete

from sqlalchemy.sql.expression import bindparam
from .search import SearchGrammar, ParseError, Rule
from .filesys.filesys import FileSystem
from .filesys.util import FileRecord

import sys
import datetime, time
import uuid
import posixpath

class StorageException(Exception):
    pass

class StorageNotFoundException(StorageException):
    pass

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
        """ convert a local path (on the local file system)
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

        idx = path.index("://")
        scheme = path[:idx]
        path = path[idx + 3:]

        return scheme, path

    # FileSystem CRUD

    def createFileSystem(self, name, path, commit=True):

        query = insert(self.dbtables.FileSystemTable) \
            .values({'name': name, 'path': path})
        result = self.db.session.execute(query)
        if commit:
            self.db.session.commit()
        return result.inserted_primary_key[0]

    def findFileSystemById(self, file_id):
        query = self.dbtables.FileSystemTable.select() \
            .where(self.dbtables.FileSystemTable.c.id == file_id)
        result = self.db.session.execute(query)
        return result.fetchone()

    def findFileSystemByName(self, name):
        query = self.dbtables.FileSystemTable.select() \
            .where(self.dbtables.FileSystemTable.c.name == name)
        result = self.db.session.execute(query)
        return result.fetchone()

    def listFileSystems(self):
        query = self.dbtables.FileSystemTable.select()
        result = self.db.session.execute(query)
        return result.fetchall()

    def removeFileSystem(self, file_id, commit=True):
        # TODO ensure file system is not used for any role

        query = delete(self.dbtables.FileSystemTable) \
            .where(self.dbtables.FileSystemTable.c.id == file_id)
        self.db.session.execute(query)

        if commit:
            self.db.session.commit()

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
            'version': 0,
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

    def listdir(self, user_id, path_prefix, delimiter='/'):
        # search for persistent objects with prefix, that also do not contain
        # the delimiter

        FsTab = self.dbtables.FileSystemStorageTable

        if not path_prefix.endswith(delimiter):
            raise StorageException("invalid directory path")

        where = FsTab.c.path.startswith(bindparam('path', path_prefix))
        where = and_(FsTab.c.user_id == user_id, where)

        query = select(['*']) \
            .select_from(FsTab) \
            .where(where)

        dirs = set()
        for item in self.db.session.execute(query).fetchall():

            rec = self._item2record(item, path_prefix, delimiter)

            if rec.isDir:
                if rec.name not in dirs:
                    dirs.add(rec.name)
                    yield rec
            else:
                yield rec

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
            raise StorageNotFoundException(path_prefix)
        elif exact:
            # an exact match for a file record
            name = path_prefix.split(delimiter)[-1]
            return FileRecord(name, False, item['size'], item['mtime'], item['version'])
        else:
            name = base_path.rstrip(delimiter).split(delimiter)[-1]
            return FileRecord(name, True, 0, 0, 0)
