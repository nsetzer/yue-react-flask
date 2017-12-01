
from .message import MessageTable
from .user import DomainTable, RoleTable, UserTable, \
                  GrandtedDomainTable, GrandtedRoleTable, \
                  FeatureTable, RoleFeatureTable
from .song import SongDataTable, SongUserDataTable
from .queue import SongQueueTable
from .song_history import SongHistoryTable
from .playlist import SongPlaylistTable


class DatabaseTables(object):
    """docstring for AppTables"""
    def __init__(self, metadata):
        super(DatabaseTables, self).__init__()

        self.MessageTable = MessageTable(metadata)

        self.DomainTable = DomainTable(metadata)
        self.RoleTable = RoleTable(metadata)
        self.UserTable = UserTable(metadata)
        self.GrandtedDomainTable = GrandtedDomainTable(metadata)
        self.GrandtedRoleTable = GrandtedRoleTable(metadata)
        self.FeatureTable = FeatureTable(metadata)
        self.RoleFeatureTable = RoleFeatureTable(metadata)

        self.SongDataTable = SongDataTable(metadata)
        self.SongUserDataTable = SongUserDataTable(metadata)
        self.SongQueueTable = SongQueueTable(metadata)
        self.SongHistoryTable = SongHistoryTable(metadata)
        self.SongPlaylistTable = SongPlaylistTable(metadata)








