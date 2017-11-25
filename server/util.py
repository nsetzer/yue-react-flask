
import unittest
import json

from .app import app, db, db_reset
from .models.user import User
from .models.song import Song, Library

class AuthAppWrapper(object):
    """docstring for AuthAppWrapper"""
    def __init__(self, app, token):
        super(AuthAppWrapper, self).__init__()
        self.app = app
        self.token = token

    def get(self, *args, **kwargs):
        return self._wrapper(self.app.get, args, kwargs)

    def post(self, *args, **kwargs):
        return self._wrapper(self.app.post, args, kwargs)

    def put(self, *args, **kwargs):
        return self._wrapper(self.app.put, args, kwargs)

    def delete(self, *args, **kwargs):
        return self._wrapper(self.app.delete, args, kwargs)

    def _wrapper(self, method, args, kwargs):
        if "headers" not in kwargs:
            kwargs['headers'] = {}
        if "Authorization" not in kwargs['headers']:
            kwargs['headers']['Authorization'] = self.token
        return method(*args, **kwargs)


class TestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with app.test_client():
            db_reset()

            cls.USERNAME = "user000"
            cls.USER = User.get_user_with_email(cls.USERNAME)

            cls.LIBRARY = Library(cls.USER.id, cls.USER.domain_id)

            songs = []
            for a in range(3):
                for b in range(3):
                    for t in range(3):
                        song = {
                            "artist" : "Artist%03d"%a,
                            "album" : "Album%03d"%b,
                            "title" : "Title%03d"%t,
                        }
                    songs.append(cls.LIBRARY.insert(song))

            cls.SONGS = songs
            cls.SONG = cls.LIBRARY.findSongById(songs[0])

            if cls.SONG is None:
                raise Exception(songs[0])

    def setUp(self):
        app.testing = True
        self.app = app.test_client()

    def login(self, email, password):
        """
        Attempt to generate a session token for the given user.
        returns a new Application wrapper, which automatically
        sends the authentication token with any request.
        """
        body = {
            "email": email,
            "password": password,
        }
        res = self.app.post('/api/user/login',
                            data=json.dumps(body),
                            content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        return AuthAppWrapper(self.app, data['token'])