from ..index import db, bcrypt

class TestMessage(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    text = db.Column(db.String(), unique=False)

    def __init__(self, text):
        super(TestMessage, self).__init__();
        self.text = text

    @staticmethod
    def get_all_messages():
        result = TestMessage.query.all()
        if result:
            return result
        return []

    def as_dict(self):
       return {c.name: getattr(self, c.name) for c in self.__table__.columns}