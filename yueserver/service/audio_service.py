
"""
The Audio service handles the interaction with the database for a particular
user. The methods exposed allow a user to search the database for songs,
as well as update metadata and statistics
"""
import os
import logging

from ..dao.user import UserDao
from ..dao.library import LibraryDao, Song
from ..dao.queue import SongQueueDao
from ..dao.history import HistoryDao
from ..dao.shuffle import binshuffle
from ..dao.filesys.filesys import FileSystem

from .exception import AudioServiceException

class AudioService(object):
    """docstring for AudioService"""

    _instance = None

    def __init__(self, config, db, dbtables):
        super(AudioService, self).__init__()
        self.config = config
        self.db = db
        self.dbtables = dbtables

        self.userDao = UserDao(db, dbtables)
        self.libraryDao = LibraryDao(db, dbtables)
        self.queueDao = SongQueueDao(db, dbtables)
        self.historyDao = HistoryDao(db, dbtables)
        self.fs = FileSystem()

    @staticmethod
    def init(config, db, dbtables):
        if not AudioService._instance:
            AudioService._instance = AudioService(config, db, dbtables)
        return AudioService._instance

    @staticmethod
    def instance():
        return AudioService._instance

    def _getSongInfo(self, user, song_id):
        song = self.libraryDao.findSongById(
            user['id'], user['domain_id'], song_id)

        if not song:
            raise AudioServiceException(
                "song not found for id: %s" % song_id)

        return song

    def findSongById(self, user, song_id):
        """ return a song object given the user and song id
        """
        return self._getSongInfo(user, song_id)

    def findSongByReferenceId(self, user, ref_id):
        """ return a song object given the user and song id
        """
        song = self.libraryDao.findSongByReferenceId(
            user['id'], user['domain_id'], ref_id)

        if not song:
            raise AudioServiceException(
                "song not found for id: %s" % ref_id)

        return song

    def setSongFilePath(self, user, song_id, path):
        """ set the location of the audio file for the song by song id
        """
        if not self.fs.exists(path):
            logging.error("invalid path: %s" % path)
            raise AudioServiceException("invalid path")

        uid = user['id']
        did = user['domain_id']
        song = {Song.path: path}
        self.libraryDao.update(uid, did, song_id, song)

    def setSongAlbumArtPath(self, user, song_id, path):
        """ set the location of the album art for the song by song id
        """
        if not self.fs.exists(path):
            logging.error("invalid path: %s" % path)
            raise AudioServiceException("invalid path")

        uid = user['id']
        did = user['domain_id']
        song = {Song.art_path: path}
        self.libraryDao.update(uid, did, song_id, song)

    def getSongAudioPath(self, user, song_id):
        """ retrieve the path for audio file for the song by song id
        """
        song = self._getSongInfo(user, song_id)

        return song['file_path']

    def getSongArtPath(self, user, song_id):
        """ retrieve the path for album art file for the song by song id
        """
        song = self._getSongInfo(user, song_id)

        return song['art_path']

    def search(self, user,
        searchTerm,
        case_insensitive=True,
        orderby=None,
        limit=None,
        offset=None):
        """ query the library and return a list of songs

        query results are restricted by the users domain and role
        """

        shuffle = False
        limit_save = limit
        if orderby == "random":
            orderby = None
            shuffle = True
            limit = None

        result = self.libraryDao.search(
            user['id'], user['domain_id'],
            searchTerm, case_insensitive,
            orderby, limit, offset)

        if shuffle:
            result = binshuffle(result, lambda s: s['artist'])[:limit_save]

        return result

    def updateSongs(self, user, songs):
        """
        update metadata for a set of songs

        songs can be partial song objects (i.e. at minimum 2 fields, one
        of which is the song id)

        updates are restricted by the users domain and role
        """

        # TODO: check user role features

        for song in songs:
            song_id = song['id']
            del song['id']
            uid = user['id']
            did = user['domain_id']
            self.libraryDao.update(uid, did, song_id, song, commit=False)
        self.db.session.commit()

    def createSong(self, user, song):
        """ create a new song record and return the song_id

        restricted by the users domain and role

        """
        uid = user['id']
        did = user['domain_id']

        # TODO: check user role features
        song_id = self.libraryDao.insert(uid, did, song)

        return song_id

    def getDomainSongInfo(self, domain_id):
        """
        return information about the set of artists and albums in the given
        domain
        """
        return self.libraryDao.domainSongInfo(domain_id)

    def getDomainSongUserInfo(self, user):
        """
        return information about the set of artists and albums in the given
        domain.

        results are restricted by the given users domain
        """
        return self.libraryDao.domainSongUserInfo(user['id'], user['domain_id'])

    def getQueue(self, user):
        """ return the list of songs (not song ids) from a users queue """
        return self.queueDao.get(user['id'], user['domain_id'])

    def setQueue(self, user, song_ids):
        """ set the queue for a user to be a list of songs """
        self.queueDao.set(user['id'], user['domain_id'], song_ids)

    def getQueueHead(self, user):
        """ return the song at the head of the queue """
        return self.queueDao.head(user['id'], user['domain_id'])

    def getQueueRest(self, user):
        """ return every song in the queue, except the head element
        """
        return self.queueDao.rest(user['id'], user['domain_id'])

    def defaultQuery(self, user):
        """ retrieve the current default query used by the user
        """
        return self.queueDao.getDefaultQuery(user['id'])

    def setDefaultQuery(self, user, query_str):
        """ set the default query to use when populating the queue for the user
        """
        return self.queueDao.setDefaultQuery(user['id'], query_str)

    def populateQueue(self, user):
        """
        use the default query to add new songs to the queue
        """
        songs = self.queueDao.get(user['id'], user['domain_id'])

        query = self.defaultQuery(user)

        # TODO: have role based limits on queue size
        limit = 50

        new_songs = self.search(user,
            query, limit=limit, orderby=Song.random)

        songs = (songs + new_songs)[:50]

        song_ids = [song['id'] for song in songs]
        self.queueDao.set(user['id'], user['domain_id'], song_ids)

        return songs

    def updatePlayCount(self, user, records, updateHistory=True):
        """
        update the playcount for a list of songs, and record history.

        records: a list of objects containing a `song_id`, and `timestamp`.
        """
        raise NotImplementedError()

    def insertPlayHistory(self, user, records):
        """
        update play history for a user given a list of records

        this merges the records with the existing database, allowing
        a user to double push without creating duplicates

        records: a list of objects containing a `song_id`, and `timestamp`.

        returns the number of records successfully imported.
        """

        # get a set of existing records for the same time span
        # as the records that are given in the request
        start = min((r['timestamp'] for r in records))
        end   = max((r['timestamp'] for r in records))
        db_records = self.historyDao.retrieve(user['id'], start, end)
        record_set = set((r['timestamp'] for r in db_records))

        # only insert records if they are unique (by time)
        count = 0
        for record in records:
            if record['timestamp'] not in record_set:
                self.historyDao.insert(user['id'],
                                       record['song_id'],
                                       record['timestamp'],
                                       commit=False)
                count += 1
        self.db.session.commit()

        return count

    def getPlayHistory(self, user, start, end=None, offset=None, limit=None):
        """
        return records playback history records for a user.
        """
        return self.historyDao.retrieve(user['id'], start, end, offset, limit)





