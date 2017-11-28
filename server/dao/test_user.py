import os
import unittest

from ..util import TestCase

from .user import UserDao

from ..app import app, db

class UserDaoTestCase(unittest.TestCase):

    def setUp(self):
        super().setUp()

    def tearDown(self):
        pass

    def test_queue_head(self):

        userDao = UserDao(db)

        domain_id = userDao.createDomain({'name': 'sample'})
        role_id = userDao.createRole({'name': 'sample'})

        user_id = userDao.createUser("test", "password", domain_id, role_id)

        domain = userDao.findDomainByName("sample")
        self.assertEqual(domain['name'], "sample")

        role = (userDao.findRoleByName("sample"))
        self.assertEqual(role['name'], "sample")

        user = userDao.findUserByEmail("test")
        self.assertEqual(user['email'], "test")
        self.assertEqual(user['domain_id'], domain_id)
        self.assertEqual(user['role_id'], role_id)

        user = userDao.findUserByEmailAndPassword("test", "password")
        self.assertEqual(user['email'], "test")

