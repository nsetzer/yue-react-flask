
from sqlalchemy import and_, or_, not_, select, column, update, insert

import bcrypt

class UserDao(object):
    """docstring for UserDao"""
    def __init__(self, db):
        super(UserDao, self).__init__()
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
        query = self.db.tables.UserTable.select() \
            .where(self.db.tables.UserTable.c.email == email)
        user = self.db.session.execute(query).fetchone()
        crypt = user[self.db.tables.UserTable.c.password]

        if bcrypt.checkpw(password.encode("utf-8"), crypt):
            return user

        raise Exception("user not found")

    def createDomain(self, domain):
        query = insert(self.db.tables.DomainTable).values(domain)
        result = self.db.session.execute(query)
        return result.inserted_primary_key[0]

    def createRole(self, role):
        query = insert(self.db.tables.RoleTable).values(role)
        result = self.db.session.execute(query)
        return result.inserted_primary_key[0]

    def createUser(self, user):

        salt = bcrypt.gensalt(12)
        crypt = bcrypt.hashpw(user['password'].encode("utf-8"), salt)
        user['password'] = crypt

        query = insert(self.db.tables.UserTable).values(user)

        result = self.db.session.execute(query)

        return result.inserted_primary_key[0]

    def updateUser(self, user):

        if 'password' in user:
            salt = bcrypt.gensalt(12)
            crypt = bcrypt.hashpw(user['password'].encode("utf-8"), salt)
            user['password'] = crypt

        query = update(self.db.tables.UserTable) \
            .values(user) \
            .where(SongQueueTable.c.user_id == self.user_id)

        self.db.session.execute(query)


