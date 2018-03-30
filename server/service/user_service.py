

from ..dao.user import UserDao
from ..dao.library import LibraryDao
from ..dao.queue import SongQueueDao

from .util import UserServiceException

class UserService(object):
    """docstring for UserService"""

    _instance = None

    def __init__(self, db, dbtables):
        super(UserService, self).__init__()
        self.db = db
        self.dbtables = dbtables

        self.userDao = UserDao(db, dbtables)

    @staticmethod
    def init(db, dbtables):
        if not UserService._instance:
            UserService._instance = UserService(db, dbtables)
        return UserService._instance

    @staticmethod
    def instance():
        return UserService._instance

    def getUserByPassword(self, email, password):
        return self.userDao.findUserByEmailAndPassword(email, password)

