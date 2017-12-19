
from sqlalchemy import and_, or_, not_, select, column, update, insert

from .library import Song, SongQueryFormatter

class SongQueueDao(object):
    """docstring for Queue"""

    def __init__(self, db, dbtables, sanitize=False):
        super(SongQueueDao, self).__init__()
        self.db = db
        self.dbtables = dbtables

        self.formatter = SongQueryFormatter(dbtables, sanitize)

    def set(self, user_id, domain_id, song_ids):

        SongQueueTable = self.dbtables.SongQueueTable

        # create the queue if it does not exist
        query = SongQueueTable.select() \
            .where(SongQueueTable.c.user_id == user_id)
        lst = self.db.session.execute(query).fetchall()

        if not lst:
            query = insert(SongQueueTable) \
                .values({"user_id": user_id, "songs": song_ids, })
        else:
            query = update(SongQueueTable) \
                .values({"songs": song_ids, }) \
                .where(SongQueueTable.c.user_id == user_id)

        self.db.session.execute(query)
        self.db.session.commit()

    def get(self, user_id, domain_id):

        SongQueueTable = self.dbtables.SongQueueTable

        query = SongQueueTable.select() \
            .where(SongQueueTable.c.user_id == user_id)
        result = self.db.session.execute(query).fetchone()

        if not result:
            return []

        id, lst, _ = result

        if not lst:
            return []

        SongData = self.dbtables.SongDataTable
        SongUserData = self.dbtables.SongUserDataTable

        query = select([column(c) for c in self.formatter.cols]) \
            .select_from(
                    SongData.join(
                        SongUserData,
                        and_(SongData.c.id == SongUserData.c.song_id,
                             SongUserData.c.user_id == user_id),
                        isouter=True)) \
            .where(and_(SongData.c.domain_id == domain_id,
                        SongData.c.id.in_(lst)))

        results = self.db.session.execute(query).fetchall()

        # todo: anywhere that defs are used to populate the songs,
        # if the uer does not have a record available, the user_id must be
        # updated.

        # todo: in addition, sanitize the output, remove:
        #  - song_id : redundant information
        #  - file_path
        #  - art_path

        # todo: the above changes have been made for this function
        # tests need to be written and changes need to propogate
        # into a common library

        songs = self.formatter.format(user_id, results)

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

        id, lst, _ = result

        if not lst:
            return None

        SongData = self.dbtables.SongDataTable
        SongUserData = self.dbtables.SongUserDataTable

        query = select([column(c) for c in self.formatter.cols]) \
            .select_from(
                    SongData.join(
                        SongUserData,
                        and_(SongData.c.id == SongUserData.c.song_id,
                             SongUserData.c.user_id == user_id),
                        isouter=True)) \
            .where(and_(SongData.c.domain_id == domain_id,
                        SongData.c.id == lst[0]))

        res = self.db.session.execute(query).fetchone()
        return self.formatter.format(user_id, [res, ])[0]

    def rest(self, user_id, domain_id):

        SongQueueTable = self.dbtables.SongQueueTable

        # session.query(SongData).filter(SongData.id.in_(seq)).all()
        query = SongQueueTable.select() \
            .where(SongQueueTable.c.user_id == user_id)
        result = self.db.session.execute(query).fetchone()

        if not result:
            return None

        id, lst, _ = result

        lst = lst[1:]

        if not lst:
            return None

        SongData = self.dbtables.SongDataTable
        SongUserData = self.dbtables.SongUserDataTable

        query = select([column(c) for c in self.formatter.cols]) \
            .select_from(
                    SongData.join(
                        SongUserData,
                        and_(SongData.c.id == SongUserData.c.song_id,
                             SongUserData.c.user_id == user_id),
                        isouter=True)) \
            .where(and_(SongData.c.domain_id == domain_id,
                        SongData.c.id.in_(lst)))

        results = self.db.session.execute(query).fetchall()

        songs = self.formatter.format(user_id, results)

        map = {k: i for i, k in enumerate(lst)}
        songs.sort(key=lambda s: map[s['id']])
        return songs

    def next(self):
        pass

    def getDefaultQuery(self, user_id):
        SongQueueTable = self.dbtables.SongQueueTable
        query = SongQueueTable.select() \
            .where(SongQueueTable.c.user_id == user_id)
        result = self.db.session.execute(query).fetchone()
        return result['query']




