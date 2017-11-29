

from ..dao.user import UserDao
from ..dao.library import LibraryDao

class AudioService(object):
    """docstring for AudioService"""

    _instance = None

    def __init__(self, db, dbtables):
        super(AudioService, self).__init__()
        self.db = db
        self.dbtables = dbtables

        self.userDao = UserDao(db, dbtables)
        self.libraryDao = LibraryDao(db, dbtables)

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

