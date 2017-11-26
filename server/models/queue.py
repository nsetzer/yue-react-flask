
from sqlalchemy.orm import relationship
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, not_, select, column, func, asc, desc

from sqlalchemy.schema import Table, Column, ForeignKey
from sqlalchemy.types import Integer, DateTime, String
from sqlalchemy import MetaData

from .song import SongData, SongUserData
from .user import User

from ..index import db

SongQueue = Table('queue_songs', db.metadata,
    Column('user_id', Integer, ForeignKey('user.id')),
    Column('song_id', Integer, ForeignKey('song.id')),
    Column('index', Integer)
)


