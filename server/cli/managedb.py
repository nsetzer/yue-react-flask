
from ..dao.user import UserDao
from ..dao.library import Song, LibraryDao
from ..dao.tables.tables import DatabaseTables

import logging
import time

from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm.session import sessionmaker

def db_connect(connection_string):
    """
    a reimplementation of the Flask-SqlAlchemy integration
    """
    Session = sessionmaker()

    engine = create_engine(connection_string)
    Session.configure(bind=engine)

    db = lambda : None
    db.metadata = MetaData()
    db.session = Session()
    db.tables = DatabaseTables(db.metadata)
    db.create_all = lambda: db.metadata.create_all(engine)
    db.connection_string = connection_string

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
        sys.stdout.write("Domain with name `%s` not found" % domain_name)
        return

    user = userDao.findUserByEmail(user_name)
    if user is None:
        sys.stdout.write("User with name `%s` not found" % user_name)
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
        sys.stdout.write("Domain with name `%s` not found" % domain_name)
        return

    user = userDao.findUserByEmail(user_name)
    if user is None:
        sys.stdout.write("User with name `%s` not found" % user_name)
        return

    start = time.time()
    count = 0
    try:

        db.session.execute("PRAGMA JOURNAL_MODE = MEMORY");
        db.session.execute("PRAGMA synchronous = OFF");
        db.session.execute("PRAGMA TEMP_STORE = MEMORY");
        db.session.execute("PRAGMA LOCKING_MODE = EXCLUSIVE");

        for song in json_objects:
            song_id = libraryDao.insertOrUpdateByReferenceId(
                user.id, domain.id, song[Song.ref_id], song, commit=False)
            count += 1
    except KeyboardInterrupt:
        pass
    finally:
        db.session.commit()

        end = time.time()

    t = end - start
    logging.info("updated %d songs in %.3f seconds" % (count, t))
