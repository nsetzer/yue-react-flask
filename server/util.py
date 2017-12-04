
import os, sys
import unittest
import json

from .app import app, db, dbtables
from .dao.user import UserDao
from .dao.library import Song, LibraryDao
from .endpoints.util import generate_basic_token
import traceback

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

            cls.userDao = UserDao(db, dbtables)

            cls.USERNAME = "user000"
            cls.PASSWORD = "user000"
            cls.USER = cls.userDao.findUserByEmail(cls.USERNAME)

            cls.LIBRARY = LibraryDao(db, dbtables)

            # , orderby=("artist", "album", "title")
            cls.SONGS = [song['id'] for song in
                cls.LIBRARY.search(cls.USER['id'], cls.USER['domain_id'],
                    None)]

            cls.SONG = cls.LIBRARY.findSongById(
                    cls.USER['id'],
                    cls.USER['domain_id'],
                    cls.SONGS[0])

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
    traceback.print_exc()






