
from sqlalchemy import and_, or_, not_, select, column, update, insert

from .library import Song

class SongQueueDao(object):
    """docstring for Queue"""

    def __init__(self, db, dbtables):
        super(SongQueueDao, self).__init__()
        self.db = db
        self.dbtables = dbtables

        self.cols_song = self._SongDataColumnNames()
        self.cols_user = self._SongUserDataColumnNames()

        self.defs_song = [self._SongDefault(col) for col in self.cols_song]
        self.defs_user = [self._UserDefault(col) for col in self.cols_user]

        self.cols = self.cols_song + self.cols_user
        self.defs = self.defs_song + self.defs_user

    def set(self, user_id, domain_id, songs):

        SongQueueTable = self.dbtables.SongQueueTable

        # create the queue if it does not exist
        query = SongQueueTable.select() \
            .where(SongQueueTable.c.user_id == user_id)
        lst = self.db.session.execute(query).fetchall()

        if not lst:
            query = insert(SongQueueTable) \
                .values({"user_id": user_id, "songs": songs, })
        else:
            query = update(SongQueueTable) \
                .values({"songs": songs, }) \
                .where(SongQueueTable.c.user_id == user_id)

        self.db.session.execute(query)
        self.db.session.commit()

    def get(self, user_id, domain_id):

        SongQueueTable = self.dbtables.SongQueueTable

        query = SongQueueTable.select() \
            .where(SongQueueTable.c.user_id == user_id)
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
                             SongUserData.c.user_id == user_id),
                        isouter=True)) \
            .where(and_(SongData.c.domain_id == domain_id,
                        SongData.c.id.in_(lst)))

        results = self.db.session.execute(query).fetchall()

        songs = [{k: (v or d) for k, v, d in zip(self.cols, res, self.defs)} for res in results]

        map = {k: i for i, k in enumerate(lst)}
        songs.sort(key=lambda s: map[s['id']])
        return songs

    def head(self, user_id, domain_id):

        SongQueueTable = self.dbtables.SongQueueTable

        query = SongQueueTable.select() \
            .where(SongQueueTable.c.user_id == user_id)
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
                             SongUserData.c.user_id == user_id),
                        isouter=True)) \
            .where(and_(SongData.c.domain_id == domain_id,
                        SongData.c.id == lst[0]))

        res = self.db.session.execute(query).fetchone()
        return {k: (v or d) for k, v, d in zip(self.cols, res, self.defs)}

    def rest(self, user_id, domain_id):

        SongQueueTable = self.dbtables.SongQueueTable

        # session.query(SongData).filter(SongData.id.in_(seq)).all()
        query = SongQueueTable.select() \
            .where(SongQueueTable.c.user_id == user_id)
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
                             SongUserData.c.user_id == user_id),
                        isouter=True)) \
            .where(and_(SongData.c.domain_id == domain_id,
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

