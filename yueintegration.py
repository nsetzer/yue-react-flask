
from yue.core.sqlstore import SQLStore
from yue.core.library import Library as YueLibrary
from yue.core.song import Song as YueSong

from server.index import db

from server.models.user import User
from server.models.song import Song, SongUserData, Library

import datetime

text_fields = {
    YueSong.path: "file_path",
    YueSong.artist: "artist",
    YueSong.artist_key: "artist_key",
    YueSong.composer: "composer",
    YueSong.album: "album",
    YueSong.title: "title",
    YueSong.genre: "genre",
    YueSong.country: "country",
    YueSong.lang: "language",
}

number_fields = {
    YueSong.album_index: "album_index",
    YueSong.length: "length",
    YueSong.equalizer: "equalizer",
    YueSong.year: "year",
}

date_fields = {
    YueSong.last_played: "last_played",
    YueSong.date_added: "date_added"
}

user_fields = {
    YueSong.rating: "rating",
    YueSong.play_count: "play_count",
    YueSong.skip_count: "skip_count",
    YueSong.blocked: "blocked",
    YueSong.comment: "comment"
}

def main():
    #dbpath = "/Users/nsetzer/Music/Library/yue.db"
    dbpath = "/home/nsetzer/projects/android/YueMusicPlayer/yue.db"
    sqlstore = SQLStore(dbpath)
    yueLib = YueLibrary(sqlstore)

    user0 = User.get_user_with_email("user000")
    lib0 = Library(user0.id)

    user1 = User.get_user_with_email("user001")
    lib1 = Library(user1.id)

    songs = yueLib.search(None)

    all_fields = {}
    all_fields.update(text_fields)
    all_fields.update(number_fields)
    all_fields.update(date_fields)
    all_fields.update(user_fields)

    for song in songs:
        new_song = {v:song[k] for k,v in all_fields.items()}
        new_song['ref_id'] = song['uid']
        new_song['last_played'] = datetime.datetime.utcfromtimestamp(new_song['last_played'])
        new_song['date_added'] = datetime.datetime.utcfromtimestamp(new_song['date_added'])

        song_id = lib0.insertOrUpdateByReferenceId(song['uid'], new_song)
        print("song_id", song_id)
        res = lib0.findSongById(song_id)
        print(res)

        count = db.session \
            .query(Song) \
            .filter(Song.ref_id == song['uid']) \
            .count()
        print(count)

        break;

if __name__ == '__main__':
    main()


