
from sqlalchemy import and_, or_, not_, select, column, update, insert

class User(object):
    """docstring for User"""
    def __init__(self, db):
        super(User, self).__init__()
        self.arg = arg

    def findDomainByName(self, name):
        pass

    def findRoleByName(self, name):
        pass

    def findUserByEmail(self, email):
        pass

    def findUserByEmailAndPassword(self, email, password):
        pass
