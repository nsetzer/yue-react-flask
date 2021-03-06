
"""
A Data Access Object for manipulating the library table

"""

import logging

from sqlalchemy.orm import relationship
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, not_, case, select, update, column, func, asc, desc
from sqlalchemy.sql.expression import bindparam
from .search import SearchGrammar, ParseError, Rule

import datetime, time
import uuid

class Song(object):
    """docstring for Song"""

    id          = 'id'          # unique identifier for song
    ref_id      = 'ref_id'      # uid for aiding migration
    user_id     = 'user_id'     # user id for per person fields
    data_id     = 'data_id'     # data id for per person fields
    path        = 'file_path'   # filepath on disk
    art_path    = 'art_path'    # filepath to album art
    static_path = 'static_path' # relative path for database migrations
    artist      = 'artist'      # the full artist name
    artist_key  = 'artist_key'  # naturally sortable artist name
    composer    = 'composer'    # composer of the piece
    album       = 'album'       # the full album title
    title       = 'title'       # the title of the song
    genre       = 'genre'       # comma separated list of genres
    year        = 'year'        # 4 digit year
    country     = 'country'     # contry of origin
    language    = 'language'    # primary language of the song
    comment     = 'comment'     # user information
    album_index = 'album_index'  # order of song in album
    length      = 'length'      # length of the song in seconds
    last_played = 'last_played'  # as unix time stamp
    play_count  = 'play_count'  # number of times song has been played
    skip_count  = 'skip_count'  # number of times song was skipped
    rating      = 'rating'      # from 0 - 10
    banished    = 'banished'     # was 'banished' by domain, type boolean
    blocked     = 'blocked'     # was 'banished' by user, type boolean
    equalizer   = 'equalizer'   # used in automatic volume leveling
    date_added  = 'date_added'  # as unix time stamp
    frequency   = 'frequency'   # how often the song is played (days)
    file_size   = 'file_size'   # in bytes

    all_text    = 'text'

    random = "RANDOM"
    asc = "ASC"
    desc = "DESC"

    abbreviations = {
        "id": id,
        "ref_id": ref_id,
        "user_id": user_id,
        "data_id": data_id,
        "path": path,
        "filepath": path,
        "file_path": path,
        "artpath": art_path,
        "art_path": art_path,
        "static_path": static_path,
        "art": artist,
        "artist": artist,
        "composer": composer,
        "abm": album,
        "alb": album,
        "album": album,
        "ttl": title,
        "tit": title,
        "title": title,
        "gen": genre,
        "genre": genre,
        "year": year,
        "country": country,
        "lang": language,
        "language": language,
        "com": comment,
        "comm": comment,
        "comment": comment,
        "index": album_index,
        "album_index": album_index,
        "len": length,
        "length": length,
        "date": last_played,
        "last_played": last_played,
        "pcnt": play_count,
        "count": play_count,
        "play_count": play_count,
        "playcount": play_count,
        "skip": skip_count,
        "scnt": skip_count,
        "skip_count": skip_count,
        "skipcount": skip_count,
        "rate": rating,
        "rating": rating,
        "text": all_text,
        "all_text": all_text,
        "ban": blocked,
        "banned": blocked,
        "blocked": blocked,
        "eq": equalizer,
        "equalizer": equalizer,
        "added": date_added,
        "freq": frequency,
        "frequency": frequency,
        "file_size": file_size,
        "size": file_size,
    }

    @staticmethod
    def column(abrv):
        return Song.abbreviations[abrv]

    @staticmethod
    def textFields():
        return Song.artist, Song.composer, Song.album, Song.title, \
               Song.genre, Song.country, Song.language, Song.comment

    @staticmethod
    def numberFields():
        """ integer fields """
        # Song.last_played,  Song.date_added,
        return Song.id, Song.year, Song.album_index, Song.length, \
            Song.play_count, Song.skip_count, \
            Song.rating, Song.banished, Song.blocked, Song.equalizer, \
            Song.frequency, Song.file_size

    @staticmethod
    def dateFields():
        return Song.last_played, Song.date_added

    @staticmethod
    def fields():
        result = list(Song.textFields()) + \
                 list(Song.numberFields()) + \
                 list(Song.dateFields())
        return result

    @staticmethod
    def getArtistKey(artist_name):
        if artist_name.lower().startswith("the "):
            artist_name = artist_name[4:]
        return artist_name

    @staticmethod
    def repairGenre(genre):
        """genres can be comma or semicolon separated.
        However, when placed in a database genres are normalized to
        use semicolons and extra spaces are removed.

        this allows for better search performance i.e.:
            ';rock;' and 'rock' will produce different results
        by surrounding the query in semicolons, exact matches can be performed
        without a schema change
        """
        gen = genre.replace(",", ";").strip().split(";")
        gen = [g.strip().title() for g in gen]
        return ";" + ";".join([g for g in gen if g]) + ";"

class SongSearchGrammar(SearchGrammar):

    def __init__(self, dbtables, cols_song, cols_user):
        super(SongSearchGrammar, self).__init__()

        # all_text is a meta-column name which is used to search all text fields
        self.all_text = Song.all_text
        self.text_fields = set(Song.textFields())
        # i still treat the path as a special case even though it really isnt
        self.text_fields.add(Song.path)
        self.date_fields = set(Song.dateFields())
        self.time_fields = set([Song.length, ])
        self.year_fields = set([Song.year, ])

        self.dbtables = dbtables
        self.keys_song = set(cols_song)
        self.keys_user = set(cols_user)

    def translateColumn(self, colid):
        """
        translate the given colid to an internal column name
        e.g. user may type 'pcnt' which expands to 'play_count',
        """
        try:
            return Song.column(colid)
        except KeyError:
            if hasattr(colid, 'pos'):
                raise ParseError("Invalid column name `%s` at position %d" % (colid, colid.pos))
            else:
                raise ParseError("Invalid column name `%s` at position %d" % (colid))

    def getColumnType(self, key):
        """
        translate the given colid to an internal column name
        e.g. convert the string 'play_count' to `SongUserData.play_count`
        """
        if key in self.keys_song:
            return getattr(self.dbtables.SongDataTable.c, key)
        elif key in self.keys_user:
            return getattr(self.dbtables.SongUserDataTable.c, key)
        else:
            if hasattr(key, 'pos'):
                raise ParseError("Invalid column name `%s` at position %d" % (key, key.pos))
            else:
                raise ParseError("Invalid column name `%s`" % (key))

class SongQueryFormatter(object):
    """docstring for SongQueryFormatter
    """
    def __init__(self, dbtables, sanitize=False):
        super(SongQueryFormatter, self).__init__()

        self.dbtables = dbtables

        self.cols_song = self._SongDataColumnNames()
        if sanitize:
            self.cols_song.remove("file_path")
            self.cols_song.remove("art_path")
            self.cols_song.remove("static_path")

        self.cols_user = self._SongUserDataColumnNames()
        self.cols_user.remove("song_id")

        self.defs_song = [self._SongDefault(col) for col in self.cols_song]
        self.defs_user = [self._UserDefault(col) for col in self.cols_user]

        self.cols = self.cols_song + self.cols_user
        self.defs = self.defs_song + self.defs_user

        self.user_index = self.cols.index("user_id")

    def format(self, user_id, results):
        defs = self.defs[:]
        defs[self.user_index] = user_id
        return [{k: (v or d) for k, v, d in zip(self.cols, res, defs)}
            for res in results]

    def _SongDefault(self, col):
        default = getattr(self.dbtables.SongDataTable.c, col).default

        if default is None:
            return ""

        return default.arg

    def _UserDefault(self, col):

        if col in ['last_played', 'date_added']:
            return 0

        default = getattr(self.dbtables.SongUserDataTable.c, col).default
        if default is None:
            return ""

        return default.arg

    def _SongDataColumnNames(self):
        return [c.name for c in self.dbtables.SongDataTable.c]

    def _SongUserDataColumnNames(self):
        return [c.name for c in self.dbtables.SongUserDataTable.c]

class LibraryException(Exception):
    pass

class LibraryDao(object):
    """docstring for Library"""

    def __init__(self, db, dbtables, sanitize=False):
        super(LibraryDao, self).__init__()
        self.db = db
        self.dbtables = dbtables

        self.formatter = SongQueryFormatter(dbtables, sanitize)

        self.grammar = SongSearchGrammar(
            dbtables, self.formatter.cols_song, self.formatter.cols_user)

        self.song_keys = set(self.formatter.cols_song)
        self.user_keys = set(self.formatter.cols_user)

    def insert(self, user_id, domain_id, song, commit=True):

        song_id = self.insertSongData(domain_id, song, False)

        self.insertUserData(user_id, song_id, song, False)

        if commit:
            self.db.session.commit()

        return song_id

    def prepareSongDataInsert(self, domain_id, song):
        """
        returns a dictionary that is ready to be inserted into the database
        """

        if Song.artist not in song:
            msg = "artist key missing from song"
            msg += "or invalid type(%s)" % (type(song))
            raise LibraryException(msg)

        if Song.album not in song:
            msg = "album key missing from song"
            msg += "or invalid type(%s)" % (type(song))
            raise LibraryException(msg)

        if Song.title not in song:
            msg = "title key missing from song"
            msg += "or invalid type(%s)" % (type(song))
            raise LibraryException(msg)

        if Song.artist_key not in song:
            song[Song.artist_key] = Song.getArtistKey(song[Song.artist])

        if Song.genre in song:
            song[Song.genre] = Song.repairGenre(song[Song.genre])

        song_data = {k: song[k] for k in song.keys() if k in self.song_keys}
        song_data['domain_id'] = domain_id

        return song_data

    def insertSongData(self, domain_id, song, commit=True):

        song_data = self.prepareSongDataInsert(domain_id, song)

        query = self.dbtables.SongDataTable.insert() \
            .values(song_data)

        result = self.db.session.execute(query)

        song_id = result.inserted_primary_key[0]

        if commit:
            self.db.session.commit()

        return song_id

    def prepareUserDataInsert(self, user_id, song_id, song):
        """
        returns a dictionary that is ready to be inserted into the database

        Note: the dictionary may be empty indicating no record
        needs to be inserted for the song. This will happen when the
        song contains user information
        """

        user_data = {k: song[k] for k in song.keys() if k in self.user_keys}

        user_data["user_id"] = user_id
        user_data["song_id"] = song_id

        return user_data

    def insertUserData(self, user_id, song_id, song, commit=True):
        """
        Insert multiple songs at once.

        each song in the given list is assumed to be the output
        from prepareSongDataInsert.

        Note: every song in the list should have the same set of keys
        otherwise an insertion error will occur, even for columns which
        have a default value
        """

        user_data = self.prepareUserDataInsert(user_id, song_id, song)

        if user_data:

            query = self.dbtables.SongUserDataTable.insert() \
                .values(user_data)

            result = self.db.session.execute(query)

            if result.rowcount != 1:
                raise LibraryException("User Data insert failed for %s" % song_id)

            if commit:
                self.db.session.commit()

    def update(self, user_id, domain_id, song_id, song, commit=True):

        self.updateSongData(domain_id, song_id, song, commit=False)
        # TODO: investigate what happens when this row does not yet exist
        # see the implementation for incrementPlaycount
        self.updateUserData(user_id, song_id, song, commit=False)

        if commit:
            self.db.session.commit()

    def updateSongData(self, domain_id, song_id, song, commit=True):

        song_keys = set(self.formatter.cols_song)
        song_data = {k: song[k] for k in song.keys() if k in song_keys}

        # TODO: do I need to update the Song.artist_key here
        # if the artist is given and the key is not?

        if song_data:
            query = update(self.dbtables.SongDataTable) \
                .values(song_data) \
                .where(
                    and_(self.dbtables.SongDataTable.c.id == song_id,
                         self.dbtables.SongDataTable.c.domain_id == domain_id))

            result = self.db.session.execute(query)

            if result.rowcount != 1:
                raise LibraryException("Song Data update failed for %s" % song_id)

            if commit:
                self.db.session.commit()

    def updateUserData(self, user_id, song_id, song, commit=True):
        """ update only the user data portion of a song in the database """
        user_keys = set(self.formatter.cols_user)
        user_data = {k: song[k] for k in song.keys() if k in user_keys}

        if user_data:
            query = update(self.dbtables.SongUserDataTable) \
                .values(user_data) \
                .where(
                    and_(self.dbtables.SongUserDataTable.c.song_id == song_id,
                         self.dbtables.SongUserDataTable.c.user_id == user_id))

            result = self.db.session.execute(query)

            # if the update fails, insert the row instead
            if result.rowcount == 0:
                self.insertUserData(user_id, song_id, song, commit=False)

            if commit:
                self.db.session.commit()

    def removeSong(self, domain_id, song_id, commit=True):
        """
        remove the song meta data.
        does not remove the song from s3
        and does not remove the storage entry

        """

        self.removeSongUserData(song_id, commit)
        self.removeSongData(domain_id, song_id, commit)

    def removeSongData(self, domain_id, song_id, commit=True):

        tab = self.dbtables.SongDataTable
        query = tab.delete() \
            .where(
                and_(self.dbtables.SongDataTable.c.id == song_id,
                     self.dbtables.SongDataTable.c.domain_id == domain_id))

        self.db.session.execute(query)

        if commit:
            self.db.session.commit()

    def removeSongUserData(self, song_id, commit=True):

        tab = self.dbtables.SongUserDataTable
        query = tab.delete() \
            .where(self.dbtables.SongUserDataTable.c.song_id == song_id)

        self.db.session.execute(query)

        if commit:
            self.db.session.commit()

    def incrementPlaycount(self, user_id, song_id, commit=True):

        tab = self.dbtables.SongUserDataTable

        query = tab.select().where(
                and_(tab.c.song_id == song_id,
                     tab.c.user_id == user_id))
        result = self.db.session.execute(query).fetchone()

        if result:
            query = tab.update() \
                .values({tab.c.play_count: tab.c.play_count + 1}) \
                .where(
                    and_(tab.c.song_id == song_id,
                         tab.c.user_id == user_id))
        else:
            query = tab.insert() \
                .values({
                    tab.c.song_id: song_id,
                    tab.c.user_id: user_id,
                    tab.c.play_count: 1}) \

        result = self.db.session.execute(query)

        if commit:
            self.db.session.commit()

    def findSongById(self, user_id, domain_id, song_id):
        results = self._query(user_id, domain_id,
                             self.dbtables.SongDataTable.c.id == song_id)

        if len(results) > 0:
            return results[0]
        return None

    def findSongByReferenceId(self, user_id, domain_id, ref_id):
        results = self._query(user_id, domain_id,
                             self.dbtables.SongDataTable.c.ref_id == ref_id)

        if len(results) > 0:
            return results[0]
        return None

    def insertOrUpdateByReferenceId(self, user_id, domain_id, ref_id, song, commit=True):
        """
        insert or update a single song record

        this operation is very slow. consuder using bulkUpsertByRefId if more
        than 1 song needs to be updated in this way.
        """
        results = self._query(user_id, domain_id,
                             self.dbtables.SongDataTable.c.ref_id == ref_id)

        if results:
            song_id = results[0]['id']
            self.update(user_id, domain_id, song_id, song, commit=False)
            return song_id

        song_id = self.insert(user_id, domain_id, song, commit=False)

        if commit:
            self.db.session.commit()

        return song_id

    def bulkUpsertByRefId(self, user_id, domain_id, songs, commit=True):
        """
        insert or update multiple song records in a single operation
        """
        SongData = self.dbtables.SongDataTable
        SongUserData = self.dbtables.SongUserDataTable

        query = select([SongData.c.id, SongData.c.ref_id]) \
            .select_from(SongData) \
            .where(SongData.c.domain_id == domain_id)

        # fetch results and map ref_id to id
        results = self.db.session.execute(query).fetchall()
        idmap = {v:k for k,v in results}

        count = 0
        for song in songs:
            ref_id = song.get(Song.ref_id, None)
            song_id = idmap.get(ref_id, None)
            if song_id is None:
                song_id = self.insertSongData(domain_id, song, commit=False)
                self.insertUserData(user_id, song_id, song, commit=False)
            else:
                self.updateSongData(domain_id, song_id, song, commit=False)
                self.updateUserData(user_id, song_id, song, commit=False)
            count += 1

        if commit:
            self.db.session.commit()

        return count

    def domainSongUserInfo(self, user_id, domain_id):
        """
        generate a document describing artists, albums, and genres in the
        database for a given domain.

        Remove songs blocked by a user

        """
        columns = [column(Song.artist),
                   column(Song.artist_key),
                   column(Song.album),
                   column(Song.genre),
                   column(Song.blocked),
                   column(Song.banished)]

        SongData = self.dbtables.SongDataTable
        SongUserData = self.dbtables.SongUserDataTable

        query = select(columns) \
            .select_from(
                    SongData.join(
                        SongUserData,
                        and_(SongData.c.id == SongUserData.c.song_id,
                             SongUserData.c.user_id == user_id),
                        isouter=True)) \
            .where(self.dbtables.SongDataTable.c.domain_id == domain_id)

        return self._getDomainSongInfo(query)

    def domainSongInfo(self, domain_id):
        """
        generate a document describing artists, albums, and genres in the
        database for a given domain.

        in testing, this takes about 1/4 of the time of calling search()
        """
        columns = [column(Song.artist),
                   column(Song.artist_key),
                   column(Song.album),
                   column(Song.genre),
                   column(Song.banished)]

        query = select(columns) \
            .select_from(self.dbtables.SongDataTable) \
            .where(self.dbtables.SongDataTable.c.domain_id == domain_id)

        return self._getDomainSongInfo(query)

    def _getDomainSongInfo(self, query):

        keys = {}
        artists = {}
        genres = {}
        n_records1 = 0
        total = 0

        genre_artists = {}

        for record in self.db.session.execute(query).fetchall():
            key = record[Song.artist_key]
            art = record[Song.artist]
            alb = record[Song.album]

            n_records1 += 1
            # ignored songs banished by the domain
            if record[Song.banished]:
                continue

            # ignored songs blocked by the user (for domainSongUserInfo)
            if Song.blocked in record and record[Song.blocked]:
                continue

            # genres are comma or colon deliminated
            gen = record[Song.genre].replace(",", ";").strip()
            if not gen:
                gen  = [ ]
            else:
                # attempt to de-duplicate genre names
                gen = [g.strip().title() for g in gen.split(";")]
                gen = [g for g in gen if g]

            # count artist and album
            if art not in artists:
                artists[art] = {"count": 0,
                                "albums": {},
                                "name": art,
                                "genres": []}
                keys[art] = key

            artists[art]['count'] += 1
            albums = artists[art]['albums']

            # count genres for the record
            for g in gen:
                if g and g not in genres:
                    genres[g] = {"name": g, "count": 0, "artist_count": 0}
                genres[g]['count'] += 1
                if g not in artists[art]['genres']:
                    artists[art]['genres'].append(g)

                if g not in genre_artists:
                    genre_artists[g] = set()
                genre_artists[g].add(art)

            # count the number of artists in each genre
            for g, items in genre_artists.items():
                genres[g]['artist_count'] = len(items)

            # count the number of songs for this album
            if alb not in albums:
                albums[alb] = 0
            albums[alb] += 1

            total += 1

        artists = sorted(artists.values(), key=lambda x: keys[x['name']])
        genres = sorted(genres.values(), key=lambda x: x['name'])

        data = {
            # artists is a sorted list of items containing fields:
            # count, name, albums, genres
            # albums: map str -> item :: item: map str -> count
            # genres: seq str
            "artists": artists,

            # genres is a sorted list of items containing fields:
            # name, count, artist_count
            "genres": genres,

            # the total number of songs counted
            "num_songs": total
        }

        return data

    def search(self,
        user_id,
        domain_id,
        rule,
        case_insensitive=True,
        orderby=None,
        limit=None,
        offset=None,
        showBanished=False,
        debug=False):

        if not isinstance(rule, Rule):
            rule = self.grammar.ruleFromString(rule)

        SongTable = self.dbtables.SongDataTable.c
        UserTable = self.dbtables.SongUserDataTable.c

        sql_rule = rule.psql() if self.db.kind() == "postgresql" else rule.sql()
        logging.info("rule: %s" % sql_rule)

        if not showBanished:
            # remove entries that have either the blocked or banished bit set
            stmt1 = SongTable.banished == 0
            # if the left outer join produces a null, default to 0 and compare.
            stmt2 = case([(UserTable.blocked == None, 0)],
                         else_=UserTable.blocked) == 0
            stmt3 = and_(stmt1, stmt2)
            sql_rule = stmt3 if sql_rule is None else and_(sql_rule, stmt3)

        if orderby is not None:
            orderby = self._getSearchOrder(case_insensitive, orderby)

        if debug:
            logging.debug(sql_rule)

        return self._query(user_id, domain_id, sql_rule, orderby, limit, offset)

    def paginate(self,
        user_id,
        domain_id,
        rule,
        case_insensitive=True,
        limit=None,
        last_id=None,
        showBanished=False):
        """
        similar to search, but use last_id to control paging in a more efficient
        way.


        To use, the first query will not set last_id. up to limit results are
        then returned. the last id found in the first search should be fed
        into the subsequent result.

        orderby is always set to sort the id ascending. this is an indexed
        table. the query can then use greater than comparisons on id
        to skip to a particular page efficiently

        """
        print(user_id, domain_id, rule, case_insensitive, last_id, limit)

        if not isinstance(rule, Rule):
            rule = self.grammar.ruleFromString(rule)

        SongTable = self.dbtables.SongDataTable.c
        UserTable = self.dbtables.SongUserDataTable.c

        sql_rule = rule.psql() if self.db.kind() == "postgresql" else rule.sql()

        orderby = [asc(self.grammar.getColumnType(Song.id))]

        if last_id is not None:
            if sql_rule:
                sql_rule = and_(sql_rule, SongTable.id > last_id)
            else:
                sql_rule = SongTable.id > last_id

        if not showBanished:
            # remove entries that have either the blocked or banished bit set
            stmt1 = SongTable.banished == 0
            # if the left outer join produces a null, default to 0 and compare.
            stmt2 = case([(UserTable.blocked == None, 0)],
                         else_=UserTable.blocked) == 0
            stmt3 = and_(stmt1, stmt2)
            sql_rule = stmt3 if sql_rule is None else and_(sql_rule, stmt3)

        logging.debug(sql_rule)

        return self._query(user_id, domain_id, sql_rule, orderby, limit)

    def _query(self,
        user_id,
        domain_id,
        where=None,
        orderby=None,
        limit=None,
        offset=None):
        SongData = self.dbtables.SongDataTable
        SongUserData = self.dbtables.SongUserDataTable

        if where is not None:
            where = and_(SongData.c.domain_id == domain_id, where)
        else:
            where = SongData.c.domain_id == domain_id

        query = select([column(c) for c in self.formatter.cols]) \
            .select_from(
                    SongData.join(
                        SongUserData,
                        and_(SongData.c.id == SongUserData.c.song_id,
                             SongUserData.c.user_id == user_id),
                        isouter=True)) \
            .where(where)

        if orderby is not None:
            query = query.order_by(*orderby)

        if limit is not None:
            query = query.limit(limit)

        if offset is not None:
            query = query.offset(offset)

        results = self.db.session.execute(query).fetchall()

        return self.formatter.format(user_id, results)

    def _getSearchOrder(self, case_insensitive, orderby):

        # orderby can be:
        # random:
        #  - Song.random
        # a string:
        #  - Song.column
        # a list of strings:
        #  - (Song.column, Song.column)
        # a list of tuples:
        #  - ( (Song.column, dir) , (Song.column, dir) )
        # dir should be a string `ASC` or `DESC`

        direction = asc

        if orderby == Song.random:
            return [func.random(), ]

        if not isinstance(orderby, (tuple, list)):
            orderby = [orderby, ]

        order = []
        for item in orderby:

            if isinstance(item, (tuple, list)):
                col_type = self.grammar.getColumnType(item[0])

                if case_insensitive and item[0] in Song.textFields():
                    col_type = func.lower(col_type)

                direction = asc if item[1].upper() == Song.asc else desc

                order.append(direction(col_type))
            else:
                col_type = self.grammar.getColumnType(item)

                if case_insensitive and item in Song.textFields():
                    col_type = func.lower(col_type)

                order.append(direction(col_type))

        return order


