
import os, sys, io
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

        self.note_filesystem = "default"

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

    def getFilePath(self, root, path):

        path = self.fileService.getStoragePath(
            self.auth_user, root, path)

        return path

    def renderContent(self, root, path):

        path = self.getFilePath(root, path)

        with self.fileService.fs.open(path, "rb") as rb:
            return rb.read().decode("utf-8")

    def authenticate(self, username, password):

        try:
            # TODO: fix this, create a new token, return user
            self.auth_token = self.userService.loginUser(username, password)
            self.auth_user = self.userService.getUserFromToken(self.auth_token)
            self.auth_info = self.userService.listUser(self.auth_user['id'])
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
        """
        set the authentication token for this session.
        validate that the token is valid

        returns true if the token is valid and the user exists.
        """
        logging.warning("setting auth %s" % token)
        if token:
            try:
                data = self.userService.getUserFromToken(token)
                user = self.userService.userDao.findUserByEmail(data['email'])
                info = self.userService.listUser(user['id'])
                self.auth_info = info
                self.auth_user = user
                self.auth_token = token
                return True
            except Exception as e:
                logging.error(e)
                self.auth_info = None
                self.auth_token = None
                self.auth_user = None
        return False

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

    def publicFileInfo(self, public_id):

        return self.fileService.publicFileInfo(public_id)

    def listNotes(self):
        """
        returns meta data describing notes
        """
        try:
            notes = self.fileService.getUserNotes(
                self.auth_user, self.note_filesystem, "public/notes")

            for note in notes:
                note['name'] = note['file_name'][:-4].replace("_", " ")
                try:
                    note['content'] = self.getNoteContent(note['file_path'])
                except Exception as e:
                    print(e)
                    note['content'] = ''

            return notes
        except StorageNotFoundException:
            return []

    def getNoteContent(self, filepath):
        """
        notes are lightly structured text files
        each line is a separate list item
        """

        stream = self.fileService.loadFile(self.auth_user, self.note_filesystem, filepath)

        try:
            content = stream.read() \
                .decode("utf-8") \
                .replace("\r", "")
            return content
        finally:
            stream.close()

    def setNoteContent(self, filepath, content):

        stream = io.BytesIO()
        stream.write(content.encode("utf-8"))
        if not content.endswith("\n"):
            stream.write(b"\n")
        stream.seek(0)

        stream = self.fileService.encryptStream(
            self.auth_user, None, stream, "rb", "system")

        self.fileService.saveFile(self.auth_user, self.note_filesystem, filepath,
            stream, encryption="system")

    def removeNote(self, filepath):

        self.fileService.remove(self.auth_user, self.note_filesystem, filepath)
