

from ..dao.user import UserDao
from ..dao.library import LibraryDao, Song
from ..dao.queue import SongQueueDao

from .util import AudioServiceException
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
        song = self.libraryDao.findSongById(
            user['id'], user['domain_id'], song_id)

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

    def getQueue(self, user):
        return self.queueDao.get(user['id'], user['domain_id'])

    def setQueue(self, user, song_ids):
        self.queueDao.set(user['id'], user['domain_id'], song_ids)

    def getQueueHead(self, user):
        return self.queueDao.head(user['id'], user['domain_id'])

    def getQueueRest(self, user):
        return self.queueDao.rest(user['id'], user['domain_id'])

    def defaultQuery(self, user):
        return None

    def populateQueue(self, user):
        songs = self.queueDao.get(user['id'], user['domain_id'])

        query = self.defaultQuery(user)

        # TODO: have role based limits on queue size
        limit = 50

        new_songs = self.search(user,
            query, limit=limit, orderby=Song.random)

        songs = songs + new_songs

        song_ids = [song['id'] for song in songs]
        self.queueDao.set(user['id'], user['domain_id'], song_ids)

        return songs





