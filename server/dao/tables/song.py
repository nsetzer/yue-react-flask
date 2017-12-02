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
    """
    return Table('song_data', metadata,
        Column('id', String, primary_key=True, default=generate_uuid),
        Column('domain_id', Integer, ForeignKey("user_domain.id")),
        Column('ref_id', Integer, default=None),
        # text
        Column('file_path', String, default=""),
        Column('art_path', String, default=""),
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
        Column('year', Integer, default=0)
    )

def SongUserDataTable(metadata):
    return Table('song_user_data', metadata,
        # index
        Column('song_id', String, ForeignKey("song_data.id")),
        Column('user_id', Integer, ForeignKey("user.id")),
        # text
        Column('comment', String, default=""),
        # number
        Column('rating', Integer, default=0),
        Column('play_count', Integer, default=0),
        Column('skip_count', Integer, default=0),
        Column('blocked', Integer, default=0),
        Column('frequency', Integer, default=0),
        # date
        Column('last_played', Integer, default=0),
        Column('date_added', Integer, default=time.time)
    )

def SongHistoryTable(metadata):
    return Table('song_history', metadata,
        Column('user_id', Integer),
        Column('song_id', String, ForeignKey("song_data.id")),
        Column('date', Integer),
    )

def SongQueueTable(metadata):
    return Table('song_queue', metadata,
        Column('user_id', Integer, ForeignKey('user.id'), unique=True),
        Column('songs', StringArrayType),
    )

def SongPlaylistTable(metadata):
    return Table('song_playlist', metadata,
        Column('user_id', Integer, ForeignKey('user.id')),
        Column('name', String),
        Column('songs', StringArrayType),
    )


