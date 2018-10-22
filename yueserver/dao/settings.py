

from sqlalchemy.orm import relationship
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, not_, case, select, update, insert, column, func, asc, desc
from sqlalchemy.sql.expression import bindparam

class SettingsDao(object):
    """docstring for SettingsDao"""
    def __init__(self, db, dbtables):
        super(SettingsDao, self).__init__()
        self.db = db
        self.dbtables = dbtables

    def _insert(self, key, value, commit):

        query = insert(self.dbtables.ApplicationSchemaTable) \
            .values({"key": key, "value": value})

        self.db.session.execute(query)

        if commit:
            self.db.session.commit()

    def _upsert(self, key, value, commit):

        query = update(self.dbtables.ApplicationSchemaTable) \
            .values({"value": value}) \
            .where(self.dbtables.ApplicationSchemaTable.key == key)

        self.db.session.execute(query)

        if commit:
            self.db.session.commit()

    def set(self, key, value, commit=True):

        query = select(['*']) \
            .select_from(self.dbtables.ApplicationSchemaTable) \
            .where(self.dbtables.ApplicationSchemaTable.key == key)

        result = self.db.session.execute(query)
        item = result.fetchone()
        if item is None:
            self._insert(key, value, commit)
        else:
            self._update(key, value, commit)

    def get(self, key):

        query = select(['*']) \
            .select_from(self.dbtables.ApplicationSchemaTable) \
            .where(self.dbtables.ApplicationSchemaTable.key == key)
        result = self.db.session.execute(query)
        item = result.fetchone()

        return item['value']
