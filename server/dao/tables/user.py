
from sqlalchemy.schema import Table, Column, ForeignKey
from sqlalchemy.types import Integer, String

def DomainTable(metadata):
    return Table('domain', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String),
    )

def RoleTable(metadata):
    return Table('role', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String),
    )

def UserTable(metadata):
    return Table('user', metadata,
        Column('id', Integer, primary_key=True),
        Column('email', String),
        Column('password', String),
        Column('domain_id', Integer, ForeignKey("domain.id")),
        Column('role_id', Integer, ForeignKey("role.id"))
    )


