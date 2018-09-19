

from sqlalchemy.orm import relationship
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, not_, select, column, update, insert, delete

from sqlalchemy.sql.expression import bindparam
from .search import SearchGrammar, ParseError, Rule
from .filesys.filesys import FileSystem

import datetime, time
import uuid

class StorageDao(object):
    """docstring for StorageDao"""
    def __init__(self, db, dbtables):
        super(StorageDao, self).__init__()
        self.db = db
        self.dbtables = dbtables
        self.fs = FileSystem()

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

    def insert(self, user_id, path, size, mtime):

        record = {
            'user_id': user_id,
            'version': 0,
            'path': path,
            'mtime': mtime,
            'size': size,

        }
        query = self.dbtables.FileSystemStorageTable.insert() \
            .values(record)

        result = self.db.session.execute(query)

    def listdir(self, user_id, path, delimiter='/'):
        # search for persistent objects with prefix, that also do not contain
        # the delimiter

        FsTab = self.dbtables.FileSystemStorageTable

        query = select(['*']) \
            .select_from(FsTab) \
            .where(bindparam('path', path).startswith(path))

        dirs = set()
        for item in self.db.session.execute(query).fetchall():
            item_path = item['path'].replace(path, "")
            if delimiter in item_path:
                name, _ = item_path.split(delimiter, 1)
                is_dir = True
                if name not in dirs:
                    dirs.add(name)
                    yield (name, True, item['size'], item['mtime'])
            else:
                yield (item_path, False, item['size'], item['mtime'])

    def file_info(self, user_id, path):
        pass

    def file_size(self, path):
        # return file info ignoring user permissions
        # the back end can allow any user to query the file size of songs
        pass