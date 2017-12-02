
import os, sys
import unittest
import json

from .app import app, db, dbtables, db_reset
from .dao.user import UserDao
from .dao.library import Song, LibraryDao
from .endpoints.util import generate_basic_token

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
    def setUpTest(cls):
        """
        init database for tests.
        this is run once before any test
        """
        with app.test_client():
            db_reset()

            cls.userDao = UserDao(db, dbtables)

            cls.USERNAME = "user000"
            cls.PASSWORD = "user000"
            cls.USER = cls.userDao.findUserByEmail(cls.USERNAME)

            try:
                cls.LIBRARY = LibraryDao(db, dbtables)

                songs = []
                for a in range(3):
                    for b in range(3):
                        for t in range(3):
                            song = {
                                "artist": "Artist%03d" % a,
                                "album": "Album%03d" % b,
                                "title": "Title%03d" % t,
                            }
                        songs.append(cls.LIBRARY.insert(
                            cls.USER['id'],
                            cls.USER['domain_id'],
                            song))

                cls.SONGS = songs
                cls.SONG = cls.LIBRARY.findSongById(
                    cls.USER['id'],
                    cls.USER['domain_id'],
                    songs[0])
            except Exception as e:
                sys.stderr.write("%s\n"%(e))
            print("done")

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
        data = json.loads(res.data.decode("utf-8"))
        return AuthAppWrapper(self.app, data['token'])

    def login_basic(self, email, password):
        """
        Attempt to generate a session token for the given user.
        returns a new Application wrapper, which automatically
        sends the authentication token with any request.
        """
        token = generate_basic_token(email, password)
        return AuthAppWrapper(self.app, token)

try:
    TestCase.setUpTest()
except Exception as e:
    sys.stderr.write("TestCase Error: %s\n"%(e))






