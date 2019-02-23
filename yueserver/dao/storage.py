

from sqlalchemy.orm import relationship
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import func
from sqlalchemy import and_, or_, not_, select, column, \
    update, insert, delete, asc, desc

from sqlalchemy.sql.expression import bindparam
from .search import SearchGrammar, ParseError, Rule
from .filesys.filesys import FileSystem
from .filesys.util import FileRecord
from .filesys.crypt import cryptkey, decryptkey, recryptkey
from .exception import BackendException
from .util import format_storage_path, hash_password, check_password_hash

import os
import sys
import datetime
import time
import calendar
import uuid
import posixpath
import base64

from functools import lru_cache
from enum import Enum

# taken from werkzeug.util.secure_file
_windows_device_files = {'CON', 'AUX', 'NUL', 'PRN'
    'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM8',
    'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'}

class CryptMode(object):
    """
    A set of encryption modes for files stored by the application
    """
    # none: no encryption is performed
    none = 'none'
    # client: file is encrypted, key is managed by the user client side
    # files are encrypted and decrypted by the client
    # files can only be decrypted by the owner
    # the server (and database) never have access to the decrypted key
    client = 'client'
    # server: file is encrypted, key is managed by the user server side
    # files are encrypted and decrypted by the server
    # files can only be decrypted by the owner
    # man in the middle attacks could determine the encryption key
    server = 'server'
    # system: file is encrypted, key is managed by the application
    # files are encrypted and decrypted by the server
    # files can be decrypted by users other than the file owner
    # the encryption key is compromised if the database is compromised
    system = 'system'

class FileRecord2(object):
    def __init__(self, *args, **kwargs):
        super(FileRecord2, self).__init__()

        self.user_id = None

        self.name = None

        self.file_path = None
        self.storage_path = None
        self.preview_path = None

        self.permission = 0o644
        self.version = 0
        self.size = 0
        self.expired = None
        self.mtime = 0

        self.encryption = None
        self.public_password = None
        self.public = None

        self.isDir = False

        self._update(args, kwargs)

    def _update(self, args, kwargs):

        if len(args) > 0:
            self.file_path = args[0]

        if len(args) > 1:
            self.storage_path = args[1]

        for key, val in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, val)
            else:
                raise KeyError(key)

    def __getitem__(self, key):
        if hasattr(self, key):
            return getattr(self, key)
        else:
            raise KeyError(key)

    @staticmethod
    def fromRow(row):
        pass

def url_uuid_v2():
    """returns a randomly generated unique identifier"""
    b = uuid.uuid4().bytes
    b = base64.b64encode(b, b"-_")
    b = b.replace(b"-", b"AA").replace(b"_", b"AB").replace(b"=", b"")
    return b.decode("utf-8")

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

    def insertFile(self, user_id, fs_id, file_path, data, commit=True):

        # TODO: required?
        # if path.endswith(delimiter):
        #    raise StorageException("invalid path")

        data['user_id'] = user_id
        data['filesystem_id'] = fs_id
        data['file_path'] = file_path

        if 'version' not in data or data['version'] is None:
            data['version'] = 1

        query = self.dbtables.FileSystemStorageTable.insert() \
            .values(data)

        ex = None
        try:
            result = self.db.session.execute(query)

            if commit:
                self.db.session.commit()

        except IntegrityError as e:
            ex = StorageException("%s" % e.args[0])
            ex.original = e

        if ex is not None:
            raise ex

    def updateFile(self, file_id, data, commit=True):
        tab = self.dbtables.FileSystemStorageTable

        data = dict(data)

        if 'user_id' in data:
            del data['user_id']

        if 'version' not in data or data['version'] is None:
            data['version'] = tab.c.version + 1

        query = tab.update() \
            .values(data) \
            .where(tab.c.id == file_id)

        self.db.session.execute(query)

        if commit:
            self.db.session.commit()

    def selectFile(self, user_id, fs_id, file_path):

        tab = self.dbtables.FileSystemStorageTable
        query = tab.select().where(
                and_(tab.c.user_id == user_id,
                     tab.c.filesystem_id == fs_id,
                     tab.c.file_path == file_path,
                     ))
        item = self.db.session.execute(query).fetchone()

        return item

    def upsertFile(self, user_id, fs_id, file_path, data, commit=True):

        item = self.selectFile(user_id, fs_id, file_path)

        if item is None:
            self.insertFile(user_id, fs_id, file_path, data, commit)
        else:
            self.updateFile(item.id, data, commit)

    def removeFile(self, user_id, fs_id, file_path, commit=True):

        tab = self.dbtables.FileSystemStorageTable
        query = tab.delete() \
            .where(
                and_(tab.c.user_id == user_id,
                     tab.c.filesystem_id == fs_id,
                     tab.c.file_path == file_path,
                     ))

        self.db.session.execute(query)

        if commit:
            self.db.session.commit()

    def _item2dir(self, name):
        return FileRecord(name, True, 0, 0)

    def _item2file(self, name, item):
        record = FileRecord(name, False, item['size'], item['mtime'],
            item['version'], item['permission'])
        record.storage_path = item['storage_path']
        record.file_path = item['file_path']
        record.encryption = item['encryption']
        record.public = item['public']
        record.public_password = item['public_password']
        record.user_id = item['user_id']
        return record

    def _item2record(self, item, path_prefix, delimiter):
        item_path = item['file_path']
        if item_path.startswith(path_prefix):
            item_path = item_path[len(path_prefix):]
        if delimiter in item_path:
            name, _ = item_path.split(delimiter, 1)
            return self._item2dir(name)
        else:
            return self._item2file(item_path, item)

    def list(self):
        FsTab = self.dbtables.FileSystemStorageTable
        query = select(['*']).select_from(FsTab)

        return self.db.session.execute(query).fetchall()

    def listall(self, user_id, fs_id, path_prefix, limit=None, offset=None, delimiter='/'):
        FsTab = self.dbtables.FileSystemStorageTable

        if not path_prefix.endswith(delimiter):
            raise StorageException("invalid directory path. must end with `%s`" % delimiter)

        where = and_(FsTab.c.user_id == user_id,
                     FsTab.c.filesystem_id == fs_id,
                     FsTab.c.file_path.startswith(
                        bindparam('file_path', path_prefix)))

        query = FsTab.select().where(where)

        if limit is not None:
            query = query.limit(limit)

        if offset is not None:
            query = query.offset(offset).order_by(asc(FsTab.c.file_path))

        result = self.db.session.execute(query).fetchall()

        for item in result:
            obj = {
                "path": item.file_path[len(path_prefix):],
                "version": item.version,
                "size": item.size,
                "mtime": item.mtime,
                "permission": item.permission,
                "public": item.public,
                "encryption": item.encryption,
            }
            yield obj

    def listdir(self, user_id, fs_id, path_prefix, limit=None, offset=None, delimiter='/'):
        # search for persistent objects with prefix, that also do not contain
        # the delimiter

        FsTab = self.dbtables.FileSystemStorageTable

        if not path_prefix.endswith(delimiter):
            raise StorageException("invalid directory path. must end with `%s`" % delimiter)

        where = and_(FsTab.c.user_id == user_id,
                     FsTab.c.filesystem_id == fs_id,
                     FsTab.c.file_path.startswith(
                        bindparam('file_path', path_prefix)))

        query = FsTab.select().where(where)

        if limit is not None:
            query = query.limit(limit)

        if offset is not None:
            query = query.offset(offset).order_by(asc(FsTab.c.file_path))

        dirs = set()
        count = 0
        result = self.db.session.execute(query)
        for item in result.fetchall():
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
        # to be required in order to support s3,
        if count == 0:
            raise StorageNotFoundException("[listdir] not found: %s" % path_prefix)

    def file_info(self, user_id, fs_id, path_prefix, delimiter='/'):
        FsTab = self.dbtables.FileSystemStorageTable

        scheme, base_path = self.splitScheme(path_prefix)

        if not base_path:
            raise StorageException("empty path component")

        if path_prefix.endswith(delimiter):
            where = FsTab.c.file_path.startswith(bindparam('file_path', path_prefix))
            where = and_(FsTab.c.user_id == user_id,
                         FsTab.c.filesystem_id == fs_id,
                         where)
            exact = False
        else:
            where = FsTab.c.file_path == path_prefix
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
            return self._item2file(name, item)
        else:
            name = base_path.rstrip(delimiter).split(delimiter)[-1]
            return self._item2dir(name)

    @lru_cache(maxsize=16)
    def getFilesystemId(self, user_id, role_id, root_name):
        FsTab = self.dbtables.FileSystemTable
        FsPermissionTab = self.dbtables.FileSystemPermissionTable

        query = select([column("id")]) \
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

        return item.id

    def rootPath(self, user_id, role_id, root_name):
        """
        returns the root path for the given filesystem name
        """

        FsTab = self.dbtables.FileSystemTable
        FsPermissionTab = self.dbtables.FileSystemPermissionTable

        query = select([column("path")]) \
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
        root_path = format_storage_path(item.path,
            user_id=user_id, pwd=os.getcwd())

        return root_path

    # TODO: refactor absoluteFilePath, absolutePath
    # be more clear on return value
    # remove call to rootPath

    def absoluteFilePath(self, user_id, role_id, rel_path):
        """ path computation to sanitize user input
        return an absolute file path
        """

        if self.fs.isabs(rel_path):
            raise StorageException("path must not be absolute")

        rel_path = rel_path.replace("\\", "/")

        scheme, parts = self.fs.parts(rel_path)
        if any([p in (".", "..") for p in parts]):
            # path must be relative to root_path...
            raise StorageException("relative paths not allowed")

        if any([(not p.strip()) for p in parts]):
            raise StorageException("empty path component")

        # note: always checking the parts here since the path
        # could exist for the user (as part of sync) even though
        # server side the path will only ever be found in the database
        if any([p in _windows_device_files for p in parts]):
            raise StorageException("invalid windows path name")

        return self.fs.join("/", rel_path)


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

    def setUserDiskQuota(self, user_id, quota, commit=True):

        tab = self.db.tables.FileSystemUserSupplementaryTable

        statement = tab.select() \
            .with_only_columns([tab.c.quota]) \
            .where(tab.c.user_id == user_id)
        item = self.db.session.execute(statement).fetchone()

        if item is None:
            statement = tab.insert().values({
                "user_id": user_id,
                "quota": quota
            })
        else:
            statement = tab.update().values({
                "quota": quota
            }).where(tab.c.user_id == user_id)

        result = self.db.session.execute(statement)

        if commit:
            self.db.session.commit()

    def userDiskQuota(self, user_id):
        # todo: set default quota based on role_id, allow for individual
        #       users to exceed that quota, a value of zero is no limit

        tab = self.db.tables.FileSystemUserSupplementaryTable

        statement = tab.select() \
            .with_only_columns([tab.c.quota]) \
            .where(tab.c.user_id == user_id)

        result = self.db.session.execute(statement)
        item = result.fetchone()

        if item is None:
            return 0

        return item.quota

    def getEncryptionKey(self, user_id, password, mode='server'):

        tab = self.dbtables.FileSystemUserEncryptionTable

        statement = tab.select().where(
            and_(tab.c.user_id == user_id,
                 tab.c.expired.is_(None),
                 tab.c.mode == mode))

        item = self.db.session.execute(statement).fetchone()

        if item is None:
            raise StorageException("key not found")

        return decryptkey(password, item.encryption_key)

    def getUserKey(self, user_id, mode='server'):
        """
        return the encryption key without decrypting it first.
        """

        tab = self.dbtables.FileSystemUserEncryptionTable

        statement = tab.select().where(
            and_(tab.c.user_id == user_id,
                 tab.c.expired.is_(None),
                 tab.c.mode == mode))

        item = self.db.session.execute(statement).fetchone()

        if item is None:
            raise StorageException("key not found")

        return item.encryption_key

    def setUserKey(self, user_id, key, mode='server', commit=True):

        tab = self.dbtables.FileSystemUserEncryptionTable

        statement = tab.select().where(
            and_(tab.c.user_id == user_id,
                 tab.c.expired.is_(None),
                 tab.c.mode == mode))

        item = self.db.session.execute(statement).fetchone()

        # invalidate the old key if it exists
        if item is not None:
            epoch = int(calendar.timegm(datetime.datetime.now().timetuple()))
            statement = tab.update().values({"expired": epoch}) \
                .where(tab.c.id == item.id)
            self.db.session.execute(statement)

        statement = tab.insert().values({
            "user_id": user_id,
            "mode": mode,
            "encryption_key": key,
            "expired": None})
        self.db.session.execute(statement)

        if commit:
            self.db.session.commit()

    def changePassword(self, user_id, password, new_password, mode='server', commit=True):

        tab = self.dbtables.FileSystemUserEncryptionTable

        statement = tab.select().where(
            and_(tab.c.user_id == user_id,
                 tab.c.expired.is_(None),
                 tab.c.mode == mode))

        item = self.db.session.execute(statement).fetchone()

        if item is None:
            new_key = cryptkey(new_password)
        else:
            new_key = recryptkey(password, new_password, item.encryption_key)
            # expire the old password
            epoch = int(calendar.timegm(datetime.datetime.now().timetuple()))

            statement = tab.update().values({"expired": epoch}) \
                .where(tab.c.id == item.id)
            self.db.session.execute(statement)

        statement = tab.insert().values({
            "user_id": user_id,
            "mode": mode,
            "encryption_key": new_key,
            "expired": None})
        self.db.session.execute(statement)

        if commit:
            self.db.session.commit()

        return new_key

    def setFilePublic(self, user_id, file_path, password=None, revoke=False, commit=True):

        tab = self.db.tables.FileSystemStorageTable

        columns = [tab.c.id, tab.c.public,
            tab.c.public_password, tab.c.encryption]
        clause = and_(tab.c.user_id == user_id, tab.c.file_path == file_path)
        statement = tab.select() \
            .with_only_columns(columns) \
            .where(clause)
        item = self.db.session.execute(statement).fetchone()

        if not item:
            raise StorageNotFoundException(file_path)

        if item.encryption == CryptMode.server:
            raise StorageException("file resource is encrypted")

        if item.encryption == CryptMode.client:
            raise StorageException("file resource is encrypted by the user")

        if revoke:
            record = {
                "public": None,
                "public_password": None
            }
        else:
            password_hash = hash_password(password) if password else None

            # bytes need to be encoded as strings when storing in postgres
            if password_hash and self.db.kind() == "postgresql":
                password_hash = password_hash.decode("utf-8")

            record = {
                "public": url_uuid_v2(),
                "public_password": password_hash
            }

        statement = tab.update() \
            .values(record).where(tab.c.id == item.id)

        self.db.session.execute(statement)

        if commit:
            self.db.session.commit()

        return record['public']

    def verifyPublicPassword(self, public_id, password):
        """
        return true if the password is valid for the given file
        """

        tab = self.db.tables.FileSystemStorageTable

        statement = tab.select() \
            .with_only_columns([tab.c.public_password]) \
            .where(tab.c.public == public_id)
        item = self.db.session.execute(statement).fetchone()

        if not item:
            raise StorageNotFoundException(public_id)

        hash = item.public_password

        # if no password set, return true only if
        # no password was given

        if not hash:
            return password is None

        if password is None:
            return False

        if self.db.kind() == "postgresql":
            hash = hash.encode("utf-8")

        res = check_password_hash(hash, password)
        return res

    def publicFileInfo(self, public_id, delimiter='/'):
        tab = self.db.tables.FileSystemStorageTable

        statement = tab.select().where(tab.c.public == public_id)
        item = self.db.session.execute(statement).fetchone()
        if not item:
            raise StorageNotFoundException(public_id)
        name = item.file_path.split(delimiter)[-1]
        return self._item2file(name, item)


