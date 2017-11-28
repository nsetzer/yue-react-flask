
from .message import MessageTable
from .queue import SongQueueTable
from .song_history import SongHistoryTable
from .playlist import SongPlaylistTable
from .user import DomainTable, RoleTable, UserTable


class DatabaseTables(object):
    """docstring for AppTables"""
    def __init__(self, metadata):
        super(DatabaseTables, self).__init__()
        self.SongQueueTable = SongQueueTable(metadata)
        self.MessageTable = MessageTable(metadata)
        self.SongHistoryTable = SongHistoryTable(metadata)
        self.SongPlaylistTable = SongPlaylistTable(metadata)

        self.DomainTable = DomainTable(metadata)
        self.RoleTable = RoleTable(metadata)
        self.UserTable = UserTable(metadata)




