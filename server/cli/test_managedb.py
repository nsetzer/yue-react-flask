import os
import unittest
import tempfile
import json

from .config import db_init, db_update
from .managedb import db_connect, db_populate
from ..dao.user import UserDao
from ..dao.library import Song, LibraryDao

class ManageDBTestCase(unittest.TestCase):

    def setUp(self):
        super().setUp()

        #self.USERNAME = "user000"
        #self.USER = self.userDao.findUserByEmail(self.USERNAME)

    def tearDown(self):
        pass

    def test_db_populate(self):

        db_path = "database.test.sqlite"

        if os.path.exists(db_path):
            os.remove(db_path)

        db = db_connect("sqlite:///" + db_path)

        # TODO: remove dependency on a config file on disk
        db_init(db, db.tables, "config/test/env.yml")

        userDao = UserDao(db, db.tables)
        libraryDao = LibraryDao(db, db.tables)

        roles = userDao.listRoles()
        self.assertTrue(len(roles) > 0)

        domains = userDao.listDomains()
        self.assertTrue(len(domains) > 0)

        for domain in domains:
            users = userDao.listUsers(domain.id)
            self.assertTrue(len(users) > 0)

        songs = []
        for i in range(10):
            song = {
                Song.artist : "artist%d" % i,
                Song.title : "album%d" % i,
                Song.album : "title%d" % i,
                Song.rating : i%10,
                Song.path : "/dev/null"
            }
            songs.append(song)

        user = userDao.findUserByEmail("user000")
        domain_name = userDao.findDomainById(user['domain_id'])['name']

        results = libraryDao.search(user['id'], user['domain_id'], "")
        db_populate(db, db.tables, user['email'], domain_name, songs)

        results = libraryDao.search(user['id'], user['domain_id'], "")

        #for song in results:
        #    print("%s %s %s %s %s" % (song["id"][:6], song['artist'],
        #        song['album'], song['title'], song[Song.path]))

        self.assertEqual(len(results), len(songs),
            "%d/%d" % (len(results), len(songs)))

    def test_db_repopulate(self):
        return

def main():
    test = ManageDBTestCase()
    test.test_db_populate()
