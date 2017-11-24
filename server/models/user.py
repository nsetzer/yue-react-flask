from ..index import db, bcrypt
from sqlalchemy.orm import relationship

class Domain(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(), unique=True)

    song_data = db.relationship("User")
    song_data = db.relationship("SongData")

    def __init__(self, name):
        super(Domain, self).__init__()

        self.name = name

    @staticmethod
    def findDomainByName(name):
        return db.session \
                .query(Domain) \
                .filter(Domain.name == name) \
                .first()

class Role(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(), unique=True)

    song_data = db.relationship("User")

    def __init__(self, name):
        super(Role, self).__init__()

        self.name = name

    @staticmethod
    def findRoleByName(name):
        return db.session \
                .query(Role) \
                .filter(Role.name == name) \
                .first()

class User(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    email = db.Column(db.String(), unique=True)
    password = db.Column(db.String())
    domain_id = db.Column(db.Integer(), db.ForeignKey("domain.id"))
    role_id = db.Column(db.Integer(), db.ForeignKey("role.id"))

    song_user_data = db.relationship("SongUserData")

    def __init__(self, email, password, domain_id, role_id):
        super(User, self).__init__()

        self.email = email
        self.domain_id = domain_id
        self.role_id = role_id
        self.password = User.hashed_password(password)
        self.active = True

    @staticmethod
    def hashed_password(password):
        # Note:
        # I had an error in python3 related to this function
        # AttributeError: 'module' object has no attribute 'ffi'
        # I uninstalled bcrypt py-bcrypt flask_bcrypt
        # then reinstalled flask_bcrypt using pip
        return bcrypt.generate_password_hash(password)

    @staticmethod
    def get_user_with_email(email):
        user = User.query.filter_by(email=email).first()
        if user:
            return user
        return None

    @staticmethod
    def get_user_with_email_and_password(email, password):
        user = User.query.filter_by(email=email).first()
        if user:
            if bcrypt.check_password_hash(user.password, password):
                return user
        return None

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        del data['password']
        return data


