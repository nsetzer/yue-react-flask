import os
import unittest

from .user import UserDao


from .db import db_connect

from sqlalchemy.exc import IntegrityError

class UserDaoTestCase(unittest.TestCase):

    db_name = "UserDaoTestCase"

    @classmethod
    def setUpClass(cls):
        # build a test database, with a minimal configuration
        cls.db_path = "database.test.%s.sqlite" % cls.db_name

        db = db_connect(None)

        db.create_all()

        cls.db = db

        cls.userDao = UserDao(db, db.tables)

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_domain(self):

        domain_id = self.userDao.createDomain("domain1")

        with self.assertRaises(IntegrityError):
            self.userDao.createDomain("domain1")

        domain = self.userDao.findDomainByName("domain1")
        self.assertEqual(domain['id'], domain_id)

        self.userDao.removeDomain(domain_id)

        domain = self.userDao.findDomainByName("domain1")
        self.assertIsNone(domain)

    def test_role(self):

        role_id = self.userDao.createRole("role1")

        with self.assertRaises(IntegrityError):
            self.userDao.createRole("role1")

        role = self.userDao.findRoleByName("role1")
        self.assertEqual(role['id'], role_id)

        self.userDao.removeRole(role_id)

        role = self.userDao.findRoleByName("role1")
        self.assertIsNone(role)

    def test_user(self):

        domain_id = self.userDao.createDomain('domain2')
        role_id = self.userDao.createRole('role2')

        user_id = self.userDao.createUser("user123", "password", domain_id, role_id)

        user = self.userDao.findUserByEmail("user123")
        self.assertEqual(user['email'], "user123")
        self.assertEqual(user['domain_id'], domain_id)
        self.assertEqual(user['role_id'], role_id)

        user = self.userDao.findUserByEmailAndPassword("user123", "password")
        self.assertEqual(user['email'], "user123")

        apikey = user['apikey']
        user = self.userDao.findUserByApiKey(apikey)
        self.assertEqual(user['email'], "user123")

        self.userDao.removeUser(user_id)
        user = self.userDao.findUserByEmail("user123")
        self.assertIsNone(user)

        self.userDao.removeRole(role_id)
        self.userDao.removeDomain(domain_id)

    def test_feature(self):

        domain_id = self.userDao.createDomain('domain3')
        role_id = self.userDao.createRole('role3')
        feat_id = self.userDao.createFeature('<create_user>')
        user_id = self.userDao.createUser("user234", "password", domain_id, role_id)

        self.userDao.addFeatureToRole(role_id, feat_id)

        self.assertTrue(self.userDao.roleHasFeature(role_id, feat_id))

        self.assertTrue(self.userDao.roleHasNamedFeature(role_id,
            '<create_user>'))

        self.userDao.removeFeatureFromRole(role_id, feat_id)

        self.assertFalse(self.userDao.roleHasFeature(role_id, feat_id))

        self.assertFalse(self.userDao.roleHasNamedFeature(role_id,
            '<create_user>'))


    def test_list_user(self):

        domain_id = self.userDao.createDomain('domain_list')
        role_id = self.userDao.createRole('role_list')
        user_id = self.userDao.createUser("user_list", "password", domain_id, role_id)


        result = self.userDao.listUsers(domain_id)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['email'], "user_list")

def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(UserDaoTestCase)
    unittest.TextTestRunner().run(suite)

if __name__ == '__main__':
    main()