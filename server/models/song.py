from ..index import db
from sqlalchemy.orm import relationship
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, not_, select, column, func, asc, desc

import datetime, time
import uuid

# http://docs.sqlalchemy.org/en/latest/orm/tutorial.html

def generate_uuid():
    return str(uuid.uuid4())

def generate_null_timestamp():
    return datetime.datetime.utcfromtimestamp(0)

class SongData(db.Model):
    __tablename__ = "song"
    id = db.Column(db.String(),
                   primary_key=True,
                   default=generate_uuid)
    domain_id  = db.Column(db.Integer(), db.ForeignKey("domain.id"))
    ref_id = db.Column(db.Integer(), default=None)

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

    song_user_data = db.relationship("SongUserData")

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def as_export_dict(self):
        data = self.as_dict()
        del data['file_path']
        del data['art_path']
        return data

    @staticmethod
    def column_names():
        return [c.name for c in SongData.__table__.columns]

    @staticmethod
    def default(key):
        default = getattr(SongData, key).default
        if default is None:
            return ""

        return default.arg

    def populate_dict(self, data):
        for c in self.__table__.columns:
            data[c.name] = getattr(self, c.name)

class SongUserData(db.Model):
    data_id = db.Column(db.Integer(), primary_key=True)

    song_id = db.Column(db.String(), db.ForeignKey("song.id"))
    user_id = db.Column(db.Integer(), db.ForeignKey("user.id"))

    # text
    comment = db.Column(db.String(), default="")

    # number
    rating = db.Column(db.Integer(), default=0)
    play_count = db.Column(db.Integer(), default=0)
    skip_count = db.Column(db.Integer(), default=0)
    blocked = db.Column(db.Integer(), default=0)
    frequency = db.Column(db.Integer(), default=0)

    # date
    # generate_null_timestamp, datetime.datetime.utcnow
    last_played = db.Column(db.Integer(), default=0)
    date_added = db.Column(db.Integer(), default=time.time)

    @staticmethod
    def column_names():
        return [c.name for c in SongUserData.__table__.columns]

    @staticmethod
    def default(key):
        if key in ['last_played', 'date_added']:
            return str(generate_null_timestamp())

        default = getattr(SongUserData, key).default
        if default is None:
            return ""

        return default.arg

    def populate_dict(self, data):
        for c in self.__table__.columns:
            data[c.name] = getattr(self, c.name)

    @staticmethod
    def populate_dict_defaults(data):
        for c in SongUserData.__table__.columns:
            if c.default is not None:
                data[c.name] = c.default.arg


