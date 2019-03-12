

from sqlalchemy.schema import Table, Column, ForeignKey, UniqueConstraint
from sqlalchemy.types import Integer, String, Boolean
from sqlalchemy.sql import func
from sqlalchemy.sql import select

from .util import generate_uuid, StringArrayType, CreateView
import time

def FileSystemStorageTableV1(metadata):
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
        Column('user_id', ForeignKey("user.id"), nullable=False),
        # text
        Column('path', String, primary_key=True, nullable=False),
        # number
        Column('permission', Integer, default=0o644),
        Column('version', Integer, default=0),
        Column('size', Integer, default=0),

        # encryption is an integer to leave room for the possibility
        # of client side or server side encryption/decryption
        Column('encrypted', Integer, default=0),
        # date
        Column('mtime', Integer, default=lambda: int(time.time())),
    )

def FileSystemStorageTableV2(metadata):
    """ returns a table describing items in persistent storage

    This new table enables the following features:
        - private static file URLs
        - optional public URLs which can be changed
        - ability to associate a keyframe for previews
        - file versioning
        - data at rest encryption
        - masking of the file name at rest
            - the file name is in the database
            - while the file on disk uses a random name
    user_id: the owner of the file
    file_path: the user specified relative path for the file
    storage_path: a fully qualified path (starting with file://, s3://, etc)
          the location of a resource
    preview_large:
    preview_small:
    permission: an integer (octal) representing unix permissions, e.g. 0o644
    version: an incrementing integer counting how many times the file has
             been rewritten
    size: the size in bytes of the current version of the file
    expired: expired is None for the latest version of a file
             otherwise it is the date the version was retired
    encryption: the encryption mode
    public: Null, or a uuid which is used for a public link
    mtime: the last time the file file was modified
           (the creation date for the latest version)
    """
    return Table('filesystem_storage_v2', metadata,
        Column('id', String, primary_key=True, default=generate_uuid),
        Column('user_id', ForeignKey("user.id"), nullable=False),
        # text
        # 2019-01-06: the theory is that file_path and storage_path
        # should always be unique.
        #   file_path: since the path has a unique prefix per user
        #     e.g.  $default/sample.txt => "s3://bucket/userid/sample.txt"
        #   storage_path: since this must be unqiue per file
        Column('file_path', String, nullable=False),
        Column('storage_path', String, unique=True, nullable=False),
        # however preview path may not be unique
        # e.g. one album with 10 songs using the same jpeg.
        Column('preview_path', String),

        Column('permission', Integer, default=0o644),
        Column('version', Integer, default=0),
        Column('size', Integer, default=0),
        Column('expired', Integer),

        # encryption can be set to 'client', 'server', 'system'. or None
        # indicates the encryption mode
        Column('encryption', String, default=None),
        # an optional password to protect public files
        Column('public_password', String, nullable=True),
        # a unique public identifier for this file
        Column('public', String, unique=True, default=None),

        Column('mtime', Integer, default=lambda: int(time.time())),
    )

def FileSystemStorageTableV3(metadata):
    """ returns a table describing items in persistent storage

    This new table enables the following features:
        - private static file URLs
        - optional public URLs which can be changed
        - ability to associate a keyframe for previews
        - file versioning
        - data at rest encryption
        - masking of the file name at rest
            - the file name is in the database
            - while the file on disk uses a random name
    user_id: the owner of the file
    file_path: the user specified relative path for the file
    storage_path: a fully qualified path (starting with file://, s3://, etc)
          the location of a resource
    preview_large:
    preview_small:
    permission: an integer (octal) representing unix permissions, e.g. 0o644
    version: an incrementing integer counting how many times the file has
             been rewritten
    size: the size in bytes of the current version of the file
    expired: expired is None for the latest version of a file
             otherwise it is the date the version was retired
    encryption: the encryption mode
    public: Null, or a uuid which is used for a public link
    mtime: the last time the file file was modified
           (the creation date for the latest version)
    """
    return Table('filesystem_storage_v3', metadata,
        Column('id', String, primary_key=True, default=generate_uuid),
        Column('user_id', ForeignKey("user.id"), nullable=False),
        Column('filesystem_id', ForeignKey("filesystem.id"), nullable=False),
        # file_path must not be null, and start with '/'
        # but may not be unique.
        # the set (user_id, filesystem, file_path) must be unique
        Column('file_path', String, nullable=False),
        Column('storage_path', String, unique=True, nullable=False),
        # however preview path may not be unique
        # e.g. one album with 10 songs using the same jpeg.
        Column('preview_path', String),

        Column('permission', Integer, default=0o644),
        Column('version', Integer, default=0),
        Column('size', Integer, default=0),
        Column('expired', Integer, nullable=True),

        # encryption can be set to 'client', 'server', 'system'. or None
        # indicates the encryption mode
        Column('encryption', String, default=None),
        # an optional password to protect public files
        Column('public_password', String, nullable=True),
        # a unique public identifier for this file
        Column('public', String, unique=True, default=None),

        Column('mtime', Integer, default=lambda: int(time.time())),

        UniqueConstraint('user_id', 'filesystem_id', 'file_path', name='uix_fs'),
    )

FileSystemStorageTableCurrentVersionName = 'filesystem_storage_v3'

def FileSystemPreviewStorageTableV1(metadata):
    """ returns a table for storing keyframes of user files
    """
    return Table('filesystem_preview_storage_v1', metadata,
        Column('id', Integer, primary_key=True),
        Column('user_id', ForeignKey("user.id"), nullable=False),
        Column('file_id',
            ForeignKey("%s.id" % FileSystemStorageTableCurrentVersionName),
            nullable=False),
        # resource file system and absolute url
        Column('filesystem_id', ForeignKey("filesystem.id"), nullable=False),
        Column('path', String, nullable=False),
        # description of the image scale
        Column('scale', String, nullable=False),
        # 1 if up to date, 0 if it needs to be regenerated
        Column('valid', Integer, nullable=False),
        # dimensions of the image
        Column('width', Integer, nullable=False),
        Column('height', Integer, nullable=False),
        # size of the file in bytes
        Column('size', Integer, nullable=False),
        UniqueConstraint('file_id', 'scale', name='uix_fs_preview'),
    )

def FileSystemTempFileTableV1(metadata):
    """ returns a table for storing meta information about temp files

    store the number of bytes in-flight for a file
    refer to the file using a session specific unique id
    """
    return Table('filesystem_tempfile_v1', metadata,
        Column('user_id', ForeignKey("user.id"), nullable=False),
        Column('uid', String, unique=True, nullable=False),
        Column('size', Integer, nullable=False),
    )

def FileSystemTable(metadata):
    """ returns a table which maps a 'root' name to a file system location
    """
    return Table('filesystem', metadata,
        Column('id', Integer, primary_key=True),
        # text
        Column('name', String, unique=True, nullable=False),
        Column('path', String, nullable=False),
    )

def FileSystemUserSupplementaryTable(metadata):
    return Table('filesystem_user_supplementary_v1', metadata,
        Column('user_id', ForeignKey("user.id"), nullable=False),
        # quota is the maximum disk usage allowed by the user
        # if not set or 0, then there is no maximum
        # value is in bytes
        Column('quota', Integer, nullable=False)
    )

def FileSystemUserEncryptionTable(metadata):
    return Table('filesystem_encryption_v1', metadata,
        Column('id', Integer, primary_key=True),
        Column('user_id', ForeignKey("user.id"), nullable=False),
        # text
        # mode is one of: client, server, system.
        # indicates who owns the encryption key
        #  client: fully owned by the user
        #  server: set by the user, owned by the server
        #  system: user has no control of encryption key
        Column('mode', String, nullable=False),
        # the encryption key is a string, itself encrypted using a password
        # known only to the user.
        Column('encryption_key', String, nullable=False),
        # expired is None for the latest version of a file
        # otherwise it is the date the version was retired
        Column('expired', Integer, nullable=True)
    )

def FileSystemPermissionTable(metadata):
    """ returns a table which lists the file system locations roles have access to
    """

    return Table('filesystem_permission', metadata,
        Column('role_id', ForeignKey("user_role.id"), nullable=False),
        Column('file_id', ForeignKey("filesystem.id"), nullable=False),
    )

def FileSystemUserUsageView(tables, metadata):

    t1 = tables.FileSystemStorageTable
    t2 = tables.FileSystemUserSupplementaryTable
    query = select([
            t1.c.user_id,
            func.count(t1.c.size).label('count'),
            func.sum(t1.c.size).label('usage'),
            t2.c.quota,
    ]).select_from(t2) \
        .where(t1.c.user_id == t2.c.user_id) \
        .group_by(t1.c.user_id)

    name = "v_filesystem_user_diskusage"
    text = CreateView(name, query)

    def f(engine, obj):
        engine.execute(text)
        obj.FileSystemUserUsageView = Table(name, metadata,
            Column('user_id', String),
            Column('count', Integer),
            Column('usage', Integer),
            Column('quota', Integer),
        )

    return f




