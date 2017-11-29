
from sqlalchemy import and_, or_, not_, select, column, update, insert

from .library import Song

class SongQueue(object):
    """docstring for Queue"""

    def __init__(self, db, dbtables, user_id, domain_id):
        super(SongQueue, self).__init__()
        self.user_id = user_id
        self.domain_id = domain_id
        self.db = db
        self.dbtables = dbtables

        self.cols_song = self._SongDataColumnNames()
        self.cols_user = self._SongUserDataColumnNames()

        self.defs_song = [self._SongDefault(col) for col in self.cols_song]
        self.defs_user = [self._UserDefault(col) for col in self.cols_user]

        self.cols = self.cols_song + self.cols_user
        self.defs = self.defs_song + self.defs_user

    def set(self, songs):

        SongQueueTable = self.db.tables.SongQueueTable

        # create the queue if it does not exist
        query = SongQueueTable.select() \
            .where(SongQueueTable.c.user_id == self.user_id)
        lst = self.db.session.execute(query).fetchall()

        if not lst:
            query = insert(SongQueueTable) \
                .values({"user_id": self.user_id, "songs": songs, })
        else:
            query = update(SongQueueTable) \
                .values({"songs": songs, }) \
                .where(SongQueueTable.c.user_id == self.user_id)

        self.db.session.execute(query)

    def get(self):

        SongQueueTable = self.db.tables.SongQueueTable

        query = SongQueueTable.select() \
            .where(SongQueueTable.c.user_id == self.user_id)
        result = self.db.session.execute(query).fetchone()

        if not result:
            return None

        id, lst = result

        if not lst:
            return None

        SongData = self.dbtables.SongDataTable
        SongUserData = self.dbtables.SongUserDataTable

        query = select([column(c) for c in self.cols]) \
            .select_from(
                    SongData.join(
                        SongUserData,
                        and_(SongData.c.id == SongUserData.c.song_id,
                             SongUserData.c.user_id == self.user_id),
                        isouter=True)) \
            .where(and_(SongData.c.domain_id == self.domain_id,
                        SongData.c.id.in_(lst)))

        results = self.db.session.execute(query).fetchall()

        songs = [{k: (v or d) for k, v, d in zip(self.cols, res, self.defs)} for res in results]

        map = {k: i for i, k in enumerate(lst)}
        songs.sort(key=lambda s: map[s['id']])
        return songs

    def head(self):

        SongQueueTable = self.db.tables.SongQueueTable

        query = SongQueueTable.select() \
            .where(SongQueueTable.c.user_id == self.user_id)
        result = self.db.session.execute(query).fetchone()

        if not result:
            return None

        id, lst = result

        if not lst:
            return None

        SongData = self.dbtables.SongDataTable
        SongUserData = self.dbtables.SongUserDataTable

        query = select([column(c) for c in self.cols]) \
            .select_from(
                    SongData.join(
                        SongUserData,
                        and_(SongData.c.id == SongUserData.c.song_id,
                             SongUserData.c.user_id == self.user_id),
                        isouter=True)) \
            .where(and_(SongData.c.domain_id == self.domain_id,
                        SongData.c.id == lst[0]))

        res = self.db.session.execute(query).fetchone()
        return {k: (v or d) for k, v, d in zip(self.cols, res, self.defs)}

    def rest(self):

        SongQueueTable = self.db.tables.SongQueueTable

        # session.query(SongData).filter(SongData.id.in_(seq)).all()
        query = SongQueueTable.select() \
            .where(SongQueueTable.c.user_id == self.user_id)
        result = self.db.session.execute(query).fetchone()

        if not result:
            return None

        id, lst = result

        lst = lst[1:]

        if not lst:
            return None

        SongData = self.dbtables.SongDataTable
        SongUserData = self.dbtables.SongUserDataTable

        query = select([column(c) for c in self.cols]) \
            .select_from(
                    SongData.join(
                        SongUserData,
                        and_(SongData.c.id == SongUserData.c.song_id,
                             SongUserData.c.user_id == self.user_id),
                        isouter=True)) \
            .where(and_(SongData.c.domain_id == self.domain_id,
                        SongData.c.id.in_(lst)))

        results = self.db.session.execute(query).fetchall()

        songs = [{k: (v or d) for k, v, d in zip(self.cols, res, self.defs)} for res in results]

        map = {k: i for i, k in enumerate(lst)}
        songs.sort(key=lambda s: map[s['id']])
        return songs

    def next(self):
        pass

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

