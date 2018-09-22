
"""
The set of tables which represent a song and records pertaining to the user
"""
from sqlalchemy.schema import Table, Column, ForeignKey
from sqlalchemy.types import Integer, String

from .util import generate_uuid, StringArrayType
import time

# http://docs.sqlalchemy.org/en/latest/orm/tutorial.html

def SongDataTable(metadata):
    """
    Construct a table representing a song

    id: uuid4 song id
    domain_id: domain this song belongs to (for multi tenant environments)
    ref_id: reference id used for migration from legacy databases.
    file_path: file path or url to song resource
    art_path: file path or url to album artwork
    static_path: a relative path used for database migrations
    artist: the name of artist for this song
    artist_key: A naturally sortable artist name
    composer: the composer for this piece
    album: the title of the album for this song
    title: the title of this song
    genre: comma or semi-colon separated list of genres
    country: origin country for this piece
    language: primary language of the song (may be a comma or semi-colon list)
    album_index: index of the song in the album
    length: length of the song in seconds
    equalizer: measure of volume of the song
    year: year the track was released
    banished: song should not appear in queries for any user of this domain
    date_added: date song was added to the database
    """
    return Table('song_data', metadata,
        Column('id', String, primary_key=True, default=generate_uuid),
        Column('domain_id', ForeignKey("user_domain.id")),
        Column('ref_id', Integer, default=None),
        # text
        Column('file_path', String, default=""),
        Column('art_path', String, default=""),
        Column('static_path', String, default=""),
        Column('artist', String),
        Column('artist_key', String),
        Column('composer', String, default=""),
        Column('album', String),
        Column('title', String),
        Column('genre', String, default=""),
        Column('country', String, default=""),
        Column('language', String, default=""),
        # number
        Column('album_index', Integer, default=0),
        Column('length', Integer, default=0),
        Column('equalizer', Integer, default=0),
        Column('year', Integer, default=0),
        Column('banished', Integer, default=0),
        # date
        Column('date_added', Integer, default=lambda: int(time.time()))
    )

def SongUserDataTable(metadata):
    """
    Construct a table representing the user specific song data

    song_id: Foreign key referencing a song
    user_id: Foreign key referencing a user
    comment: a user specified comment. used for notes and to improve search
    rating: the users rating of the song
    play_count: the number of time the user has played this song
    skip_count: the number of time the user has skipped this song during playback
    blocked: the user does not want this song appearing in search results
    frequency: an average rate of playback, in days
    last_played: the date of the last time the user played the song
    """
    return Table('song_user_data', metadata,
        # index
        Column('song_id', ForeignKey("song_data.id")),
        Column('user_id', ForeignKey("user.id")),
        # text
        Column('comment', String, default=""),
        # number
        Column('rating', Integer, default=0),
        Column('play_count', Integer, default=0),
        Column('skip_count', Integer, default=0),
        Column('blocked', Integer, default=0),
        Column('frequency', Integer, default=0),
        # date
        Column('last_played', Integer, default=0)
    )

def SongHistoryTable(metadata):
    """
    returns a table representing playback date of songs by users

    when playback completes normally (the song is not skipped) an entry
    is added recording the song, user, and date of completion
    """
    return Table('song_history', metadata,
        Column('user_id', Integer),
        Column('song_id', ForeignKey("song_data.id")),
        Column('timestamp', Integer),
    )

def SongQueueTable(metadata):
    """
    returns a table representing a users song queue

    the queue is an ordered list of songs for playback. when
    empty it is automatically populated using a default query.
    """
    return Table('song_queue', metadata,
        Column('user_id', ForeignKey('user.id'), unique=True),
        Column('songs', StringArrayType),
        Column('query', String, default=""),
    )

def SongPlaylistTable(metadata):
    """
    A table containing user defined playlists
    """
    return Table('song_playlist', metadata,
        Column('user_id', ForeignKey('user.id')),
        Column('name', String),
        Column('songs', StringArrayType),
    )


