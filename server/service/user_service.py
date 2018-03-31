

from ..dao.user import UserDao
from ..dao.library import LibraryDao
from ..dao.queue import SongQueueDao

from .util import UserServiceException

from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired, BadSignature

import base64
from bcrypt import gensalt

TWO_WEEKS = 1209600

def generate_basic_token(username, password):
    """convert a username and possword into a basic token"""
    enc = (username + ":" + password).encode("utf-8", "ignore")
    return b"Basic " + base64.b64encode(enc)

def parse_basic_token(token):
    """return the username and password given a token"""
    if not token.startswith(b"Basic "):
        raise Exception("Invalid Basic Token")
    return base64.b64decode(token[6:]).decode("utf-8").split(":")

def parse_apikey_token(token):
    """return the username and password given a token"""
    if not token.startswith(b"APIKEY "):
        raise Exception("Invalid ApiKey Token")
    return token[7:].decode("utf-8")

def generate_token(user, expiration=TWO_WEEKS):
    s = Serializer(app.config['SECRET_KEY'], expires_in=expiration)
    token = s.dumps({
        'id': user['id'],
        'email': user['email'],
        'domain_id': user['domain_id'],
        'role_id': user['role_id'],
    }).decode('utf-8')
    return token

def verify_token(token):
    s = Serializer(app.config['SECRET_KEY'])
    return s.loads(token)

class UserException(Exception):
    pass

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


    def createUser(self, email, domain, role, password):
        user_id = userDao.createUser(
                email,
                domain,
                role,
                password
            )
        return user_id

    def getUserByPassword(self, email, password):

        # TODO: decompose email into username@Domain/Role

        return self.userDao.findUserByEmailAndPassword(email, password)

    def getUserFromBasicToken(self, token, features = None):

        # TODO: decompose email from user@domain/role
        # and set the domain and role correctly

        email, password = parse_basic_token(token)

        user = self.userDao.findUserByEmailAndPassword(email, password)

        user_data = {
            "id": user.id,
            "email": user.email,
            "domain_id": user.domain_id,
            "role_id": user.role_id
        }

        if features is not None:
            if not self._validate_user_feature(user_data, features[0]):
                raise UserException(
                    "failed to authenticate user %s with feature %s" % (
                        user_data['email'], features[0]))

        return user_data

    def getUserFromApikey(self, token, features = None):

        apikey = parse_apikey_token(token)

        user = self.userDao.findUserByApiKey(apikey)

        user_data = {
            "id": user.id,
            "email": user.email,
            "domain_id": user.domain_id,
            "role_id": user.role_id
        }

        if features is not None:
            if not self._validate_user_feature(user_data, features[0]):
                raise UserException(
                    "failed to authenticate user %s with feature %s" % (
                        user_data['email'], features[0]))

        return user_data

    def getUserFromToken(self, token, features = None):

        try:
            user_data = verify_token(token)

            if features is not None:
                if not self._validate_user_feature(user_data, features[0]):
                    raise UserException(
                        "failed to authenticate user %s with feature %s" % (
                            user_data['email'], features[0]))

            return user_data
        except BadSignature:
            pass
        except SignatureExpired:
            pass

        raise UserException("Invalid Token")

    def loginUser(self, email, password):

        user = self.getUserByPassword(email, password)

        if not user:
            raise UserException("Unable to login user")

        return generate_token(user)

    def verifyToken(self, token):

        is_valid = False
        reason = ""
        try:
            if verify_token(token):
                is_valid = True
                reason = "OK"
        except BadSignature:
            is_valid = False
            reason = "Bad Signature"
        except SignatureExpired:
            is_valid = False
            reason = "Expired Signature"

        return is_valid, reason



    def changeUserPassword(self, user, new_password):

        userDao.changeUserPassword(user['id'], new_password)

    def listUser(self, userId):

        user = userDao.findUserById(userId)

        if not user:
            raise UserException("Unable to login user")

        features = self.userDao.listFeaturesByName(user['role_id'])

        # TODO: list all granted roles and domains

        user_info = {
            "email": user['email'],
            "default_domain": user['domain_id'],
            "default_role": user['role_id'],
            "roles": [
                {
                "id": user['role_id'],
                "features": features,
                },
            ],
            "domains": [
                {
                "id": user['domain_id'],
                }
            ],
        }

        return user_info

    def listDomainUsers(self, domainName):

        did = self.userDao.findDomainByName(domain).id

        domains = { d['id']: d['name'] for d in self.userDao.listDomains() }
        roles = { r['id']: r['name'] for r in self.userDao.listRoles() }
        users = userDao.listUsers(did)

        info = {
            "domains": domains,
            "roles": roles,
            "users": users,
        }

        return info



    def _validate_user_feature(self, user_data, feature_name):
        """
        validate that a role has a specific feature
        assume that the user has been granted the specified role
        """
        user_id = user_data['id']
        role_id = user_data['role_id']
        # has_role = _userDao.userHasRole(user_id, role_id)
        has_feat = self.userDao.roleHasNamedFeature(role_id, feature_name)
        return has_feat;