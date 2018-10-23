
import os, sys
import logging

from .exception import AuthenticationError, LibraryException

from ...framework import gui
from ...dao.storage import StorageNotFoundException

class YueAppState(object):
    """docstring for YueAppState"""
    def __init__(self, userService, audioService, fileService):
        super(YueAppState, self).__init__()

        self.auth_token = None  # the user token
        self.auth_user = None  # the logged in user
        self.auth_info = None  # the user information

        self.userService = userService
        self.audioService = audioService
        self.fileService = fileService

        self.current_playlist = None

        self.execute = gui.Signal(str)
        self.login = gui.Signal(str)
        self.logout = gui.Signal()
        self.playlistChanged = gui.Signal()
        self.currentSongChanged = gui.Signal()

    def listroots(self):
        return self.fileService.getRoots(self.auth_user)

    def listdir(self, root, path):
        records = []

        try:
            result = self.fileService.listDirectory(self.auth_user, root, path)

            for name in result['directories']:
                records.append({'name': name, 'isDir': True})

            for item in result['files']:
                item['isDir'] = False
                records.append(item)

        except StorageNotFoundException as e:
            pass

        return records

    def renderContent(self, root, path):

        path = self.fileService.storageDao.absolutePath(
            self.auth_user['id'],
            self.auth_user['role_id'],
            root, path)

        with self.fileService.fs.open(path, "rb") as rb:
            return rb.read().decode("utf-8")

    def authenticate(self, username, password):

        try:
            # TODO: fix this, create a new token, return user
            print(username, password)
            self.auth_token = self.userService.loginUser(username, password)
            print(self.auth_token)
            self.auth_user = self.userService.getUserFromToken(self.auth_token)
            print(self.auth_user)
            self.auth_info = self.userService.listUser(self.auth_user['id'])
            print(self.auth_info)
        except Exception as e:
            logging.exception(e)
            self.auth_token = None
            self.auth_user = None
            raise AuthenticationError()

        self.login.emit(self.auth_token)

    def is_authenticated(self):
        """ returns true if the user is authenticated """
        return self.auth_token is not None

    def set_authentication(self, token):
        if token:
            # TODO: fix this, in testing, the database is recreated every run
            # the user token may be valid, but for an user with a different id
            user = self.userService.getUserFromToken(token)
            user = self.userService.userDao.findUserByEmail(user['email'])

            self.auth_token = token
            self.auth_user = user
            self.auth_info = self.userService.listUser(self.auth_user['id'])

    def get_user(self):
        if self.auth_user is None:
            raise AuthenticationError()
        return self.auth_user

    def clear_authentication(self):
        """delete information related to the logged in user"""
        self.auth_token = None
        self.auth_user = None
        self.auth_info = None
        self.logout.emit()

    def getDomainInfo(self):
        return self.audioService.getDomainSongUserInfo(self.auth_user)

    def search(self, query):
        return self.audioService.search(self.auth_user, query)

    def getCurrentSong(self):
        if self.current_playlist is None:
            self.current_playlist = self.audioService.getQueue(self.auth_user)
        if len(self.current_playlist) < 1:
            raise LibraryException("empty playlist")
        return self.current_playlist[0]

    def getPlaylist(self):
        if self.current_playlist is None:
            self.current_playlist = self.audioService.getQueue(self.auth_user)
        if len(self.current_playlist) < 1:
            raise LibraryException("empty playlist")
        return self.current_playlist

    def createPlaylist(self, query):
        results = self.audioService.search(self.auth_user, query, limit=50)
        self.current_playlist = results
        self.audioService.setQueue(self.auth_user, [song['id'] for song in results])
        self.playlistChanged.emit()

    def playlistPlayNext(self, index):
        if 0 < index < len(self.current_playlist):
            item = self.current_playlist.pop(index)
            self.current_playlist.insert(1, item)
            self.currentSongChanged.emit()

    def playlistDeleteSong(self, index):

        if index == 0:
            self.nextSong()
        elif 0 < index < len(self.current_playlist):
            self.current_playlist.pop(index)
            self.currentSongChanged.emit()

    def playlistInsertSong(self, index, song):

        if 0 <= index < len(self.current_playlist):
            self.current_playlist.insert(index, song)
        else:
            self.current_playlist.append(song)
        self.playlistChanged.emit()

    def nextSong(self):
        if self.current_playlist is None:
            self.current_playlist = self.audioService.getQueue(self.auth_user)
        if len(self.current_playlist) < 1:
            raise Exception("empty playlist")
        self.current_playlist.pop(0)
        self.currentSongChanged.emit()
        return self.current_playlist[0]