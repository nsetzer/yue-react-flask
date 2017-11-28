
from .message import MessageTable
from .queue import SongQueueTable


class DatabaseTables(object):
    """docstring for AppTables"""
    def __init__(self, metadata):
        super(DatabaseTables, self).__init__()
        self.SongQueueTable = SongQueueTable(metadata)
        self.MessageTable = MessageTable(metadata)




