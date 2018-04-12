
import logging

from .user import DomainTable, RoleTable, UserTable, \
                  GrantedDomainTable, GrantedRoleTable, \
                  FeatureTable, RoleFeatureTable
from .song import SongDataTable, SongUserDataTable, \
                  SongQueueTable, SongHistoryTable, SongPlaylistTable


class DatabaseTables(object):
    """docstring for AppTables"""
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

    def drop(self, engine):

        self.SongPlaylistTable.drop(engine, checkfirst=True)
        self.SongHistoryTable.drop(engine, checkfirst=True)
        self.SongQueueTable.drop(engine, checkfirst=True)
        self.SongUserDataTable.drop(engine, checkfirst=True)
        self.SongDataTable.drop(engine, checkfirst=True)
        self.RoleFeatureTable.drop(engine, checkfirst=True)
        self.FeatureTable.drop(engine, checkfirst=True)
        self.GrantedRoleTable.drop(engine, checkfirst=True)
        self.GrantedDomainTable.drop(engine, checkfirst=True)
        self.UserTable.drop(engine, checkfirst=True)
        self.RoleTable.drop(engine, checkfirst=True)
        self.DomainTable.drop(engine, checkfirst=True)







