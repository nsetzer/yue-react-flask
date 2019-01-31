

from sqlalchemy.orm import relationship
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, not_, case, select, update, insert, column, func, asc, desc
from sqlalchemy.sql.expression import bindparam

class Settings(object):
    db_version = "db_version"
    storage_system_key = "storage_system_key"

class SettingsDao(object):
    """docstring for SettingsDao"""
    def __init__(self, db, dbtables):
        super(SettingsDao, self).__init__()
        self.db = db
        self.dbtables = dbtables

    def _select(self, key):
        query = self.dbtables.ApplicationSchemaTable.select() \
            .where(self.dbtables.ApplicationSchemaTable.c.key == key)
        result = self.db.session.execute(query)
        return result.fetchone()

    def _insert(self, key, value):
        query = insert(self.dbtables.ApplicationSchemaTable) \
            .values({"key": key, "value": value})
        self.db.session.execute(query)

    def _update(self, key, value):
        query = update(self.dbtables.ApplicationSchemaTable) \
            .values({"value": value}) \
            .where(self.dbtables.ApplicationSchemaTable.key == key)
        self.db.session.execute(query)

    def set(self, key, value, commit=True):

        item = self._select(key)
        if item is None:
            self._insert(key, value)
        else:
            self._update(key, value)

        if commit:
            self.db.session.commit()

    def get(self, key):
        item = self._select(key)
        if item is None:
            raise Exception("not found: %s" % key)
        return item['value']

    def has(self, key):
        return self._select(key) is not None
