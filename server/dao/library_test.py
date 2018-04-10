import os
import unittest
import tempfile
import json
import time

from .db import db_init_main, db_connect

from .user import UserDao
from .library import Song, LibraryDao, LibraryException

class LibraryTestCase(unittest.TestCase):

    db_name = "LibraryTestCase"

    @classmethod
    def setUpClass(cls):
        # build a test database, with a minimal configuration
        cls.db_path = "database.test.%s.sqlite" % cls.db_name

        db = db_connect(None)

        env_cfg = {
            'features': ['test', ],
            'domains': ['test'],
            'roles': [
                {'test': { 'features': ['all',]}},
            ],
            'users': [
                {'email': 'user000',
                 'password': 'user000',
                 'domains': ['test'],
                 'roles': ['test']},
                {'email': 'user001',
                 'password': 'user001',
                 'domains': ['test'],
                 'roles': ['test']},
                {'email': 'user002',
                 'password': 'user002',
                 'domains': ['test'],
                 'roles': ['test']},
            ]
        }

        db_init_main(db, db.tables, env_cfg)

        cls.userDao = UserDao(db, db.tables)

        cls.USERNAME = "user000"
        cls.USER = cls.userDao.findUserByEmail(cls.USERNAME)

        cls.libraryDao = LibraryDao(db, db.tables)

        cls.songs = []
        for a in range(3):
            for b in range(3):
                for t in range(3):
                    song = {
                        Song.artist: "Artist%03d" % a,
                        Song.album: "Album%03d" % b,
                        Song.title: "Title%03d" % t,
                        Song.ref_id: "id%06d" % len(cls.songs),
                    }
                    cls.songs.append(song)

        cls.db = db

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_001_get_song_by_id(self):

        user_id = self.USER['id']
        domain_id = self.USER['domain_id']

        song = {
            "artist": "test",
            "title": "test",
            "album": "test",
        }

        uid = self.libraryDao.insert(user_id, domain_id, song)

        # show that we can find a song given an ID
        song2 = self.libraryDao.findSongById(user_id, domain_id, uid)
        for key, value in song.items():
            self.assertEqual(song2[key], song[key], key)
        self.assertEqual(song2['id'], uid, "id")

        # test domain filter
        song3 = self.libraryDao.findSongById(user_id, -1, uid)
        self.assertIsNone(song3)

    def test_002a_insert_no_artist(self):

        user_id = self.USER['id']
        domain_id = self.USER['domain_id']

        song = {
            Song.album: "test",
            Song.title: "test",
        }

        with self.assertRaises(LibraryException):
            self.libraryDao.insert(user_id, domain_id, song)

    def test_002b_insert_no_albumt(self):

        user_id = self.USER['id']
        domain_id = self.USER['domain_id']

        song = {
            Song.artist: "test",
            Song.title: "test",
        }

        with self.assertRaises(LibraryException):
            self.libraryDao.insert(user_id, domain_id, song)

    def test_002c_insert_no_title(self):

        user_id = self.USER['id']
        domain_id = self.USER['domain_id']

        song = {
            Song.artist: "test",
            Song.album: "test",
        }

        with self.assertRaises(LibraryException):
            self.libraryDao.insert(user_id, domain_id, song)

    def test_003_insert_songs(self):
        user_id = self.USER['id']
        domain_id = self.USER['domain_id']

        for song in self.songs:
            self.libraryDao.insert(user_id, domain_id, song, commit=False)

        self.db.session.commit()

    def test_003a_all_text_search(self):
        user_id = self.USER['id']
        domain_id = self.USER['domain_id']

        songs = self.libraryDao.search(user_id, domain_id, "Artist000")

        self.assertEqual(len(songs), 9)

        for song in songs:
            self.assertEqual(song[Song.artist], "Artist000")

    def test_003b_simple_search(self):
        user_id = self.USER['id']
        domain_id = self.USER['domain_id']

        songs = self.libraryDao.search(user_id, domain_id, "art=Artist000")

        self.assertEqual(len(songs), 9)

        for song in songs:
            self.assertEqual(song[Song.artist], "Artist000")

    def test_003c_search_limit(self):
        user_id = self.USER['id']
        domain_id = self.USER['domain_id']
        limit = 4

        songs = self.libraryDao.search(user_id, domain_id,
            "Artist000", limit=limit)

        self.assertEqual(len(songs), limit)

        for song in songs:
            self.assertEqual(song[Song.artist], "Artist000")

    def test_003d_search_order_string(self):

        user_id = self.USER['id']
        domain_id = self.USER['domain_id']

        songs = self.libraryDao.search(user_id, domain_id,
            "Artist", orderby="artist")

        songs2 = [s['artist'] for s in songs]
        songs2.sort()

        for s1, s2 in zip(songs, songs2):
            self.assertEqual(s1['artist'], s2)

    def test_003e_search_order_forward(self):

        user_id = self.USER['id']
        domain_id = self.USER['domain_id']

        songs = self.libraryDao.search(user_id, domain_id,
            "Artist", orderby=[("artist", "ASC")])

        songs2 = [s['artist'] for s in songs]
        songs2.sort()

        for s1, s2 in zip(songs, songs2):
            self.assertEqual(s1['artist'], s2)

    def test_003f_search_order_reverse(self):

        user_id = self.USER['id']
        domain_id = self.USER['domain_id']

        songs = self.libraryDao.search(user_id, domain_id,
            "Artist", orderby=[("artist", "DESC")])

        songs2 = [s['artist'] for s in songs]
        songs2.sort(reverse=True)

        for s1, s2 in zip(songs, songs2):
            self.assertEqual(s1['artist'], s2)

    def test_003_insert_update_by_refid(self):

        user_id = self.USER['id']
        domain_id = self.USER['domain_id']

        song = {
            Song.artist: "test",
            Song.album: "test",
            Song.title: "test",
            Song.ref_id: 1474,
        }

        song_id = self.libraryDao.insertOrUpdateByReferenceId(
            user_id, domain_id, song[Song.ref_id], song)

        song2 = self.libraryDao.findSongById(user_id, domain_id, song_id)
        self.assertEqual(song2[Song.artist], song[Song.artist])

        song[Song.artist] = "test2"

        song_id2 = self.libraryDao.insertOrUpdateByReferenceId(
            user_id, domain_id, song[Song.ref_id], song)

        # a new song record should not be created
        self.assertEqual(song_id, song_id2)

        song3 = self.libraryDao.findSongById(user_id, domain_id, song_id)
        s= "%s=%s" % (song3[Song.artist], song[Song.artist])
        self.assertEqual(song3[Song.artist], song[Song.artist], s)

    def test_003a_bulk_upsert(self):

        # generate 1000 songs to insert
        songs = []
        for a in range(10):
            for b in range(10):
                for t in range(10):
                    song = {
                        Song.artist: "bulk%03d" % a,
                        Song.album: "bulk%03d" % b,
                        Song.title: "bulk%03d" % t,
                        Song.ref_id: "bulk%06d" % len(songs),
                    }
                    songs.append(song)

        # first upsert inserts 1000 records
        s = time.time()
        self.libraryDao.bulkUpsertByRefId( \
            self.USER['id'], self.USER['domain_id'], songs)
        e = time.time()
        #print( len(songs), len(songs)/(e-s), (e-s) )

        # second upsert updates the values instead
        s = time.time()
        self.libraryDao.bulkUpsertByRefId( \
            self.USER['id'], self.USER['domain_id'], songs)
        e = time.time()
        #print( len(songs), len(songs)/(e-s), (e-s) )

        #TODO: build a performance benchmark test
        # this test should write to stderr if the performance
        # changes between runs. cache results to the local file system
        return

    def test_003b_insert_and_update(self):
        # insert a song with user data for user000
        # update the song with user data for user001
        # verify that the user000 data is unchanged
        # verify that the user001 data is inserted correctly
        # the first insert should create two rows
        # the next update should update one row (song data)
        #    and insert one row (user data)
        # verify that the update falls back to an insert when the user data
        # row does not exist

        user000 = self.userDao.findUserByEmail("user000")
        user001 = self.userDao.findUserByEmail("user001")

        user_id = self.USER['id']
        domain_id = self.USER['domain_id']

        song = {
            "artist": "test",
            "title": "test",
            "album": "test",
            "rating": 5
        }

        song_id = self.libraryDao.insert(
            user000['id'], user000['domain_id'], song)

        song["rating"] = 3
        song["artist"] = "test2"
        self.libraryDao.update(
            user001['id'], user001['domain_id'], song_id, song)

        song000 = self.libraryDao.search(
            user000['id'], user000['domain_id'], "id=%s" % song_id)[0]

        song001 = self.libraryDao.search(
            user001['id'], user001['domain_id'], "id=%s" % song_id)[0]

        self.assertEqual(song000["artist"], "test2")
        self.assertEqual(song001["artist"], "test2")

        self.assertEqual(song000["rating"], 5)
        self.assertEqual(song001["rating"], 3)

    def test_004a_search_blocked(self):

        user000 = self.userDao.findUserByEmail("user000")

        song = {
            Song.artist: "test",
            Song.album: "test",
            Song.title: "test",
            Song.blocked: 1,
        }

        song_id = self.libraryDao.insert(
            user000['id'], user000['domain_id'], song)

        songs = self.libraryDao.search(
            user000['id'], user000['domain_id'], "id=%s" % song_id,
            showBanished=True, debug=False)

        self.assertEqual(len(songs), 1)

        songs = self.libraryDao.search(
            user000['id'], user000['domain_id'], "id=%s" % song_id,
            showBanished=False, debug=False)

        self.assertEqual(len(songs), 0)

    def test_004b_search_banished(self):

        user000 = self.userDao.findUserByEmail("user000")

        song = {
            Song.artist: "test",
            Song.album: "test",
            Song.title: "test",
            Song.banished: 1,
        }

        song_id = self.libraryDao.insert(
            user000['id'], user000['domain_id'], song)

        songs = self.libraryDao.search(
            user000['id'], user000['domain_id'], "id=%s" % song_id,
            showBanished=True, debug=False)

        self.assertEqual(len(songs), 1)

        songs = self.libraryDao.search(
            user000['id'], user000['domain_id'], "id=%s" % song_id,
            showBanished=False, debug=False)

        self.assertEqual(len(songs), 0)

    def test_005_domain_info(self):

        user_id = self.USER["id"]
        domain_id = self.userDao.createDomain("test_info", commit=False)
        self.userDao.grantDomain(user_id, domain_id, commit=False)

        # create a set of songs
        # every artist gets 3 albums, every album has 3 songs
        # the three songs are either normal, banished by domain
        # or blocked by the user

        for a in range(3):
            for b in range(3):
                for t in range(3):
                    song = {
                        Song.artist: "Artist%03d" % a,
                        Song.album: "Album%03d" % b,
                        Song.title: "Title%03d" % t,
                        Song.genre: "Genre%03d" % a,

                    }

                    if t==1:
                        song[Song.blocked] = 1

                    if t==2:
                        song[Song.banished] = 1

                    self.libraryDao.insert(user_id, domain_id, song, commit=False)

        # an extra song with no genre
        song = {
            Song.artist: "extra",
            Song.album: "extra",
            Song.title: "extra",
        }
        self.libraryDao.insert(user_id, domain_id, song, commit=False)

        self.db.session.commit()


        # check that the domain info contains the correct fields
        # domain info should include songs blocked by the user
        info = self.libraryDao.domainSongInfo(domain_id)

        self.assertTrue("artists" in info)
        for art_info in info["artists"]:
            self.assertTrue("name" in art_info)
            if art_info["name"] == "extra":
                continue
            self.assertEqual(art_info["count"], 6)
            self.assertEqual(len(art_info["albums"]), 3)
            self.assertTrue("genres" in art_info)


        self.assertTrue("genres" in info)
        for gen_info in info["genres"]:
            self.assertEqual(gen_info["count"], 6)
            self.assertEqual(gen_info["artist_count"], 1)
            self.assertTrue("name" in art_info)

        self.assertTrue("num_songs" in info)
        self.assertEqual(info["num_songs"], 3 * 3 * 2 + 1)

        # check that the domain info contains the correct fields
        # domain info should not include songs blocked or banished
        info = self.libraryDao.domainSongUserInfo(user_id, domain_id)

        self.assertTrue("artists" in info)
        for art_info in info["artists"]:
            self.assertTrue("name" in art_info)
            if art_info["name"] == "extra":
                continue
            self.assertEqual(art_info["count"], 3)
            self.assertEqual(len(art_info["albums"]), 3)
            self.assertTrue("genres" in art_info)

        self.assertTrue("genres" in info)
        for gen_info in info["genres"]:
            self.assertEqual(gen_info["count"], 3)
            self.assertEqual(gen_info["artist_count"], 1)
            self.assertTrue("name" in art_info)

        self.assertTrue("num_songs" in info)
        self.assertEqual(info["num_songs"], 3 * 3 + 1)

    def test_006_search_by_genre(self):

        user_id = self.USER['id']
        domain_id = self.USER['domain_id']
        song = {
            Song.artist: "test",
            Song.album: "test",
            Song.title: "test",
        }

        song_ids = []
        for g in ["rock", "punk, rock", "punk rock"]:
            song[Song.genre] = g

            song_id = self.libraryDao.insert(user_id, domain_id, song)
            song_ids.append(song_id)

        songs = self.libraryDao.search(user_id, domain_id, "gen=rock")
        self.assertEqual(len(songs), 3)

        # does not match 'punk rock'
        songs = self.libraryDao.search(user_id, domain_id, "gen=;rock;")
        self.assertEqual(len(songs), 2)

        songs = self.libraryDao.search(user_id, domain_id, 'gen="punk rock"')
        self.assertEqual(len(songs), 1)

        songs = self.libraryDao.search(user_id, domain_id, 'gen=";punk rock;"')
        self.assertEqual(len(songs), 1)

def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(LibraryTestCase)
    unittest.TextTestRunner().run(suite)

if __name__ == '__main__':
    main()