#! C:\\Python35\\python.exe $this --config-dir config/production create
import os, sys, argparse

if (sys.version_info[0] == 2):
    raise RuntimeError("python2 not supported")

from yue.core.sqlstore import SQLStore
from yue.core.library import Library as YueLibrary
from yue.core.song import Song as YueSong, get_album_art, ArtNotFound

from server.config import Config

parser = argparse.ArgumentParser(description='yue server')
parser.add_argument('--config-dir', type=str,
                    default="config/development",
                    help='application config path')
parser.add_argument('mode', type=str,
                    help='action to take')
args = parser.parse_args()

cfg = Config.init(os.path.join(args.config_dir,"application.yml"))

from server.app import app, db, dbtables

from server.dao.user import UserDao
from server.dao.library import Song, LibraryDao

import time
import datetime

from sqlalchemy import and_, or_, select

from server.service.audio_service import AudioService

import json

userDao = UserDao(db, dbtables)
libraryDao = LibraryDao(db, dbtables)

from server.cli.config import db_init, db_init_generate
from server.dao.util import pathCorrectCase

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

def _yue_reader(dbpath, chroot = None):
    sqlstore = SQLStore(dbpath)
    yueLib = YueLibrary(sqlstore)

    for song in yueLib.search(""):
        new_song = {v: song[k] for k, v in all_fields.items()}

        new_song[Song.ref_id] = song[YueSong.uid]
        new_song[Song.banished] = song[YueSong.blocked]

        if chroot is not None:
            src, dst = chroot
            path = new_song[Song.path].replace("\\", "/")
            if path.lower.startswith(src):
                path = os.path.join(dst,path[len(src):])
                path = pathCorrectCase(path)
                new_song[Song.path] = path

        # experimental hack to allow searching by genre
        # all genrs are now formated as: 'foo;'
        gen = new_song[Song.genre].replace(",", ";").strip()
        if not gen:
            gen  = [ ]
        else:
            gen = [g.strip().title() for g in gen.split(";")]
        new_song[Song.genre] = ";" + ";".join([ g for g in gen if g]) + ";"

        new_song[Song.art_path] = ""
        #try:
        #    temp_path = os.path.splitext(song[YueSong.path])[0] + ".jpg"
        #    art_path = get_album_art(song[YueSong.path], temp_path)
        #    new_song[Song.art_path] = art_path
        #except ArtNotFound as e:
        #    pass
        #except Exception as e:
        #    pass

        yield new_song

def migrate(username, domain_name, json_objects):
    """
    username: username to associate with the new songs
    domain_name: name of the domain for songs to be available in
    json_objects: an iterable of json objects reprenting songs

    each song record requires an Artist, Album Title,
    and a reference id "ref_id". the ref_id is used to associate the
    old style database format with the database used by the web app.
    """

    domain = userDao.findDomainByName(domain_name)
    if domain is None:
        sys.stdout.write("Domain with name `%s` not found" % domain_name)
        sys.exit(1)

    user = userDao.findUserByEmail(username)

    print("Migrating Database:")
    start = time.time()
    count = 0
    try:
        db.session.execute("PRAGMA JOURNAL_MODE = MEMORY");
        db.session.execute("PRAGMA synchronous = OFF");
        db.session.execute("PRAGMA TEMP_STORE = MEMORY");
        db.session.execute("PRAGMA LOCKING_MODE = EXCLUSIVE");

        bulk_songs = []
        bulk_users = []
        for new_song in json_objects:
            if count % 100 == 0 and count > 1:
                end = time.time()
                t = (end-start)
                print("%d %.2f %.2f" % (count, count / t, t))

            song_data = libraryDao.prepareSongDataInsert(domain.id, new_song)
            bulk_songs.append(song_data)

            user_data = libraryDao.prepareUserDataInsert(user.id, domain.id, new_song)
            if user_data:
                bulk_users.append(user_data)

            #song_id = libraryDao.insert(
            #    user.id, domain.id,
            #    new_song,
            #    commit=False)

            #song_id = libraryDao.insertOrUpdateByReferenceId(
            #    user.id, domain.id,
            #    new_song[Song.ref_id], new_song,
            #    commit=False)
            count += 1

        print("prepared %d songs in %.3f seconds, performing bulk insert" % (count, t))

        libraryDao.bulkInsertSongData(bulk_songs, False)
        if bulk_users:
            libraryDao.bulkInsertUserData(bulk_users, False)

    except KeyboardInterrupt:
        pass
    finally:
        db.session.commit()

    end = time.time()

    t = end - start
    print("migrated %d songs in %.3f seconds" % (count, t))

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

    username = 'admin'
    domain_name = app.config['DEFAULT_DOMAIN']
    role_name = "admin"

    path1 = "/home/nsetzer/projects/android/YueMusicPlayer/yue.db"
    path2 = "/Users/nsetzer/Music/Library/yue.db"
    path3 = "D:\\Dropbox\\ConsolePlayer\\yue.db"
    for path in [path1, path2, path3]:
        if os.path.exists(path):
            dbpath = path
            break
    else:
        sys.stderr.write("cannot find source db")
        sys.exit(1)

    env_config = os.path.join(args.config_dir,"env.yml")

    if args.mode == 'migrate':
        migrate(username, domain_name, list(_yue_reader(dbpath)))

    elif args.mode == "create":

        db_init(db, dbtables, env_config)

        domain = userDao.findDomainByName(domain_name)
        if domain is None:
            sys.stdout.write("Domain with name `%s` not found" % domain_name)
            sys.exit(1)

        role = userDao.findRoleByName(role_name)
        if role is None:
            sys.stdout.write("Role with name `%s` not found" % role_name)
            sys.exit(1)

        migrate(username, domain_name, _yue_reader(dbpath))

    elif args.mode == "generate":
        """ create a database and populate it with dummy data"""

        db_init_generate(db, dbtables, env_config)

    elif args.mode == "domain_info":

        domain = userDao.findDomainByName(domain_name)
        if domain is None:
            sys.stdout.write("Domain with name `%s` not found" % domain_name)
            sys.exit(1)

        s = time.time()
        data = libraryDao.domainSongInfo(domain.id)
        e = time.time()
        print("completed in %s" % (e - s))

        with open("library.JSON", "w") as wf:
            wf.write(json.dumps(data, sort_keys=True, indent=2))

    elif args.mode == "test-2":
        # test()
        #userDao = UserDao(db, dbtables)
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


