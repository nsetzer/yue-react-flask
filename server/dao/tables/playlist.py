
from sqlalchemy.schema import Table, Column, ForeignKey
from sqlalchemy.types import Integer, DateTime, String

from .util import StringArrayType

def SongPlaylistTable(metadata):
    return Table('song_playlist', metadata,
        Column('user_id', Integer, ForeignKey('user.id')),
        Column('name', String),
        Column('songs', StringArrayType),
    )


