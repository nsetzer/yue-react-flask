from sqlalchemy.schema import Table, Column, ForeignKey
from sqlalchemy.types import Integer, String

from sqlalchemy import and_, or_, not_, select, column, func, asc, desc
from .util import generate_uuid
import time

# http://docs.sqlalchemy.org/en/latest/orm/tutorial.html

def SongDataTable(metadata):
    """
    Construct a table representing a song

    id: uuid4 song id
    domain_id: domain this song belongs to (for multi tenant environments)
    ref_id: reference id used for migration from legacy databases.
    file_path: file path or url to song resource
    art_path: file path or url to album artwork
    artist: the name of artist for this song
    artist_key: A naturally sortable artist name
    composer: the composer for this piece
    album: the title of the album for this song
    title: the title of this song
    genre: comma or semi-colon separated list of genres
    country: origin country for this piece
    language: primary language of the song (may be a comma or semi-colon list)
    album_index: index of the song in the album
    length: length of the song in seconds
    equalizer: measure of volume of the song
    year: year the track was released
    """
    return Table('song_data', metadata,
        Column('id', String, primary_key=True, default=generate_uuid),
        Column('domain_id', Integer, ForeignKey("domain.id")),
        Column('ref_id', Integer, default=None),
        # text
        Column('file_path', String, default=""),
        Column('art_path', String, default=""),
        Column('artist', String),
        Column('artist_key', String),
        Column('composer', String, default=""),
        Column('album', String),
        Column('title', String),
        Column('genre', String, default=""),
        Column('country', String, default=""),
        Column('language', String, default=""),
        # number
        Column('album_index', Integer, default=0),
        Column('length', Integer, default=0),
        Column('equalizer', Integer, default=0),
        Column('year', Integer, default=0)
    )

def SongUserDataTable(metadata):
    return Table('song_user_data', metadata,
        # index
        Column('song_id', String, ForeignKey("song_data.id")),
        Column('user_id', Integer, ForeignKey("user.id")),
        # text
        Column('comment', String, default=""),
        # number
        Column('rating', Integer, default=0),
        Column('play_count', Integer, default=0),
        Column('skip_count', Integer, default=0),
        Column('blocked', Integer, default=0),
        Column('frequency', Integer, default=0),
        # date
        Column('last_played', Integer, default=0),
        Column('date_added', Integer, default=time.time)
    )

# class SongData(db.Model):
#     __tablename__"song"
#     id = db.Column(db.String(),
#                    primary_key=True,
#                    default=generate_uuid)
#     domain_id  = db.Column(db.Integer(), db.ForeignKey("domain.id"))
#     ref_id = db.Column(db.Integer(), default=None)
#
#     # text
#     file_path = db.Column(db.String(), default="")
#     art_path = db.Column(db.String(), default="")
#     artist = db.Column(db.String())
#     artist_key = db.Column(db.String())
#     composer = db.Column(db.String(), default="")
#     album = db.Column(db.String())
#     title = db.Column(db.String())
#     genre = db.Column(db.String(), default="")
#     country = db.Column(db.String(), default="")
#     language = db.Column(db.String(), default="")
#
#     # number
#     album_index = db.Column(db.Integer(), default=0)
#     length = db.Column(db.Integer(), default=0)
#     equalizer = db.Column(db.Integer(), default=0)
#     year = db.Column(db.Integer(), default=0)
#
#     song_user_data = db.relationship("SongUserData")
#
#     def as_dict(self):
#         return {c.name: getattr(self, c.name) for c in self.__table__.columns}
#
#     def as_export_dict(self):
#         data = self.as_dict()
#         del data['file_path']
#         del data['art_path']
#         return data
#
#     @staticmethod
#     def column_names():
#         return [c.name for c in SongData.__table__.columns]
#
#     @staticmethod
#     def default(key):
#         default = getattr(SongData, key).default
#         if default is None:
#             return ""
#
#         return default.arg
#
#     def populate_dict(self, data):
#         for c in self.__table__.columns:
#             data[c.name] = getattr(self, c.name)
#
# class SongUserData(db.Model):
#     data_id = db.Column(db.Integer(), primary_key=True)
#
#     song_id = db.Column(db.String(), db.ForeignKey("song.id"))
#     user_id = db.Column(db.Integer(), db.ForeignKey("user.id"))
#
#     # text
#     comment = db.Column(db.String(), default="")
#
#     # number
#     rating = db.Column(db.Integer(), default=0)
#     play_count = db.Column(db.Integer(), default=0)
#     skip_count = db.Column(db.Integer(), default=0)
#     blocked = db.Column(db.Integer(), default=0)
#     frequency = db.Column(db.Integer(), default=0)
#
#     # date
#     # generate_null_timestamp, datetime.datetime.utcnow
#     last_played = db.Column(db.Integer(), default=0)
#     date_added = db.Column(db.Integer(), default=time.time)
#
#     @staticmethod
#     def column_names():
#         return [c.name for c in SongUserData.__table__.columns]
#
#     @staticmethod
#     def default(key):
#         if key in ['last_played', 'date_added']:
#             return str(generate_null_timestamp())
#
#         default = getattr(SongUserData, key).default
#         if default is None:
#             return ""
#
#         return default.arg
#
#     def populate_dict(self, data):
#         for c in self.__table__.columns:
#             data[c.name] = getattr(self, c.name)
#
#     @staticmethod
#     def populate_dict_defaults(data):
#         for c in SongUserData.__table__.columns:
#             if c.default is not None:
#                 data[c.name] = c.default.arg


