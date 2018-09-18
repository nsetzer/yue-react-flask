

from sqlalchemy.orm import relationship
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, not_, case, select, update, column, func, asc, desc
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

    def insert_path(self, user_id, path):

        name, is_dir, size, mtime = self.fs.file_info()

        return self.insert(user_id, path, size, mtime)

    def insert(self, user_id, path, size, mtime):

        record = {
            'user_id': user_id,
            'version': 0,
            'path': path,
            'mtime': mtime,
            'size': mtime,

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