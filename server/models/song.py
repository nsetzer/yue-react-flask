from ..index import db
from sqlalchemy.orm import relationship
from sqlalchemy.exc import IntegrityError

from .user import User

import datetime
import uuid

class Song(object):
    """docstring for Song"""

    id          = 'id'          # unique identifier for song
    ref_id      = 'ref_id'      # uid for aiding migration
    path        = 'file_path'   # filepath on disk
    art_path    = 'art_path'    # filepath to album art
    artist      = 'artist'      # the full artist name
    artist_key  = 'artist_key'  # naturally sortable artist name
    composer    = 'composer'    # composer of the piece
    album       = 'album'       # the full album title
    title       = 'title'       # the title of the song
    genre       = 'genre'       # comma separated list of genres
    year        = 'year'        # 4 digit year
    country     = 'country'     # contry of origin
    language    = 'language'    # primary language of the song
    comment     = 'comment'     # user information
    album_index = 'album_index' # order of song in album
    length      = 'length'      # length of the song in seconds
    last_played = 'last_played' # as unix time stamp
    play_count  = 'play_count'  # number of times song has been played
    skip_count  = 'skip_count'  # number of times song was skipped
    rating      = 'rating'      # from 0 - 10
    blocked     = 'blocked'     # was 'banished', type boolean
    equalizer   = 'equalizer'   # used in automatic volume leveling
    date_added  = 'date_added'  # as unix time stamp
    frequency   = 'frequency'   # how often the song is played (days)
    file_size   = 'file_size'   # in bytes

    def __init__(self, arg):
        super(Song, self).__init__()
        self.arg = arg

    @staticmethod
    def getArtistKey(artist_name):
        if artist_name.lower().startswith("the "):
            artist_name = artist_name[4:]
        return artist_name

def generate_uuid():
   return str(uuid.uuid4())

def generate_null_timestamp():
    return datetime.datetime.utcfromtimestamp(0);

class SongData(db.Model):
    __tablename__="song"
    id = db.Column(db.String(),
                   primary_key=True,
                   default=generate_uuid)
    domain_id  = db.Column(db.Integer(), db.ForeignKey("domain.id"))
    ref_id = db.Column(db.Integer(), default = None)

    # text
    file_path = db.Column(db.String(), default="")
    art_path = db.Column(db.String(), default="")
    artist = db.Column(db.String())
    artist_key = db.Column(db.String())
    composer = db.Column(db.String(), default="")
    album = db.Column(db.String())
    title = db.Column(db.String())
    genre = db.Column(db.String(), default="")
    country = db.Column(db.String(), default="")
    language = db.Column(db.String(), default="")

    # number
    album_index = db.Column(db.Integer(), default=0)
    length = db.Column(db.Integer(), default=0)
    equalizer = db.Column(db.Integer(), default=0)
    year = db.Column(db.Integer(), default=0)

    # date
    last_played = db.Column(db.Date(), default=generate_null_timestamp)
    date_added = db.Column(db.Date(), default=datetime.datetime.utcnow)

    song_user_data = db.relationship("SongUserData")

    def as_dict(self):
       return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def as_export_dict(self):
        data = self.as_dict();
        del data['file_path']
        del data['art_path']
        return data

    @staticmethod
    def column_names():
        return [c.name for c in SongData.__table__.columns]

    def populate_dict(self, data):
        for c in self.__table__.columns:
            data[c.name] = getattr(self, c.name)

class SongUserData(db.Model):
    data_id = db.Column(db.Integer(), primary_key=True)

    song_id = db.Column(db.Integer(), db.ForeignKey("song.id"))
    user_id = db.Column(db.Integer(), db.ForeignKey("user.id"))

    # text
    comment = db.Column(db.String(),default="")

    # number
    rating = db.Column(db.Integer(), default=0)
    play_count = db.Column(db.Integer(), default=0)
    skip_count = db.Column(db.Integer(), default=0)
    blocked = db.Column(db.Integer(), default=0)
    frequency = db.Column(db.Integer(), default=0)

    @staticmethod
    def column_names():
        return [c.name for c in SongUserData.__table__.columns]

    def populate_dict(self, data):
        for c in self.__table__.columns:
            data[c.name] = getattr(self, c.name)

    @staticmethod
    def populate_dict_defaults(data):
        for c in SongUserData.__table__.columns:
            if c.default is not None:
                data[c.name] = c.default.arg


class LibraryException(Exception):
    pass

class Library(object):
    """docstring for Library"""
    def __init__(self, user_id, domain_id):
        super(Library, self).__init__()
        self.user_id = user_id
        self.domain_id = domain_id;

    def query(self):
        return db.session.query(SongData, SongUserData).join(SongUserData)

    def insert(self,song):

        if Song.artist not in song:
            raise LibraryException("artist key missing from song")

        if Song.album not in song:
            raise LibraryException("album key missing from song")

        if Song.title not in song:
            raise LibraryException("title key missing from song")

        if Song.artist_key not in  song:
            song[Song.artist_key] = Song.getArtistKey(song[Song.artist])

        song_keys = set(SongData.column_names())
        song_data = {k:song[k] for k in song.keys() if k in song_keys}
        song_data['domain_id'] = self.domain_id

        user_keys = set(SongUserData.column_names())
        user_data = {k:song[k] for k in song.keys() if k in user_keys}

        new_song = SongData(**song_data)
        db.session.add(new_song)

        try:
            db.session.commit()
        except IntegrityError:
            raise LibraryException(str(e))

        db.session.refresh(new_song)

        if user_data:
            user_data["user_id"] = self.user_id
            user_data["song_id"] = new_song.id
            new_data = SongUserData(**user_data)

            db.session.add(new_data)

            try:
                db.session.commit()
            except IntegrityError:
                raise LibraryException(str(e))

        return new_song.id

    def update(self,song_id, song):

        song_keys = set(SongData.column_names())
        song_data = {k:song[k] for k in song.keys() if k in song_keys}

        user_keys = set(SongUserData.column_names())
        user_data = {k:song[k] for k in song.keys() if k in user_keys}

        if song_data:
            new_song = SongData \
                        .query \
                        .filter_by(id = song_id) \
                        .first()
            for k,v in song_data.items():
                setattr(new_song, k, v)

        if user_data:
            new_user = SongUserData \
                        .query \
                        .filter_by(song_id = song_id,
                                   user_id = self.user_id) \
                        .first()
            if new_user:
                for k,v in user_data.items():
                    setattr(new_user, k, v)

        try:
            db.session.commit()
        except IntegrityError:
            raise LibraryException(str(e))

    def findSongById(self, song_id):
        song = {}

        result = db.session \
                    .query(SongData) \
                    .filter(SongData.id == song_id) \
                    .first()

        if not result:
            return None

        result.populate_dict(song)

        result = db.session \
                    .query(SongUserData) \
                    .filter(SongUserData.song_id == song_id,
                            SongUserData.user_id == self.user_id) \
                    .first()

        if result:
            result.populate_dict(song)
        else:
            SongUserData.populate_dict_defaults(song)

        if 'song_id' in song:
            del song['song_id']

        return song

    def insertOrUpdateByReferenceId(self, ref_id, song):

        result = db.session \
                    .query(SongData) \
                    .filter(SongData.ref_id == ref_id) \
                    .first()

        if result:
            self.update(result.id, song)
            return result.id
        else:
            return self.insert( song )

