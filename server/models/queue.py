
from sqlalchemy.orm import relationship
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, not_, select, column, update, insert

from sqlalchemy.schema import Table, Column, ForeignKey
from sqlalchemy.types import Integer, DateTime, String
from sqlalchemy import MetaData

from .user import User

from .util import StringArrayType

from ..index import db

SongQueueTable = Table('song_queue', db.metadata,
    Column('user_id', Integer, ForeignKey('user.id'), unique=True),
    Column('songs', StringArrayType),
)





