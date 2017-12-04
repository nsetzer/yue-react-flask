

from ..dao.user import UserDao
from ..dao.library import LibraryDao
from ..dao.queue import SongQueueDao

class ServiceException(Exception):

    def __init__(self, user, message):
        name = "%s@%s/%s" % (user['email'], user['domain_id'], user['role_id'])
        message = name + ": " + message
        super(ServiceException, self).__init__(message)

class AudioServiceException(ServiceException):
    pass

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

    def _getSongInfo(self, user, song_id):
        song = self.libraryDao.findSongById(user['id'], user['domain_id'], song_id);

        if not song:
            raise AudioServiceException(user,
                "song not found for id: %s" % song_id)

        return song

    def findSongById(self, user, song_id):

        # TODO check user role permissions

        return self._getSongInfo(user, song_id)

    def getSongAudioPath(self, user, song_id):

        song = self._getSongInfo(user, song_id)

        return song['file_path']

    def getSongArtPath(self, user, song_id):

        song = self._getSongInfo(user, song_id)

        return song['art_path']

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


