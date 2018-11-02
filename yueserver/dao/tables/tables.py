
"""
A class which describes the set of tables defined in this package.
"""
import logging

from sqlalchemy.schema import Table

from .user import DomainTable, RoleTable, UserTable, \
                  GrantedDomainTable, GrantedRoleTable, \
                  FeatureTable, RoleFeatureTable, UserSessionTable, \
                  UserPreferencesTable
from .song import SongDataTable, SongUserDataTable, \
                  SongQueueTable, SongHistoryTable, SongPlaylistTable
from .storage import FileSystemStorageTableV1, FileSystemStorageTableV2, \
                     FileSystemTable, FileSystemPermissionTable, \
                     FileSystemUserDataTable
from .schema import ApplicationSchemaTable

class BaseDatabaseTables(object):
    """docstring for BaseDatabaseTables"""
    def __init__(self):
        super(BaseDatabaseTables, self).__init__()

    def drop(self, engine):
        """ drop all tables, using engine as the db connection """

        for item in self.__dict__.values():
            if isinstance(item, Table):
                item.drop(engine, checkfirst=True)

class DatabaseTablesV0(BaseDatabaseTables):
    """define all tables required for the database"""
    version = 0

    def __init__(self, metadata):
        super(DatabaseTables, self).__init__()

        self.DomainTable = DomainTable(metadata)
        self.RoleTable = RoleTable(metadata)
        self.UserTable = UserTable(metadata)
        self.GrantedDomainTable = GrantedDomainTable(metadata)
        self.GrantedRoleTable = GrantedRoleTable(metadata)
        self.FeatureTable = FeatureTable(metadata)
        self.RoleFeatureTable = RoleFeatureTable(metadata)

        self.SongDataTable = SongDataTable(metadata)
        self.SongUserDataTable = SongUserDataTable(metadata)
        self.SongQueueTable = SongQueueTable(metadata)
        self.SongHistoryTable = SongHistoryTable(metadata)
        self.SongPlaylistTable = SongPlaylistTable(metadata)

        self.FileSystemStorageTable = FileSystemStorageTableV1(metadata)
        self.FileSystemTable = FileSystemTable(metadata)
        self.FileSystemPermissionTable = FileSystemPermissionTable(metadata)

class DatabaseTablesV1(BaseDatabaseTables):
    """define all tables required for the database"""
    version = 1

    def __init__(self, metadata):
        super(DatabaseTablesV1, self).__init__()

        self.ApplicationSchemaTable = ApplicationSchemaTable(metadata)

        self.DomainTable = DomainTable(metadata)
        self.RoleTable = RoleTable(metadata)
        self.UserTable = UserTable(metadata)
        self.GrantedDomainTable = GrantedDomainTable(metadata)
        self.GrantedRoleTable = GrantedRoleTable(metadata)
        self.FeatureTable = FeatureTable(metadata)
        self.RoleFeatureTable = RoleFeatureTable(metadata)
        self.UserSessionTable = UserSessionTable(metadata)
        self.UserPreferencesTable = UserPreferencesTable(metadata)

        self.SongDataTable = SongDataTable(metadata)
        self.SongUserDataTable = SongUserDataTable(metadata)
        self.SongQueueTable = SongQueueTable(metadata)
        self.SongHistoryTable = SongHistoryTable(metadata)
        self.SongPlaylistTable = SongPlaylistTable(metadata)

        self.FileSystemStorageTable = FileSystemStorageTableV2(metadata)
        self.FileSystemTable = FileSystemTable(metadata)
        self.FileSystemPermissionTable = FileSystemPermissionTable(metadata)
        self.FileSystemUserDataTable = FileSystemUserDataTable(metadata)

DatabaseTables = DatabaseTablesV0

#all_tables= sorted([x for x in locals() if Base], key= x.version)
# offset = current_version - all_tables[0].version
# use all_Tables to migrate x to y

# export the latest version of the schema
