import os
import unittest
import json
import time

from ..app import TestApp

class UserResourceTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        cls.app = TestApp(cls.__name__);

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
            self.assertEqual(result.status_code, 200, result)
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
            self.assertEqual(result.status_code, 200, result)
            data = json.loads(result.data.decode("utf-8"))

            self.assertTrue("result" in data)

            user_info = data['result']

            self.assertTrue('email' in user_info)
            self.assertEqual(user_info['email'], username)

    def test_change_password(self):
        """ show that a user can change their password
        """
        username = "user000"
        new_password = {"password": "testxyz"}
        with self.app.login(username, username) as app:
            result = app.put_json('/api/user/password', new_password)
            self.assertEqual(result.status_code, 200, result)
            data = json.loads(result.data.decode("utf-8"))

        # change it back for later tests
        new_password = {"password": username}
        with self.app.login(username, "testxyz") as app:
            result = app.put_json('/api/user/password', new_password)
            self.assertEqual(result.status_code, 200, result)
            data = json.loads(result.data.decode("utf-8"))

    def test_change_password_not_authorized(self):
        """ without write permisson a user cannot change their password
        """
        username = "null"
        new_password = {"password": "testxyz"}
        with self.app.login(username, username) as app:
            result = app.put_json('/api/user/password', new_password)
            self.assertEqual(result.status_code, 401, result)

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
            self.assertEqual(result.status_code, 200, result)
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

    def test_list_user(self):

        user_id = self.app.USER['id']

        with self.app.login("admin", "admin") as app:
            result = app.get('/api/user/list/user/%s' % user_id)
            self.assertEqual(result.status_code, 200)
            data = json.loads(result.data.decode("utf-8"))
            self.assertTrue('result' in data)

            user_info = data['result']

            # TODO: may want to test that more fields are correct
            self.assertEqual(user_info['email'], self.app.USER['email'])

    def test_list_domain_users(self):

        domain = self.app.TEST_DOMAIN

        with self.app.login("admin", "admin") as app:
            result = app.get('/api/user/list/domain/%s' % domain)
            self.assertEqual(result.status_code, 200)
            data = json.loads(result.data.decode("utf-8"))
            self.assertTrue('result' in data)
            domain_info = data['result']

            self.assertTrue('domains' in domain_info)
            self.assertTrue('roles' in domain_info)
            self.assertTrue('users' in domain_info)


def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(UserResourceTestCase)
    unittest.TextTestRunner().run(suite)

if __name__ == '__main__':
    main()
