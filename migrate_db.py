
import sys

from yue.core.sqlstore import SQLStore
from yue.core.library import Library as YueLibrary
from yue.core.song import Song as YueSong

from server.app import app, db, db_init, Domain, Role, User

from server.models.user import User
from server.models.song import Song, SongData, SongUserData, SongSearchGrammar, Library

import time
import datetime

from sqlalchemy import and_, or_, select

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

    domain = Domain.findDomainByName(domain_name)
    if domain is None:
        sys.stdout.write("Domain with name `%s` not found" % domain_name)
        sys.exit(1)

    sqlstore = SQLStore(dbpath)
    yueLib = YueLibrary(sqlstore)

    user = User.get_user_with_email(username)
    lib = Library(user.id, domain.id)

    print("Migrating Database:")
    start = time.time()
    for song in yueLib.search(None):
        new_song = {v: song[k] for k, v in all_fields.items()}
        new_song[Song.ref_id] = song[YueSong.uid]
        new_song[Song.last_played] = datetime.datetime.utcfromtimestamp(new_song[Song.last_played])
        new_song[Song.date_added] = datetime.datetime.utcfromtimestamp(new_song[Song.date_added])

        song_id = lib.insertOrUpdateByReferenceId(song[YueSong.uid], new_song)

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
    #dbpath = "/Users/nsetzer/Music/Library/yue.db"

    if mode == 'migrate':
        migrate(username, dbpath)

    elif mode == "create":

        db_init()

        domain = Domain.findDomainByName(domain_name)
        if domain is None:
            sys.stdout.write("Domain with name `%s` not found" % domain_name)
            sys.exit(1)
        role = Role.findRoleByName(role_name)
        if role is None:
            sys.stdout.write("Role with name `%s` not found" % role_name)
            sys.exit(1)
        username = "nsetzer"
        password = "nsetzer"

        user = User(username, password, domain.id, role.id)
        sys.stdout.write("Creating User: %s@%s/%s\n" % (username, domain.name, role.name))
        db.session.add(user)
        db.session.commit()

        migrate(username, domain_name, dbpath)

    elif mode == "test":
        test()


if __name__ == '__main__':
    main()


