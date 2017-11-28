
from sqlalchemy import and_, or_, not_, select, column, update, insert

import bcrypt

class User(object):
    """docstring for User"""
    def __init__(self, db):
        super(User, self).__init__()
        self.db = db

    def findDomainByName(self, name):
        query = self.db.tables.DomainTable.select() \
            .where(self.db.tables.DomainTable.c.name == name)
        result = self.db.session.execute(query)
        return result.fetchone()

    def findRoleByName(self, name):
        query = self.db.tables.RoleTable.select() \
            .where(self.db.tables.RoleTable.c.name == name)
        result = self.db.session.execute(query)
        return result.fetchone()

    def findUserByEmail(self, email):
        query = self.db.tables.UserTable.select() \
            .where(self.db.tables.UserTable.c.email == email)
        result = self.db.session.execute(query)
        return result.fetchone()

    def findUserByEmailAndPassword(self, email, password):
        cols = [
            self.db.tables.UserTable.c.password
        ]
        query = self.db.tables.UserTable.select(cols) \
            .where(self.db.tables.UserTable.c.email == email)
        password, = self.db.session.execute(query).fetchone()

        return bcrypt.checkpw(password, user)

    def createUser(self, user):



