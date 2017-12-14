
from sqlalchemy import and_, or_, not_, select, column, update, insert

from .library import Song, SongQueryFormatter

class HistoryDao(object):
    """docstring for HistoryDao"""
    def __init__(self, db, dbtables, sanitize=False):
        super(HistoryDao, self).__init__()
        self.db = db
        self.dbtables = dbtables

        self.formatter = SongQueryFormatter(dbtables, sanitize)

    def insert(self, user_id, song_id, timestamp, commit=True):
        SongHistoryTable = self.dbtables.SongHistoryTable

        query = insert(SongHistoryTable) \
                .values({"user_id": user_id,
                         "song_id": song_id,
                         "timestamp": timestamp})

        self.db.session.execute(query)

        if commit:
            self.db.session.commit()

    def retrieve(self, user_id, start, end=None):
        """
        retrieve all history records between the given start and end time

        to retreive all records in the last day:
          start = (datetime.datetime.now() - timedelta(days=1)).timestamp()
          end   = datetime.datetime.now().timestamp()

        """

        SongHistoryTable = self.dbtables.SongHistoryTable

        terms = [SongHistoryTable.c.user_id == user_id,
                 SongHistoryTable.c.timestamp > start, ]

        if end is not None:
            terms.append(SongHistoryTable.c.timestamp < end)

        query = SongHistoryTable.select() \
            .where(and_(*terms))
        lst = self.db.session.execute(query).fetchall()

        records = [{"song_id": r['song_id'],
                   "timestamp": r['timestamp']} for r in lst]

        return records
