
import os, sys

if (sys.version_info[0] == 2):
    raise RuntimeError("python2 not supported")

from yue.core.sqlstore import SQLStore
from yue.core.library import Library as YueLibrary
from yue.core.song import Song as YueSong, get_album_art, ArtNotFound

from server.app import app, db, dbtables, db_init

from server.dao.user import UserDao
from server.dao.library import Song, LibraryDao

import time
import datetime

from sqlalchemy import and_, or_, select

from server.service.audio_service import AudioService

userDao = UserDao(db, dbtables)
libraryDao = LibraryDao(db, dbtables)

text_fields = {
    YueSong.path: Song.path,
    YueSong.artist: Song.artist,
    YueSong.artist_key: Song.artist_key,
    YueSong.composer: Song.composer,
    YueSong.album: Song.album,
    YueSong.title: Song.title,
    YueSong.genre: Song.genre,
    YueSong.country: Song.country,
    YueSong.lang: Song.language,
}

number_fields = {
    YueSong.album_index: Song.album_index,
    YueSong.length: Song.length,
    YueSong.equalizer: Song.equalizer,
    YueSong.year: Song.year,

}

date_fields = {
    YueSong.last_played: Song.last_played,
    YueSong.date_added: Song.date_added
}

user_fields = {
    YueSong.rating: Song.rating,
    YueSong.play_count: Song.play_count,
    YueSong.skip_count: Song.skip_count,
    YueSong.blocked: Song.blocked,
    YueSong.comment: Song.comment,
    YueSong.frequency: Song.frequency
}

all_fields = {}
all_fields.update(text_fields)
all_fields.update(number_fields)
all_fields.update(date_fields)
all_fields.update(user_fields)

def migrate(username, domain_name, dbpath):

    domain = userDao.findDomainByName(domain_name)
    if domain is None:
        sys.stdout.write("Domain with name `%s` not found" % domain_name)
        sys.exit(1)

    sqlstore = SQLStore(dbpath)
    yueLib = YueLibrary(sqlstore)

    user = userDao.findUserByEmail(username)

    print("Migrating Database:")
    start = time.time()
    for song in yueLib.search(None):
        new_song = {v: song[k] for k, v in all_fields.items()}
        new_song[Song.ref_id] = song[YueSong.uid]

        try:
            temp_path = os.path.splitext(song[YueSong.path])[0] + ".jpg"
            art_path = get_album_art(song[YueSong.path], temp_path)
            new_song[Song.art_path] = art_path
        except ArtNotFound as e:
            pass

        song_id = libraryDao.insertOrUpdateByReferenceId(
            user.id, domain.id, song[YueSong.uid], new_song, commit=False)
    db.session.commit()

    end = time.time()

    t = end - start
    print("migrated %d songs in %.3f seconds" % (len(yueLib), t))

def test():

    username = "nsetzer"
    username = "user000"
    domain_name = app.config['DEFAULT_DOMAIN']

    domain = Domain.findDomainByName(domain_name)
    if domain is None:
        sys.stdout.write("Domain with name `%s` not found" % domain_name)
        sys.exit(1)

    g = SongSearchGrammar()

    user = User.get_user_with_email(username)
    lib = Library(user.id, domain.id)

    songs = lib.search("art=beast", limit=3, orderby="RANDOM")

    for song in songs:
        print(song['title'])


def main():

    mode = sys.argv[1]

    username = 'nsetzer'
    domain_name = app.config['DEFAULT_DOMAIN']
    role_name = "admin"
    dbpath = "/home/nsetzer/projects/android/YueMusicPlayer/yue.db"
    if not os.path.exists(dbpath):
        dbpath = "/Users/nsetzer/Music/Library/yue.db"

    if mode == 'migrate':
        migrate(username, dbpath)

    elif mode == "create":

        db_init()

        userDao = UserDao(db, dbtables)

        domain = userDao.findDomainByName(domain_name)
        if domain is None:
            sys.stdout.write("Domain with name `%s` not found" % domain_name)
            sys.exit(1)
        role = userDao.findRoleByName(role_name)
        if role is None:
            sys.stdout.write("Role with name `%s` not found" % role_name)
            sys.exit(1)
        username = "nsetzer"
        password = "nsetzer"

        user = userDao.createUser(username, password, domain.id, role.id)
        sys.stdout.write("Creating User: %s@%s/%s\n" % (username, domain.name, role.name))

        migrate(username, domain_name, dbpath)

    elif mode == "test":
        # test()
        userDao = UserDao(db, dbtables)
        user = userDao.findUserByEmail("user000")
        results = AudioService.instance().search(user, "beast", limit=5)
        for song in results:
            print("/api/library/%s/audio" % song['id'])
            uid = song['id']

        print("""
curl -u user000:user000 \\
  http://localhost:4200/api/library/%s/audio \\
  -o out.mp3

curl -u user000:user000 \\
  http://localhost:4200/api/library/%s/art \\
  -o out.jpg
        """ % (uid, uid))
if __name__ == '__main__':
    main()


