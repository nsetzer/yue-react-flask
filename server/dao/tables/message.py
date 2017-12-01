
from sqlalchemy.schema import Table, Column, ForeignKey
from sqlalchemy.types import Integer, String

def MessageTable(metadata):
    return Table('message', metadata,
        Column('id', Integer, primary_key=True),
        Column('text', String, unique=False)
    )

