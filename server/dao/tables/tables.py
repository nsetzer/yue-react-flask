
from .message import MessageTable
from .user import DomainTable, RoleTable, UserTable, \
                  GrantedDomainTable, GrantedRoleTable, \
                  FeatureTable, RoleFeatureTable
from .song import SongDataTable, SongUserDataTable, \
                  SongQueueTable, SongHistoryTable, SongPlaylistTable


class DatabaseTables(object):
    """docstring for AppTables"""
    def __init__(self, metadata):
        super(DatabaseTables, self).__init__()

        self.MessageTable = MessageTable(metadata)

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








