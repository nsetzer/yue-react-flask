

from ..dao.user import UserDao
from ..dao.library import LibraryDao
from ..dao.queue import SongQueueDao

class AudioService(object):
    """docstring for AudioService"""

    _instance = None

    def __init__(self, db, dbtables):
        super(AudioService, self).__init__()
        self.db = db
        self.dbtables = dbtables

        self.userDao = UserDao(db, dbtables)
        self.libraryDao = LibraryDao(db, dbtables)
        self.queueDao = SongQueueDao(db, dbtables)

    @staticmethod
    def init(db, dbtables):
        if not AudioService._instance:
            AudioService._instance = AudioService(db, dbtables)
        return AudioService._instance

    @staticmethod
    def instance():
        return AudioService._instance

    def findSongById(self, user, song_id):

        # TODO check user role permissions

        song = self.libraryDao.findSongById(user['id'], user['domain_id'], song_id);

        return song

    def getSongAudioPath(self, user, song_id):

        song = self.libraryDao.findSongById(user['id'], user['domain_id'], song_id);

        return song['file_path']

    def search(self, user,
        searchTerm,
        case_insensitive=True,
        orderby=None,
        limit=None,
        offset=None):

        return self.libraryDao.search(
            user['id'], user['domain_id'],
            searchTerm, case_insensitive,
            orderby, limit, offset)


