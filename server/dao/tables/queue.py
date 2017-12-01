
from sqlalchemy.schema import Table, Column, ForeignKey
from sqlalchemy.types import Integer
from .util import StringArrayType

def SongQueueTable(metadata):
    return Table('song_queue', metadata,
        Column('user_id', Integer, ForeignKey('user.id'), unique=True),
        Column('songs', StringArrayType),
    )





