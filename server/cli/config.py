#! cd ../.. && python migrate_db.py test

import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

from ..dao.user import UserDao
from ..dao.library import LibraryDao

class ConfigException(Exception):
    """docstring for ConfigException"""
    def __init__(self, path, message):

        message = "Configuration Error with %s: %s" % (
            path, message)

        super(ConfigException, self).__init__(message)

def yaml_assert_list_of_string(data, key):

    if not isinstance(data[key], list):
        raise ConfigException(config_path, "%s must be a list" % key)

    for feat in data[key]:
        if not isinstance(feat, str):
            raise ConfigException(config_path,
                "%s must be a list of strings" % key)

def yaml_assert(data):

    yaml_assert_list_of_string(data, "features")

    yaml_assert_list_of_string(data, "domains")

    if not isinstance(data['roles'], list):
        raise ConfigException(config_path, "roles must be a list")

    for role in data['roles']:
        for name, items in role.items():
            yaml_assert_list_of_string(items, "features")

    for user in data['users']:

        if "email" not in user:
            raise ConfigException(config_path, "user must have an email")

        if "password" not in user:
            raise ConfigException(config_path, "user must have a password")

        yaml_assert_list_of_string(user, "domains")
        yaml_assert_list_of_string(user, "roles")

def db_drop_all(db, dbtables):
    """ drop all tables from database """
    db.drop_all()
    db.session.commit()

def db_init(db, dbtables, config_path):

    with open(config_path, "r") as rf:
        data = yaml.load(rf, Loader=Loader)

    yaml_assert(data)

    db.create_all()

    userDao = UserDao(db, dbtables)

    for feature in data['features']:
        userDao.createFeature(feature, commit=False)

    for domain in data['domains']:
        userDao.createDomain(domain, commit=False)

    for item in data['roles']:
        for role, child in item.items():
            role_id = userDao.createRole(role, commit=False)
            for name in child['features']:
                if name == "all":
                    for feat in userDao.listFeatures():
                        userDao.addFeatureToRole(
                            role_id, feat['id'], commit=False)
                else:
                    feat = userDao.findFeatureByName(name)
                    userDao.addFeatureToRole(
                        role_id, feat['id'], commit=False)

    for user in data['users']:

        domains = user['domains']
        roles = user['roles']

        default_domain = userDao.findDomainByName(domains.pop(0))
        default_role = userDao.findRoleByName(roles.pop(0))

        user_id = userDao.createUser(user['email'],
                                     user['password'],
                                     default_domain['id'],
                                     default_role['id'])

        # grant additional domains
        for name in domains:
            domain = userDao.findDomainByName(name)
            userDao.grantDomain(user_id, domain['id'])

        # grant additional roles
        for name in roles:
            role = userDao.findRoleByName(name)
            userDao.grantRole(user_id, role['id'])

    db.session.commit()

def db_init_test(db, dbtables, config_path):

    # create initial environment
    db_init(db, dbtables, config_path)

    userDao = UserDao(db, dbtables)
    libDao = LibraryDao(db, dbtables)

    user = userDao.findUserByEmail("user000")

    # create additional resources for testing
    for a in range(3):
        for b in range(3):
            for t in range(3):
                song = {
                    "artist": "Artist%03d" % a,
                    "album": "Album%03d" % b,
                    "title": "Title%03d" % t,
                    "rating": int(10 * (a * b * t) / 27)
                }
                libDao.insert(user['id'], user['domain_id'],
                    song, commit=False)
    db.session.commit()


