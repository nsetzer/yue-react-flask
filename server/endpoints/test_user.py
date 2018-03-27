import os
import unittest
import tempfile
import json

from ..util import TestCase

from ..dao.user import UserDao

from ..app import app, db, dbtables

class LibraryEndpointTestCase(TestCase):

    def setUp(self):
        super().setUp()

        self.userDao = UserDao(db, dbtables)

    def tearDown(self):
        pass

    def test_list_domain(self):

        app = self.login(self.USERNAME, self.PASSWORD)

        user_id = self.USER['id']
        domain_id = self.USER['domain_id']

        domain = self.userDao.findDomainById(domain_id)

        users = app.get_json("/api/user/list/domain/%s" % domain['name'])
        self.assertGreater(len(users), 0)

        user_info = app.get_json("/api/user/list/user/%s" % self.USER['id'])
        self.assertTrue("default_domain" in user_info)
        self.assertTrue("default_role" in user_info)
        self.assertTrue("domains" in user_info)
        self.assertTrue("roles" in user_info)
        self.assertTrue("email" in user_info)