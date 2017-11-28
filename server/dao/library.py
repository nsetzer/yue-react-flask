

from ..index import db
from sqlalchemy.orm import relationship
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, not_, select, column, func, asc, desc

from ..models.user import User
from ..models.song import SongData, SongUserData

from .search import SearchGrammar, ParseError

import datetime, time
import uuid

_cols_song = SongData.column_names()
_cols_user = SongUserData.column_names()
_cols_user.remove("song_id")

_defs_song = [SongData.default(col) for col in _cols_song]
_defs_user = [SongUserData.default(col) for col in _cols_user]

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
    def all_columns():
        return _cols_song + _cols_user

    @staticmethod
    def all_defaults():
        return _defs_song + _defs_user

    @staticmethod
    def getArtistKey(artist_name):
        if artist_name.lower().startswith("the "):
            artist_name = artist_name[4:]
        return artist_name

class SongSearchGrammar(SearchGrammar):
    """docstring for SongSearchGrammar"""

    def __init__(self):
        super(SongSearchGrammar, self).__init__()

        # all_text is a meta-column name which is used to search all text fields
        self.all_text = Song.all_text
        self.text_fields = set(Song.textFields())
        # i still treat the path as a special case even though it really isnt
        self.text_fields.add(Song.path)
        self.date_fields = set(Song.dateFields())
        self.time_fields = set([Song.length, ])
        self.year_fields = set([Song.year, ])

        self.keys_song = set(SongData.column_names())
        self.keys_user = set(SongUserData.column_names())

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
            return getattr(SongData, key)
        elif key in self.keys_user:
            return getattr(SongUserData, key)
        else:
            if hasattr(key, 'pos'):
                raise ParseError("Invalid column name `%s` at position %d" % (key, key.pos))
            else:
                raise ParseError("Invalid column name `%s`" % (key))

class LibraryException(Exception):
    pass

class Library(object):
    """docstring for Library"""

    def __init__(self, user_id, domain_id):
        super(Library, self).__init__()
        self.user_id = user_id
        self.domain_id = domain_id
        self.grammar = SongSearchGrammar()

    def query(self):
        return db.session.query(SongData, SongUserData).join(SongUserData)

    def insert(self, song):

        if Song.artist not in song:
            raise LibraryException("artist key missing from song")

        if Song.album not in song:
            raise LibraryException("album key missing from song")

        if Song.title not in song:
            raise LibraryException("title key missing from song")

        if Song.artist_key not in song:
            song[Song.artist_key] = Song.getArtistKey(song[Song.artist])

        song_keys = set(SongData.column_names())
        song_data = {k: song[k] for k in song.keys() if k in song_keys}
        song_data['domain_id'] = self.domain_id

        user_keys = set(SongUserData.column_names())
        user_data = {k: song[k] for k in song.keys() if k in user_keys}

        new_song = SongData(**song_data)
        db.session.add(new_song)

        try:
            db.session.commit()
        except IntegrityError:
            raise LibraryException(str(e))

        db.session.refresh(new_song)

        if user_data:
            user_data["user_id"] = self.user_id
            user_data["song_id"] = new_song.id
            new_data = SongUserData(**user_data)

            db.session.add(new_data)

            try:
                db.session.commit()
            except IntegrityError:
                raise LibraryException(str(e))

        return new_song.id

    def update(self, song_id, song):

        song_keys = set(SongData.column_names())
        song_data = {k: song[k] for k in song.keys() if k in song_keys}

        user_keys = set(SongUserData.column_names())
        user_data = {k: song[k] for k in song.keys() if k in user_keys}

        if song_data:
            new_song = SongData \
                        .query \
                        .filter_by(id=song_id) \
                        .first()
            for k, v in song_data.items():
                setattr(new_song, k, v)

        if user_data:
            new_user = SongUserData \
                        .query \
                        .filter_by(song_id=song_id,
                                   user_id=self.user_id) \
                        .first()
            if new_user:
                for k, v in user_data.items():
                    setattr(new_user, k, v)

        try:
            db.session.commit()
        except IntegrityError:
            raise LibraryException(str(e))

    def findSongById(self, song_id):

        columns = Song.all_columns()
        defaults = Song.all_defaults()

        results = db.session.execute(
           select([column(c) for c in columns])
           .select_from(
               SongData.__table__.join(SongUserData.__table__,
                           and_(SongData.id == SongUserData.song_id,
                                SongUserData.user_id == self.user_id),
                           isouter=True))
           .where(and_(SongData.domain_id == self.domain_id,
                       SongData.id == song_id))
        ).fetchall()

        if not results:
            raise LibraryException("No song found with id=%s" % song_id)

        return {k: (v or d) for k, v, d in zip(columns, results[0], defaults)}

    def insertOrUpdateByReferenceId(self, ref_id, song):

        result = db.session \
                    .query(SongData) \
                    .filter(SongData.ref_id == ref_id) \
                    .first()

        if result:
            self.update(result.id, song)
            return result.id
        else:
            return self.insert(song)

    def _search_get_order(self, case_insensitive, orderby):

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

    def search(self, searchTerm, case_insensitive=True, orderby=None, limit=None, offset=None):

        rule = self.grammar.ruleFromString(searchTerm)

        sql_rule = rule.sql()

        # limit search results to a specific domain
        if sql_rule is not None:
            sql_rule = and_(SongData.domain_id == self.domain_id,
                            sql_rule)
        else:
            sql_rule = SongData.domain_id == self.domain_id

        columns = Song.all_columns()
        defaults = Song.all_defaults()

        query = select([column(c) for c in columns]) \
            .select_from(
                    SongData.__table__.join(
                        SongUserData.__table__,
                        and_(SongData.id == SongUserData.song_id,
                             SongUserData.user_id == self.user_id),
                        isouter=True)) \
            .where(sql_rule)

        if orderby is not None:
            order = self._search_get_order(case_insensitive, orderby)
            query = query.order_by(*order)

        if limit is not None:
            query = query.limit(limit)

        if offset is not None:
            query = query.offset(offset)

        results = db.session.execute(query).fetchall()

        if not results:
            raise LibraryException("No song found with id=%s" % song_id)

        return [{k: (v or d) for k, v, d in zip(columns, res, defaults)} for res in results]
