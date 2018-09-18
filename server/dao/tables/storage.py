

from sqlalchemy.schema import Table, Column, ForeignKey
from sqlalchemy.types import Integer, String

from .util import generate_uuid, StringArrayType
import time

def FileSystemStorageTable(metadata):
    """ returns a table describing items in persistent storage

    user_id: the owner of the file
    path: a fully qualified path (starting with file://, s3://, etc)
          the location of a resource
    version: an incrementing integer counting how many times the file has
             been rewritten
    size: the size in bytes of the current version of the file
    mtime: the last time the file file was modified
           (the creation date for the latest version)
    """
    return Table('filesystem_storage', metadata,
        Column('user_id', ForeignKey("user_role.id"), nullable=False),
        # text
        Column('path', String, default=""),
        # number
        Column('version', Integer, default=0),
        Column('size', Integer, default=0),
        # date
        Column('mtime', Integer, default=lambda: int(time.time()))
    )

def FileSystemTable(metadata):
    """ returns a table which maps a 'root' name to a file system location
    """
    return Table('filesystem', metadata,
        Column('id', Integer, primary_key=True),
        # text
        Column('name', String, default=""),
        Column('path', String, default=""),
    )


def FileSystemPermissionTable(metadata):
    """ returns a table which lists the file system locations roles have access to
    """

    return Table('filesystem_permission', metadata,
        Column('role_id', ForeignKey("user_role.id"), nullable=False),
        Column('file_id', ForeignKey("filesystem.id"), nullable=False),
    )

