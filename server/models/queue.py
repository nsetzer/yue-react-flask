
from sqlalchemy.orm import relationship
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, not_, select, column, update, insert

from sqlalchemy.schema import Table, Column, ForeignKey
from sqlalchemy.types import Integer, DateTime, String
from sqlalchemy import MetaData

from .song import Song, SongData, SongUserData
from .user import User

from .util import StringArrayType

from ..index import db

SongQueueTable = Table('song_queue', db.metadata,
    Column('user_id', Integer, ForeignKey('user.id'), unique=True),
    Column('songs', StringArrayType),
)

class SongQueue(object):
    """docstring for Queue"""

    def __init__(self, user_id, domain_id):
        super(SongQueue, self).__init__()
        self.user_id = user_id
        self.domain_id = domain_id

    def set(self, songs):

        # create the queue if it does not exist
        query = SongQueueTable.select() \
            .where(SongQueueTable.c.user_id == self.user_id)
        lst = db.session.execute(query).fetchall()

        if not lst:
            query = insert(SongQueueTable) \
                .values({"user_id": self.user_id, "songs": songs, })
        else:
            query = update(SongQueueTable) \
                .values({"songs": songs, }) \
                .where(SongQueueTable.c.user_id == self.user_id)

        db.session.execute(query)

    def get(self):

        query = SongQueueTable.select() \
            .where(SongQueueTable.c.user_id == self.user_id)
        result = db.session.execute(query).fetchone()

        if not result:
            return None

        id, lst = result

        if not lst:
            return None

        columns = Song.all_columns()
        defaults = Song.all_defaults()

        query = select([column(c) for c in columns]) \
            .select_from(
                    SongData.__table__.join(
                        SongUserData.__table__,
                        and_(SongData.id == SongUserData.song_id,
                             SongUserData.user_id == self.user_id),
                        isouter=True)) \
            .where(and_(SongData.domain_id == self.domain_id,
                        SongData.id.in_(lst)))

        results = db.session.execute(query).fetchall()

        songs = [{k: (v or d) for k, v, d in zip(columns, res, defaults)} for res in results]

        map = {k: i for i, k in enumerate(lst)}
        songs.sort(key=lambda s: map[s['id']])
        return songs

    def head(self):

        query = SongQueueTable.select() \
            .where(SongQueueTable.c.user_id == self.user_id)
        result = db.session.execute(query).fetchone()

        if not result:
            return None

        id, lst = result

        if not lst:
            return None

        columns = Song.all_columns()
        defaults = Song.all_defaults()

        query = select([column(c) for c in columns]) \
            .select_from(
                    SongData.__table__.join(
                        SongUserData.__table__,
                        and_(SongData.id == SongUserData.song_id,
                             SongUserData.user_id == self.user_id),
                        isouter=True)) \
            .where(and_(SongData.domain_id == self.domain_id,
                        SongData.id == lst[0]))

        res = db.session.execute(query).fetchone()
        return {k: (v or d) for k, v, d in zip(columns, res, defaults)}

    def rest(self):
        # session.query(SongData).filter(SongData.id.in_(seq)).all()
        query = SongQueueTable.select() \
            .where(SongQueueTable.c.user_id == self.user_id)
        result = db.session.execute(query).fetchone()

        if not result:
            return None

        id, lst = result

        lst = lst[1:]

        if not lst:
            return None

        columns = Song.all_columns()
        defaults = Song.all_defaults()

        query = select([column(c) for c in columns]) \
            .select_from(
                    SongData.__table__.join(
                        SongUserData.__table__,
                        and_(SongData.id == SongUserData.song_id,
                             SongUserData.user_id == self.user_id),
                        isouter=True)) \
            .where(and_(SongData.domain_id == self.domain_id,
                        SongData.id.in_(lst)))

        results = db.session.execute(query).fetchall()

        songs = [{k: (v or d) for k, v, d in zip(columns, res, defaults)} for res in results]

        map = {k: i for i, k in enumerate(lst)}
        songs.sort(key=lambda s: map[s['id']])
        return songs

    def next(self):
        pass





