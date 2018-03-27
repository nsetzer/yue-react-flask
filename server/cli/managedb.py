
from ..dao.user import UserDao
from ..dao.library import LibraryDao

import time

def db_populate(db, dbtables, username, domain_name, json_objects):
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
        sys.exit(1)

    user = userDao.findUserByEmail(username)

    print("Migrating Database:")
    start = time.time()
    count = 0
    try:
        db.session.execute("PRAGMA JOURNAL_MODE = MEMORY");
        db.session.execute("PRAGMA synchronous = OFF");
        db.session.execute("PRAGMA TEMP_STORE = MEMORY");
        db.session.execute("PRAGMA LOCKING_MODE = EXCLUSIVE");

        bulk_songs = []
        bulk_users = []
        for new_song in json_objects:
            if count % 100 == 0 and count > 1:
                end = time.time()
                t = (end-start)
                print("%d %.2f %.2f" % (count, count / t, t))

            song_data = libraryDao.prepareSongDataInsert(domain.id, new_song)
            bulk_songs.append(song_data)

            user_data = libraryDao.prepareUserDataInsert(user.id, domain.id, new_song)
            if user_data:
                bulk_users.append(user_data)

            #song_id = libraryDao.insert(
            #    user.id, domain.id,
            #    new_song,
            #    commit=False)

            #song_id = libraryDao.insertOrUpdateByReferenceId(
            #    user.id, domain.id,
            #    new_song[Song.ref_id], new_song,
            #    commit=False)
            count += 1

        print("prepared %d songs in %.3f seconds, performing bulk insert" % (count, t))

        libraryDao.bulkInsertSongData(bulk_songs, False)
        if bulk_users:
            libraryDao.bulkInsertUserData(bulk_users, False)

    except KeyboardInterrupt:
        pass
    finally:
        db.session.commit()

    end = time.time()

    t = end - start
    print("migrated %d songs in %.3f seconds" % (count, t))


def db_repopulate(db, dbtables, username, domain_name, json_objects):
     print(len(list(json_objects)))
