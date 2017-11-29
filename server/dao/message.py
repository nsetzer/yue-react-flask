
from sqlalchemy import and_, or_, not_, select, column, update, delete, insert

class Message(object):
    """docstring for Message"""

    def __init__(self, db):
        super(Message, self).__init__()
        self.db = db

    def add(self, message):
        query = self.db.tables.MessageTable.insert() \
                .values({"text": message, })
        result = self.db.session.execute(query)
        return result.inserted_primary_key[0]

    def remove(self, id):
        query = delete(self.db.tables.MessageTable) \
                .where(self.db.tables.MessageTable.c.id == id)
        self.db.session.execute(query)

    def get_all_messages(self):
        query = self.db.tables.MessageTable.select()
        result = self.db.session.execute(query)
        return result.fetchall()
