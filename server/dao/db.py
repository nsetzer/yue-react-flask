
from .user import UserDao
from .library import Song, LibraryDao
from .tables.tables import DatabaseTables
from .search import regexp

import os
import sys
import logging
import time
import random
import logging
import argparse
import unittest

from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm.session import sessionmaker

import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

def db_remove(db_path):
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except PermissionError:
            sys.stderr.write("\nUnable to remove database: %s\n" % db_path)
            return False
    return True

def _abort_flush(*args, **kwargs):
    """monkey patch db.session.flush to prevent writing to the database"""
    sys.stderr.write("ERROR: flush. Database open in readonly mode\n")
    return

def db_connect(connection_string=None, readonly=False):
    """
    a reimplementation of the Flask-SqlAlchemy integration
    """
    Session = sessionmaker()

    # connect to a SQLite :memory: database
    if connection_string is None or connection_string == ":memory:":
        connection_string = 'sqlite://'

    engine = create_engine(connection_string)
    Session.configure(bind=engine)

    db = lambda: None
    db.engine = engine
    db.metadata = MetaData()
    db.session = Session()
    if readonly:
        db.session.flush = _abort_flush
    db.tables = DatabaseTables(db.metadata)
    db.create_all = lambda: db.metadata.create_all(engine)
    db.delete_all = lambda: db.tables.drop(db.engine)
    db.disconnect = lambda: engine.dispose()
    db.connection_string = connection_string
    db.kind = lambda: connection_string.split(":")[0]

    db.conn = db.session.bind.connect()
    if connection_string.startswith("sqlite:"):
        db.conn.connection.create_function('REGEXP', 2, regexp)

    return db

def db_populate(db, dbtables, user_name, domain_name, json_objects):
    """
    username: username to associate with the new songs
    domain_name: name of the domain for songs to be available in
    json_objects: an iterable of json objects reprenting songs

    each song record requires an Artist, Album Title,
    and a reference id "ref_id". the ref_id is used to associate the
    old style database format with the database used by the web app.
    """

    userDao = UserDao(db, dbtables)
    libraryDao = LibraryDao(db, dbtables)

    domain = userDao.findDomainByName(domain_name)
    if domain is None:
        sys.stderr.write("Domain with name `%s` not found" % domain_name)
        return

    user = userDao.findUserByEmail(user_name)
    if user is None:
        sys.stderr.write("User with name `%s` not found" % user_name)
        return

    start = time.time()
    count = 0
    try:
        db.session.execute("PRAGMA JOURNAL_MODE = MEMORY");
        db.session.execute("PRAGMA synchronous = OFF");
        db.session.execute("PRAGMA TEMP_STORE = MEMORY");
        db.session.execute("PRAGMA LOCKING_MODE = EXCLUSIVE");

        for song in json_objects:
            song_id = libraryDao.insert(
                user.id, domain.id, song, commit=False)
            count += 1

    except KeyboardInterrupt:
        pass
    finally:
        db.session.commit()

    end = time.time()

    t = end - start
    logging.info("imported %d songs in %.3f seconds" % (count, t))

def db_repopulate(db, dbtables, user_name, domain_name, json_objects):

    userDao = UserDao(db, dbtables)
    libraryDao = LibraryDao(db, dbtables)

    domain = userDao.findDomainByName(domain_name)
    if domain is None:
        sys.stderr.write("Domain with name `%s` not found\n" % domain_name)
        return False

    user = userDao.findUserByEmail(user_name)
    if user is None:
        sys.stderr.write("User with name `%s` not found\n" % user_name)
        return False

    start = time.time()

    count = libraryDao.bulkUpsertByRefId(
            user.id, domain.id, json_objects)

    end = time.time()

    t = end - start
    logging.info("updated %d songs in %.3f seconds" % (count, t))

    return True

class ConfigException(Exception):
    """docstring for ConfigException"""
    def __init__(self, message):

        message = "Configuration Error: %s" % (message)

        super(ConfigException, self).__init__(message)

def yaml_assert_list_of_string(data, key):

    if not isinstance(data[key], list):
        raise ConfigException("%s must be a list" % key)

    for feat in data[key]:
        if not isinstance(feat, str):
            raise ConfigException(
                "%s must be a list of strings" % key)

def yaml_assert(data):

    yaml_assert_list_of_string(data, "features")

    yaml_assert_list_of_string(data, "domains")

    if not isinstance(data['roles'], list):
        raise ConfigException("roles must be a list")

    for role in data['roles']:
        for name, items in role.items():
            yaml_assert_list_of_string(items, "features")
            for feat in items["features"]:
                if feat not in data['features'] and feat != "all":
                    raise ConfigException("unknown user feature: %s" % feat)

    for user in data['users']:

        for field in ["email", "password", "domains", "roles"]:
            if field not in user:
                raise ConfigException("user must have field: %s" % field)

        yaml_assert_list_of_string(user, "domains")
        yaml_assert_list_of_string(user, "roles")

def db_drop_all(db, dbtables):
    """ drop all tables from database """
    db.drop_all()
    db.session.commit()

def _db_create_role(userDao, role_name, child):
    n_changes = 0
    role_id = userDao.createRole(role_name, commit=False)
    for feat_name in child['features']:
        if feat_name == "all":
            for feat in userDao.listAllFeatures():
                logging.info("adding feature %s to role %s" % (feat['feature'], role_name))
                feat_id = feat['id']
                userDao.addFeatureToRole(
                    role_id, feat_id, commit=False)
                n_changes += 1
        else:
            logging.info("adding feature %s to role %s" % (feat_name, role_name))
            feat = userDao.findFeatureByName(feat_name)
            if feat is None:
                raise ConfigException("Unknown feature: %s" % feat_name)
            feat_id = feat['id']
            userDao.addFeatureToRole(
                role_id, feat_id, commit=False)
            n_changes += 1
    return n_changes

def _db_update_role(userDao, role_name, child):
    n_changes = 0
    role = userDao.findRoleByName(role_name)
    for feat_name in child['features']:
        if feat_name == "all":
            for feat in userDao.listAllFeatures():
                logging.info("adding feature %s to role %s" % (feat['feature'], role_name))
                if not userDao.roleHasFeature(role.id, feat['id']):
                    userDao.addFeatureToRole(
                        role.id, feat['id'], commit=False)
                    n_changes += 1
        else:
            logging.info("adding feature %s to role %s" % (feat_name, role_name))
            feat = userDao.findFeatureByName(feat_name)
            if not userDao.roleHasFeature(role.id, feat['id']):
                userDao.addFeatureToRole(
                    role.id, feat['id'], commit=False)
                n_changes += 1
    return n_changes

def db_init(db, dbtables, config_path):

    logging.info("reading configuration: %s" % config_path)
    with open(config_path, "r") as rf:
        data = yaml.load(rf, Loader=Loader)

    return db_init_main(db, dbtables, data)

def db_init_main(db, dbtables, data):

    yaml_assert(data)

    db.create_all()

    userDao = UserDao(db, dbtables)

    for feat_name in data['features']:
        logging.info("creating feature: %s" % feat_name)
        userDao.createFeature(feat_name, commit=False)

    for domain_name in data['domains']:
        logging.info("creating domain: %s" % domain_name)
        userDao.createDomain(domain_name, commit=False)

    for item in data['roles']:
        for role_name, child in item.items():
            logging.info("creating role: %s" % role_name)
            _db_create_role(userDao, role_name, child)

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

def db_update(db, dbtables, config_path):

    # removing roles or domains and modifing users is
    # beyond the scope of this function

    logging.info("reading configuration: %s" % config_path)
    with open(config_path, "r") as rf:
        data = yaml.load(rf, Loader=Loader)


    return db_update_main(db, dbtables, data)

def db_update_main(db, dbtables, data):

    yaml_assert(data)

    n_changes = 0

    db.create_all()

    userDao = UserDao(db, dbtables)

    cfg_features = set(data['features'])
    all_features = set(feat['feature'] for feat in userDao.listAllFeatures())
    # the set of features to be removed from the database
    rem_features = all_features - cfg_features
    # the set of features to be added to the database
    new_features = cfg_features - all_features

    for feat_name in rem_features:
        logging.info("removing feature: %s" % feat_name)
        feat = userDao.findFeatureByName(feat_name)
        userDao.dropFeature(feat['id'], commit=False)
        n_changes += 1

    for feat_name in new_features:
        logging.info("creating feature: %s" % feat_name)
        userDao.createFeature(feat_name, commit=False)
        n_changes += 1

    cfg_domains = set(data['domains'])
    all_domains = set(d['name'] for d in userDao.listDomains())
    # the set of features to be added to the database
    new_domains = cfg_domains - all_domains

    for domain_name in new_domains:
        logging.info("creating domain: %s" % domain_name)
        userDao.createDomain(domain_name, commit=False)
        n_changes += 1

    cfg_roles = set()
    for item in data['roles']:
        for role, child in item.items():
            cfg_roles.add(role)
    all_roles = set(role['name'] for role in userDao.listRoles())
    # the set of roles to be removed from the database
    # rem_roles = all_roles - cfg_roles
    # the set of roles to be added to the database
    new_roles = cfg_roles - all_roles
    # update these roles for any changes to their features
    update_roles = all_roles & cfg_roles

    for role_name in new_roles:
        for item in data['roles']:
            if role_name in item:
                logging.info("creating role: %s" % role_name)
                child = item[role_name]
                n_changes += _db_create_role(userDao, role_name, child)

    for role_name in update_roles:
        for item in data['roles']:
            if role_name in item:
                child = item[role_name]
                n_changes += _db_update_role(userDao, role_name, child)

    db.session.commit()

    return n_changes;

_db_test_connection_string = ":memory:"
def db_connect_test(name):
    db = db_connect(_db_test_connection_string)

    # TODO: prevent connecting to production databases if possible...
    # query = db.tables.DomainTable.select() \
    #     .where(db.tables.DomainTable.c.name == "production")
    # result = db.session.execute(query)
    # domains = result.fetchall()
    # if len(domains) > 0:
    #     sys.exit(1)

    return db

def set_test_db(connection_string):
    global _db_test_connection_string
    _db_test_connection_string = connection_string

def main_test(argv, module_items):

    parser = argparse.ArgumentParser(description='Process some integers.')

    parser.add_argument('--db', default=":memory:",
        help="database connection string (:memory:)")

    args = parser.parse_args(argv[1:])

    suite = unittest.TestSuite()

    set_test_db(args.db)

    for name, item in module_items.items():

        if name.endswith("TestCase"):
            suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(item))

    unittest.TextTestRunner().run(suite)
