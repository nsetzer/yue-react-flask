
from ..index import db
from sqlalchemy.schema import Table, Column, ForeignKey
from sqlalchemy.types import Integer, DateTime, String
from sqlalchemy import MetaData

from .song import SongData

SongHistory = Table('song_history', db.metadata,
    Column('user_id', Integer()),
    Column('song_id', String(), ForeignKey(SongData.id)),
    Column('date', DateTime()),
    )
