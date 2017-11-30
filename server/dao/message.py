
from sqlalchemy import and_, or_, not_, select, column, update, delete, insert

class MessageDao(object):
    """docstring for Message"""

    def __init__(self, db, dbtables):
        super(MessageDao, self).__init__()
        self.db = db
        self.dbtables = dbtables

    def add(self, message):
        query = self.dbtables.MessageTable.insert() \
                .values({"text": message, })
        result = self.db.session.execute(query)
        self.db.session.commit()
        return result.inserted_primary_key[0]

    def remove(self, id):
        query = delete(self.dbtables.MessageTable) \
                .where(self.dbtables.MessageTable.c.id == id)
        self.db.session.execute(query)
        self.db.session.commit()

    def get_all_messages(self):
        query = self.dbtables.MessageTable.select()
        result = self.db.session.execute(query)
        return result.fetchall()
