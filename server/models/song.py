from ..index import db
from sqlalchemy.orm import relationship
from sqlalchemy.exc import IntegrityError

from .user import User

import datetime
import uuid

def generate_uuid():
   return str(uuid.uuid4())

class Song(db.Model):
    id = db.Column(db.String(),
                   primary_key=True,
                   default=generate_uuid)
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
    last_played = db.Column(db.Date(), default=datetime.datetime.utcnow)
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
        return [c.name for c in Song.__table__.columns]

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

    @staticmethod
    def column_names():
        return [c.name for c in SongUserData.__table__.columns]

    def populate_dict(self, data):
        for c in self.__table__.columns:
            data[c.name] = getattr(self, c.name)

class LibraryException(Exception):
    pass

class Library(object):
    """docstring for Library"""
    def __init__(self, user_id):
        super(Library, self).__init__()
        self.user_id = user_id

    def query(self):
        return db.session.query(Song, SongUserData).join(SongUserData)

    def insert(self,song):

        song_keys = set(Song.column_names())
        song_data = {k:song[k] for k in song.keys() if k in song_keys}

        user_keys = set(SongUserData.column_names())
        user_data = {k:song[k] for k in song.keys() if k in user_keys}

        new_song = Song(**song_data)
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

        song_keys = set(Song.column_names())
        song_data = {k:song[k] for k in song.keys() if k in song_keys}

        user_keys = set(SongUserData.column_names())
        user_data = {k:song[k] for k in song.keys() if k in user_keys}

        if song_data:
            new_song = Song \
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
        result = db.session \
                    .query(Song, SongUserData) \
                    .join(SongUserData) \
                    .filter(Song.id == song_id,
                            User.id == self.user_id) \
                    .first()

        song = {}
        for tableItem in result:
            tableItem.populate_dict(song)

        if 'song_id' in song:
            del song['song_id']
        return song

    def insertOrUpdateByReferenceId(self, ref_id, song):


        result = db.session \
                    .query(Song) \
                    .filter(Song.ref_id == ref_id) \
                    .first()

        if result:
            self.update(result.id, song)
            return result.id
        else:
            return self.insert( song )

