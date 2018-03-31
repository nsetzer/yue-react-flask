import os
import unittest
import json
import time

from ..app import TestApp

class UserResourceTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        cls.app = TestApp(cls.__name__);

        cls.app.add_resource(cls.app.resource_user)

    @classmethod
    def tearDownClass(cls):
        cls.app.tearDown()

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_login(self):

        body = {
            "email": "user000",
            "password": "user000",
        }

        with self.app.test_client() as app:
            result = app.post('/api/user/login',
                             data=json.dumps(body),
                             content_type='application/json')
            self.assertEqual(result.status_code, 200)
            data = json.loads(result.data.decode("utf-8"))
            self.assertTrue("token" in data)

            token = data['token']

            isok, _ = self.app.user_service.verifyToken(token)

            self.assertTrue(isok)

    def test_get_user_by_token(self):
        """ show that a user can log in, and make requests
        """
        username = "user000"
        token = self.app.user_service.loginUser(username, username)
        headers = {"Authorization": token}

        with self.app.test_client() as app:
            result = app.get('/api/user',
                             headers=headers)
            self.assertEqual(result.status_code, 200)
            data = json.loads(result.data.decode("utf-8"))

            self.assertTrue("result" in data)

            user_info = data['result']

            self.assertTrue('email' in user_info)
            self.assertEqual(user_info['email'], username)

    def test_get_user_by_token_v2(self):
        """ show that a user can log in, and make requests
        this uses the login convenience function for testing
        """
        username = "user000"
        with self.app.login(username, username) as app:
            result = app.get('/api/user')
            self.assertEqual(result.status_code, 200)
            data = json.loads(result.data.decode("utf-8"))

            self.assertTrue("result" in data)

            user_info = data['result']

            self.assertTrue('email' in user_info)
            self.assertEqual(user_info['email'], username)


    def test_create_user(self):

        body = {
            "email": "test_create",
            "password": "test",
            "domain": self.app.TEST_DOMAIN,
            "role": self.app.TEST_ROLE,
        }

        with self.app.login("admin", "admin") as app:
            result = app.post('/api/user/create',
                             data=json.dumps(body),
                             content_type='application/json')
            self.assertEqual(result.status_code, 200)
            data = json.loads(result.data.decode("utf-8"))
            self.assertTrue("id" in data)

            # TODO: verify the user exists with the returned id

    def test_create_user_not_authorized(self):

        body = {
            "email": "test_create2",
            "password": "test",
            "domain": self.app.TEST_DOMAIN,
            "role": self.app.TEST_ROLE,
        }

        with self.app.test_client() as app:
            result = app.post('/api/user/create',
                             data=json.dumps(body),
                             content_type='application/json')
            self.assertEqual(result.status_code, 401)

def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(UserResourceTestCase)
    unittest.TextTestRunner().run(suite)

if __name__ == '__main__':
    main()
