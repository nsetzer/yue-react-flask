from sqlalchemy.schema import Table, Column
from sqlalchemy.types import String


def ApplicationSchemaTable(metadata):
    """
    returns a table for describing the application schema, versioning

    key: the name of a parameter
    value: a json string containing application settings.
           the value can be a scalar, sequence or mapping

    This table is used to hold the current version of the database.
    """
    return Table('application_schema', metadata,
        Column('key', String, primary_key=True),
        Column('value', String, unique=True, nullable=False),
    )
