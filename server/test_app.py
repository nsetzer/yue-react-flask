import os
import unittest
import tempfile
import json

from .util import TestCase

class AppTestCase(TestCase):

    def setUp(self):
        super().setUp()

    def tearDown(self):
        pass

    def test_token_login(self):
        """
        login in and authenticated apis

        A test which first logs the user in, and then
        attempts to request information about the user
        """
        email = "user000"
        password = "user000"
        app = self.login(email, password)

        res = app.get("/api/user")
        body = json.loads(res.data.decode("utf-8"))

        self.assertEqual(res.status_code, 200)
        self.assertTrue("email" in body['result'])
        self.assertTrue("domain_id" in body['result'])
        self.assertTrue("role_id" in body['result'])
        self.assertTrue("password" not in body['result'])

        user = body['result']
        self.assertEqual(user['email'], email)

    def test_basic_login(self):
        """
        login in and authenticated apis

        A test which first logs the user in, and then
        attempts to request information about the user
        """
        email = "user000"
        password = "user000"
        app = self.login_basic(email, password)

        res = app.get("/api/user")
        body = json.loads(res.data.decode("utf-8"))

        self.assertEqual(res.status_code, 200)
        self.assertTrue("email" in body['result'])
        self.assertTrue("domain_id" in body['result'])
        self.assertTrue("role_id" in body['result'])
        self.assertTrue("password" not in body['result'])

        user = body['result']
        self.assertEqual(user['email'], email)

    def test_apikey_login(self):
        """
        login in and authenticated apis

        A test which first logs the user in, and then
        attempts to request information about the user
        """
        email = self.USER['email']
        apikey = self.USER['apikey']
        app = self.login_apikey(apikey)

        res = app.get("/api/user")
        body = json.loads(res.data.decode("utf-8"))

        self.assertEqual(res.status_code, 200)
        self.assertTrue("email" in body['result'])
        self.assertTrue("domain_id" in body['result'])
        self.assertTrue("role_id" in body['result'])
        self.assertTrue("password" not in body['result'])

        user = body['result']
        self.assertEqual(user['email'], email)

    def test_login_fail(self):
        """
        fail to log in

        A test which shows that an invalid password generates an error
        """
        body = {
            "email": "user000",
            "password": "invalid+password",
        }
        res = self.app.post('/api/user/login',
                            data=json.dumps(body),
                            content_type='application/json')
        self.assertEqual(res.status_code, 403)

