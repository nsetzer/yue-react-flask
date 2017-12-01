
from sqlalchemy.schema import Table, Column, ForeignKey
from sqlalchemy.types import Integer, DateTime, String
from sqlalchemy import MetaData

def SongHistoryTable(metadata):
    return Table('song_history', metadata,
        Column('user_id', Integer()),
        Column('song_id', String(), ForeignKey("song_data.id")),
        Column('date', DateTime()),
    )
