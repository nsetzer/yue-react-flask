
from sqlalchemy.orm import relationship
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, not_, select, column, func, asc, desc

from sqlalchemy.schema import Table, Column, ForeignKey
from sqlalchemy.types import Integer, DateTime, String
from sqlalchemy import MetaData

from .song import SongData, SongUserData
from .user import User

from ..index import db

PlaylistSongs = Table('playlist_songs', db.metadata,
    Column('playlist_id', Integer, ForeignKey('playlist.id')),
    Column('song_id', Integer, ForeignKey('song.id')),
    Column('index', Integer)
)

class Playlist(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id'))
    name = db.Column(db.String())

