
"""
The Audio service handles the interaction with the database for a particular
user. The methods exposed allow a user to search the database for songs,
as well as update metadata and statistics
"""
import os, sys
import logging

from ..dao.user import UserDao
from ..dao.library import LibraryDao, Song
from ..dao.queue import SongQueueDao
from ..dao.history import HistoryDao
from ..dao.shuffle import binshuffle
from ..dao.storage import StorageDao, StorageNotFoundException
from ..dao.filesys.filesys import FileSystem

from .exception import AudioServiceException

class AudioService(object):
    """docstring for AudioService"""

    _instance = None

    def __init__(self, config, db, dbtables):
        # TODO: all services should not accept a config,
        #       instead have getters, setters, defaults
        super(AudioService, self).__init__()
        self.config = config
        self.db = db
        self.dbtables = dbtables

        self.userDao = UserDao(db, dbtables)
        self.libraryDao = LibraryDao(db, dbtables)
        self.queueDao = SongQueueDao(db, dbtables)
        self.historyDao = HistoryDao(db, dbtables)
        self.storageDao = StorageDao(db, dbtables)
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

    def _getOrCreateFileEntry(self, user, song_id, fs_name, rel_path):
        """
        Get or Create a File Entry for a given path

        look up a path in the file system table, or check
        the underlying file system for a file of the same name

        return the true storage path and file size, so that it can
        be used as the path for audio or album art for a song
        """
        uid = user['id']
        did = user['domain_id']
        rid = user['role_id']

        fs_id = self.storageDao.getFilesystemId(
                user['id'], user['role_id'], fs_name)

        file_path = self.storageDao.absoluteFilePath(
                user['id'], user['role_id'], rel_path)

        try:

            info = self.storageDao.file_info(uid, fs_id, file_path)
            storage_path = info.storage_path
        except StorageNotFoundException as e:
            # if the file is not in the database, check the file system
            # then add it to the database
            # throws FileNotFoundError if dne

            storage_path = self.storageDao.absolutePath(
                uid, rid, fs_name, rel_path)

            try:
                info = self.fs.file_info(storage_path)
            except Exception as e:
                logging.exception(e)
                raise

            data = dict(
                storage_path=storage_path,
                permission=info.permission,
                size=info.size,
                mtime=info.mtime,
            )

            self.storageDao.upsertFile(user['id'], fs_id, file_path, data)

        return storage_path, info.size

    def setSongFilePath(self, user, song_id, fs_name, rel_path):
        """ set the location of the audio file for the song by song id

        user: the current user
        song_id: the song_id for the song to update
        rel_path: a relative path (sample.jpg)
        abs_path: an absolute path (s3://bucket/sample.jpg)
        """

        uid = user['id']
        did = user['domain_id']

        storage_path, size = self._getOrCreateFileEntry(
            user, song_id, fs_name, rel_path)

        song = {Song.path: storage_path, Song.file_size: size}
        self.libraryDao.update(uid, did, song_id, song)

    def setSongAlbumArtPath(self, user, song_id, fs_name, rel_path):
        """ set the location of the album art for the song by song id

        user: the current user
        song_id: the song_id for the song to update
        rel_path: a relative path (sample.jpg)
        abs_path: an absolute path (s3://bucket/sample.jpg)
        """

        uid = user['id']
        did = user['domain_id']

        storage_path, size = self._getOrCreateFileEntry(
            user, song_id, fs_name, rel_path)

        song = {Song.art_path: storage_path}
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
        offset=None,
        showBanished=False):
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
            orderby, limit, offset, showBanished)

        if shuffle:
            result = binshuffle(result, lambda s: s['artist'])[:limit_save]

        return result

    def search_forest(self, user,
        searchTerm,
        case_insensitive=True,
        showBanished=False):
        """ query the library and return a list of songs as a forest

        query results are restricted by the users domain and role
        """

        orderby = [Song.artist_key, Song.album, Song.title]
        limit = None
        offset = None

        songList = self.libraryDao.search(
            user['id'], user['domain_id'],
            searchTerm, case_insensitive,
            orderby, limit, offset, showBanished)

        # A Forset is list-of-ArtistItem
        # An ArtistItem is a {name: str, albums: list-of-AlbumItem}
        # An AlbumItem is a {name: str, tracks: list-of-TrackItem}
        # A TrackItem is a {title: str, id: str}

        artist = None
        album = None
        forest = []
        for song in songList:
            if artist is None or song[Song.artist] != artist['name']:
                artist = {'name': song[Song.artist], 'albums': []}
                forest.append(artist)

            if album is None or song[Song.album] != album['name']:
                album = {'name': song[Song.album], 'tracks': []}
                artist['albums'].append(album)

            songItem = {
            'id': song[Song.id],
            'title': song[Song.title],
            'length': song[Song.length],
            }
            album['tracks'].append(songItem)

        return forest

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

    def queueNext(self, user):
        """pop the head element and return the next song"""
        pass

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

        songs = (songs + new_songs)[:limit]

        song_ids = [song['id'] for song in songs]
        self.queueDao.set(user['id'], user['domain_id'], song_ids)

        return songs

    def updatePlayCount(self, user, records, updateHistory=True):
        """
        update the playcount for a list of songs, and record history.

        records: a list of objects containing a `song_id`, and `timestamp`.
        """

        for record in records:
            self.libraryDao.incrementPlaycount(
                user['id'], record['song_id'], commit=False)
            self.historyDao.insert(user['id'],
                                   record['song_id'],
                                   record['timestamp'],
                                   commit=False)
        self.db.session.commit()

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

    def getPathFromSong(self, user, song):
        """ returns a file path, if it exits

        """

        if not song:
            raise AudioServiceException("No song for id %s" % (song))

        path = song[Song.path]

        if not path or not self.fs.exists(path):
            raise FileNotFoundError("No audio for %s" % (song[Song.id]))

        return path





