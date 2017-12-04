

from ..index import db
from sqlalchemy.orm import relationship
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, not_, select, update, column, func, asc, desc

from .search import SearchGrammar, ParseError

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
    blocked     = 'blocked'     # was 'banished', type boolean
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
    }

    def __init__(self, arg):
        super(Song, self).__init__()
        self.arg = arg

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
            Song.rating, Song.blocked, Song.equalizer, \
            Song.frequency

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

class SongSearchGrammar(SearchGrammar):
    """docstring for SongSearchGrammar"""

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

class LibraryException(Exception):
    pass

class LibraryDao(object):
    """docstring for Library"""

    def __init__(self, db, dbtables):
        super(LibraryDao, self).__init__()
        self.db = db
        self.dbtables = dbtables

        self.cols_song = self._SongDataColumnNames()
        self.cols_user = self._SongUserDataColumnNames()
        self.cols_user.remove('song_id')

        self.defs_song = [self._SongDefault(col) for col in self.cols_song]
        self.defs_user = [self._UserDefault(col) for col in self.cols_user]

        self.cols = self.cols_song + self.cols_user
        self.defs = self.defs_song + self.defs_user

        self.grammar = SongSearchGrammar(dbtables, self.cols_song, self.cols_user)

    def insert(self, user_id, domain_id, song, commit=True):

        song_id = self.insertSongData(domain_id, song, False)

        self.insertUserData(user_id, song_id, song, False)

        if commit:
            self.db.session.commit()

        return song_id

    def insertSongData(self, domain_id, song, commit=True):

        if Song.artist not in song:
            raise LibraryException("artist key missing from song")

        if Song.album not in song:
            raise LibraryException("album key missing from song")

        if Song.title not in song:
            raise LibraryException("title key missing from song")

        if Song.artist_key not in song:
            song[Song.artist_key] = Song.getArtistKey(song[Song.artist])

        song_keys = set(self._SongDataColumnNames())
        song_data = {k: song[k] for k in song.keys() if k in song_keys}
        song_data['domain_id'] = domain_id

        query = self.dbtables.SongDataTable.insert() \
            .values(song_data)

        result = self.db.session.execute(query)

        song_id = result.inserted_primary_key[0]

        if commit:
            self.db.session.commit()

        return song_id

    def insertUserData(self, user_id, song_id, song, commit=True):

        user_keys = set(self._SongUserDataColumnNames())
        user_data = {k: song[k] for k in song.keys() if k in user_keys}

        if user_data:

            user_data["user_id"] = user_id
            user_data["song_id"] = song_id

            query = self.dbtables.SongUserDataTable.insert() \
                .values(user_data)

            self.db.session.execute(query)

            if commit:
                self.db.session.commit()

    def update(self, user_id, domain_id, song_id, song, commit=True):

        self.updateSongData(domain_id, song_id, song, commit=False)
        self.updateUserData(user_id, song_id, song, commit=False)

        if commit:
            self.db.session.commit()

    def updateSongData(self, domain_id, song_id, song, commit=True):

        song_keys = set(self._SongDataColumnNames())
        song_data = {k: song[k] for k in song.keys() if k in song_keys}

        if song_data:
            query = update(self.dbtables.SongDataTable) \
                .values(song_data) \
                .where(
                    and_(self.dbtables.SongDataTable.c.song_id == song_id,
                         self.dbtables.SongDataTable.c.domain_id == domain_id))
            self.db.session.execute(query)

            if commit:
                self.db.session.commit()

    def updateUserData(self, user_id, song_id, song, commit=True):
        """ update only the user data portion of a song in the database """
        user_keys = set(self._SongUserDataColumnNames())
        user_data = {k: song[k] for k in song.keys() if k in user_keys}

        if user_data:
            query = update(self.dbtables.SongUserDataTable) \
                .values(user_data) \
                .where(
                    and_(self.dbtables.SongDataTable.c.song_id == song_id,
                         self.dbtables.SongDataTable.c.user_id == user_id))
            self.db.session.execute(query)

            if commit:
                self.db.session.commit()

    def findSongById(self, user_id, domain_id, song_id):
        results = self._query(user_id, domain_id,
                             self.dbtables.SongDataTable.c.id == song_id)

        if len(results) > 0:
            return results[0]
        return None

    def insertOrUpdateByReferenceId(self, user_id, domain_id, ref_id, song, commit=True):

        results = self._query(user_id, domain_id,
                             self.dbtables.SongDataTable.c.ref_id == ref_id)

        if results:
            self.update(user_id, domain_id, results[0]['id'], song)
            return results[0]['id']

        song_id = self.insert(user_id, domain_id, song)

        if commit:
            self.db.session.commit()

        return song_id

    def search(self,
        user_id,
        domain_id,
        searchTerm,
        case_insensitive=True,
        orderby=None,
        limit=None,
        offset=None):

        rule = self.grammar.ruleFromString(searchTerm)

        sql_rule = rule.sql()

        if orderby is not None:
            orderby = self._getSearchOrder(case_insensitive, orderby)

        return self._query(user_id, domain_id, sql_rule, orderby, limit, offset)

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

        query = select([column(c) for c in self.cols]) \
            .select_from(
                    SongData.join(
                        SongUserData,
                        and_(SongData.c.id == SongUserData.c.song_id,
                             SongUserData.c.user_id == user_id),
                        isouter=True)) \
            .where(where)

        if orderby is not None:
            query = query.order_by(*order)

        if limit is not None:
            query = query.limit(limit)

        if offset is not None:
            query = query.offset(offset)

        results = db.session.execute(query).fetchall()

        return [{k: (v or d) for k, v, d in zip(self.cols, res, self.defs)}
                for res in results]

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




