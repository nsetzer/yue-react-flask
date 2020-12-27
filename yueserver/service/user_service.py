
"""
The user service handles user management and authentication.

User can be created or removed, A user can authenticate and change their
password.
"""

import logging

from ..dao.user import UserDao
from ..dao.storage import StorageDao
from ..dao.library import LibraryDao
from ..dao.settings import SettingsDao, Settings
from ..dao.queue import SongQueueDao
from ..dao.filesys.crypt import uuid_token_generate, uuid_token_verify, sha256
from .exception import UserServiceException

#from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
#from itsdangerous import SignatureExpired, BadSignature
from ..framework2.webtoken import  WebToken, WebTokenException

import json
import base64
from bcrypt import gensalt

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


def generate_token_v2(secret, user, expiration):
    json.dumps({
        'id': user['id'],
        'email': user['email'],
        'domain_id': user['domain_id'],
        'role_id': user['role_id'],
    })
    struct.pack(">L", expiration)

def generate_token(secret, user, expiration):
    #s = Serializer(secret, expires_in=expiration)
    #token = s.dumps().decode('utf-8')
    #return token

    wt = WebToken(secret)
    payload = json.dumps({
        'id': user['id'],
        'email': user['email'],
        'domain_id': user['domain_id'],
        'role_id': user['role_id'],
    }).encode("utf-8")
    return wt.create(payload)

def verify_token(secret, token):
    #s = Serializer(secret)
    #return s.loads(token)
    wt = WebToken(secret)
    payload = wt.verify(token).decode("utf-8")
    return json.loads(payload)

class UserException(Exception):
    pass

class UserService(object):
    """docstring for UserService"""

    _instance = None

    def __init__(self, config, db, dbtables):
        super(UserService, self).__init__()
        self.config = config
        self.db = db
        self.dbtables = dbtables

        self.userDao = UserDao(db, dbtables)
        self.storageDao = StorageDao(db, dbtables)
        self.settingsDao = SettingsDao(db, dbtables)

        # TODO: this needs to be populated by the application config
        self.secret = config.secret_key
        # allow specifying 14d for 14 days, 2w for 2 weeks, 1m for 1 month, etc
        TWO_WEEKS = 1209600
        self.expiration = TWO_WEEKS

    @staticmethod
    def init(config, db, dbtables):
        if not UserService._instance:
            UserService._instance = UserService(config, db, dbtables)
        return UserService._instance

    @staticmethod
    def instance():
        return UserService._instance

    def createUser(self, email, domain, role, password):

        domain = self.userDao.findDomainByName(domain)
        role = self.userDao.findRoleByName(role)
        user_id = self.userDao.createUser(
                email,
                password,
                domain['id'],
                role['id']
            )
        default_user_quota = self.settingsDao.get(Settings.default_user_quota)
        self.storageDao.setUserDiskQuota(user_id, default_user_quota)

        return user_id

    def getUserByPassword(self, email, password):

        # TODO: decompose email into username@Domain/Role

        return self.userDao.findUserByEmailAndPassword(email, password)

    def getUserFromBasicToken(self, token, features=None):

        # TODO: decompose email from user@domain/role
        # and set the domain and role correctly

        email, password = parse_basic_token(token)

        user = self.userDao.findUserByEmailAndPassword(email, password)

        if not user:
            raise Exception("user %s does not exist or password incorrect" % email)

        user_data = {
            "id": user.id,
            "email": user.email,
            "domain_id": user.domain_id,
            "role_id": user.role_id
        }

        self._validate_features(user_data, features)

        return user_data

    def getUserFromApikey(self, token, features=None):

        apikey = parse_apikey_token(token)

        user = self.userDao.findUserByApiKey(apikey)

        if not user:
            raise Exception("user %s does not exist or password incorrect" % email)

        user_data = {
            "id": user.id,
            "email": user.email,
            "domain_id": user.domain_id,
            "role_id": user.role_id
        }

        self._validate_features(user_data, features)

        return user_data

    def getUserFromToken(self, token, features=None):

        try:
            user_data = verify_token(self.secret, token)

            self._validate_features(user_data, features)

            return user_data
        except WebTokenException:
            pass
        #except BadSignature:
        #    pass
        #except SignatureExpired:
        #    pass

        raise UserException("Invalid Token")

    def getUserFromUUIDToken(self, token, features=None):

        key = sha256(self.secret.encode('utf-8'))[:16]
        uuid_str = uuid_token_verify(key, token)

        user = self.userDao.findUserById(uuid_str)

        if not user:
            raise Exception("user %s does not exist or password incorrect" % email)

        user_data = {
            "id": user.id,
            "email": user.email,
            "domain_id": user.domain_id,
            "role_id": user.role_id
        }

        self._validate_features(user_data, features)

        return user_data

    def loginUser(self, email, password):

        user = self.getUserByPassword(email, password)

        if not user:
            raise UserServiceException("Unable to login user", 401)

        return generate_token(self.secret, user, self.expiration)

    def verifyToken(self, token):

        is_valid = False
        reason = ""
        try:
            if verify_token(self.secret, token):
                is_valid = True
                reason = "OK"
        except BadSignature:
            is_valid = False
            reason = "Bad Signature"
        except SignatureExpired:
            is_valid = False
            reason = "Expired Signature"

        return is_valid, reason

    def generateUUIDToken(self, user, expiry):

        key = sha256(self.secret.encode('utf-8'))[:16]
        token = uuid_token_generate(key, user['id'], expiry)
        return token

    def changeUserPassword(self, user, new_password):

        self.userDao.changeUserPassword(user['id'], new_password)

    def listUser(self, userId):

        user = self.userDao.findUserById(userId)

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
            # todo: features here should be the list of features for the
            # default role. I may want to remove this in the future
            # and upadte the frontend to correctly process this structure
            # added for compatability with the old framework
            "features": features,
            # todo: I should only return this once on a successful login...
            "apikey": user['apikey']
        }

        return user_info

    def listDomainUsers(self, domainName):

        did = self.userDao.findDomainByName(domainName).id

        domains = {d['id']: d['name'] for d in self.userDao.listDomains()}
        roles = {r['id']: r['name'] for r in self.userDao.listRoles()}
        users = self.userDao.listUsers(did)

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
        return has_feat

    def _validate_features(self, user_data, features=None):

        if features is not None and features:
            if not self._validate_user_feature(user_data, features[0]):
                raise UserException(
                    "failed to authenticate user %s with feature %s" % (
                        user_data['email'], features[0]))