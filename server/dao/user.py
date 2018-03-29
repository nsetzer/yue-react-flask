from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, not_, select, column, update, insert, delete

from .util import hash_password, check_password_hash

class UserDao(object):
    """docstring for UserDao"""

    def __init__(self, db, dbtables):
        super(UserDao, self).__init__()
        self.db = db
        self.dbtables = dbtables

        self.workfactor = 12

    def createDomain(self, domainName, commit=True):
        query = insert(self.dbtables.DomainTable) \
            .values({'name': domainName})
        result = self.db.session.execute(query)
        if commit:
            self.db.session.commit()
        return result.inserted_primary_key[0]

    def findDomainById(self, did):
        query = self.dbtables.DomainTable.select() \
            .where(self.dbtables.DomainTable.c.id == did)
        result = self.db.session.execute(query)
        return result.fetchone()

    def findDomainByName(self, name):
        query = self.dbtables.DomainTable.select() \
            .where(self.dbtables.DomainTable.c.name == name)
        result = self.db.session.execute(query)
        return result.fetchone()

    def listDomains(self):
        query = self.dbtables.DomainTable.select()
        result = self.db.session.execute(query)
        return result.fetchall()

    def removeDomain(self, domain_id, commit=True):
        # TODO ensure domain is not used for any user

        query = delete(self.dbtables.DomainTable) \
            .where(self.dbtables.DomainTable.c.id == domain_id)

        self.db.session.execute(query)

        if commit:
            self.db.session.commit()

    def createRole(self, roleName, commit=True):
        query = insert(self.dbtables.RoleTable) \
            .values({'name': roleName})
        result = self.db.session.execute(query)
        if commit:
            self.db.session.commit()
        return result.inserted_primary_key[0]

    def findRoleById(self, rid):
        query = self.dbtables.RoleTable.select() \
            .where(self.dbtables.RoleTable.c.id == rid)
        result = self.db.session.execute(query)
        return result.fetchone()

    def findRoleByName(self, name):
        query = self.dbtables.RoleTable.select() \
            .where(self.dbtables.RoleTable.c.name == name)
        result = self.db.session.execute(query)
        return result.fetchone()

    def listRoles(self):
        query = self.dbtables.RoleTable.select()
        result = self.db.session.execute(query)
        return result.fetchall()

    def removeRole(self, role_id, commit=True):
        # TODO ensure role is not used for any user

        query = delete(self.dbtables.RoleTable) \
            .where(self.dbtables.RoleTable.c.id == role_id)
        self.db.session.execute(query)

        if commit:
            self.db.session.commit()

    def createFeature(self, featName, commit=True):
        query = insert(self.dbtables.FeatureTable) \
            .values({"feature": featName})
        result = self.db.session.execute(query)
        if commit:
            self.db.session.commit()
        return result.inserted_primary_key[0]

    def dropFeature(self, feature_id, commit=True):
        """
        remove a feature from the database
        revoke the feature from any roles it has been granted to.
        """
        query = delete(self.dbtables.RoleFeatureTable) \
            .where(self.dbtables.RoleFeatureTable.c.feature_id == feature_id)
        self.db.session.execute(query)

        query = delete(self.dbtables.FeatureTable) \
            .where(self.dbtables.FeatureTable.c.id == feature_id)
        self.db.session.execute(query)

        if commit:
            self.db.session.commit()

    def findFeatureByName(self, name):
        query = self.dbtables.FeatureTable.select() \
            .where(self.dbtables.FeatureTable.c.feature == name)
        result = self.db.session.execute(query)
        return result.fetchone()

    def listAllFeatures(self):
        query = self.dbtables.FeatureTable.select()
        result = self.db.session.execute(query)
        return result.fetchall()

    def removeFeature(self, feat_id, commit=True):
        # TODO ensure feature is not used for any role

        query = delete(self.dbtables.FeatureTable) \
            .where(self.dbtables.FeatureTable.c.id == feat_id)

        self.db.session.execute(query)

        if commit:
            self.db.session.commit()

    def createUser(self, email, password, domain_id, role_id, commit=True):

        hashed = hash_password(password, self.workfactor)

        user_ = {
            "email": email,
            "password": hashed,
            "domain_id": domain_id,
            "role_id": role_id,
        }

        query = insert(self.dbtables.UserTable).values(user_)

        result = self.db.session.execute(query)

        user_id = result.inserted_primary_key[0]

        self.grantDomain(user_id, domain_id, commit=False)
        self.grantRole(user_id, role_id, commit=False)

        if commit:
            self.db.session.commit()

        return user_id

    def findUserById(self, userId):
        query = self.dbtables.UserTable.select() \
            .where(self.dbtables.UserTable.c.id == userId)
        result = self.db.session.execute(query)
        return result.fetchone()

    def findUserByEmail(self, email):
        query = self.dbtables.UserTable.select() \
            .where(self.dbtables.UserTable.c.email == email)
        result = self.db.session.execute(query)
        return result.fetchone()

    def findUserByEmailAndPassword(self, email, password):
        query = self.dbtables.UserTable.select() \
            .where(self.dbtables.UserTable.c.email == email)
        user = self.db.session.execute(query).fetchone()

        if user:
            hash = user[self.dbtables.UserTable.c.password]
            print(email, password, user)
            if check_password_hash(hash, password):
                return user

        return None

    def findUserByApiKey(self, apikey):
        query = self.dbtables.UserTable.select() \
            .where(self.dbtables.UserTable.c.apikey == apikey)
        result = self.db.session.execute(query)
        return result.fetchone()

    def changeUserPassword(self, user_id, password, commit=True):

        hash = hash_password(password, self.workfactor)
        data = {"password": hash}
        query = update(self.dbtables.UserTable) \
            .values(data) \
            .where(self.dbtables.UserTable.c.id == user_id)
        self.db.session.execute(query)

        if commit:
            self.db.session.commit()

    def listUsers(self, domain_id):

        userTable = self.dbtables.UserTable
        grantedDomainTable = self.dbtables.GrantedDomainTable
        columns = [userTable.c.id,
                   userTable.c.email,
                   userTable.c.domain_id,
                   userTable.c.role_id]

        query = select(columns) \
            .select_from(
                userTable.join(
                    grantedDomainTable,
                    and_(grantedDomainTable.c.user_id == userTable.c.id),
                    isouter=True)) \
            .where(grantedDomainTable.c.domain_id == domain_id)
        result = self.db.session.execute(query)

        return [{
            'id':u['id'],
            'email':u['email'],
            'default_domain':u['domain_id'],
            'default_role':u['role_id'],
        } for u in result]

    def getUserApiKey(self, user_id):
        query = self.dbtables.UserTable.select() \
            .where(self.dbtables.UserTable.c.id == user_id)
        result = self.db.session.execute(query)
        return result.fetchone()['apikey']

    def updateUser(self, user, commit=True):

        if 'password' in user:
            hash = hash_password(password, self.workfactor)
            user['password'] = hash

        query = update(self.dbtables.UserTable) \
            .values(user) \
            .where(SongQueueTable.c.user_id == self.user_id)

        self.db.session.execute(query)
        if commit:
            self.db.session.commit()

    def removeUser(self, user_id, commit=True):

        # remove user roles
        query = delete(self.dbtables.GrantedRoleTable) \
            .where(self.dbtables.GrantedRoleTable.c.user_id == user_id)
        self.db.session.execute(query)

        # remove user domains
        query = delete(self.dbtables.GrantedDomainTable) \
            .where(self.dbtables.GrantedDomainTable.c.user_id == user_id)
        self.db.session.execute(query)

        # remove user
        query = delete(self.dbtables.UserTable) \
            .where(self.dbtables.UserTable.c.id == user_id)
        self.db.session.execute(query)

        if commit:
            self.db.session.commit()

    def grantDomain(self, user_id, domain_id, commit=True):

        query = insert(self.dbtables.GrantedDomainTable) \
            .values({"user_id": user_id, "domain_id": domain_id})

        result = self.db.session.execute(query)

        if commit:
            self.db.session.commit()

    def revokeDomain(self, user_id, domain_id, commit=True):

        query = delete(self.dbtables.GrantedDomainTable) \
            .where(
                and_(self.dbtables.GrantedDomainTable.c.user_id == user_id,
                     self.dbtables.GrantedDomainTable.c.domain_id == domain_id,
                    ))

        self.db.session.execute(query)

        if commit:
            self.db.session.commit()

    def grantRole(self, user_id, role_id, commit=True):

        query = insert(self.dbtables.GrantedRoleTable) \
            .values({"user_id": user_id, "role_id": role_id})

        result = self.db.session.execute(query)

        if commit:
            self.db.session.commit()

    def revokeRole(self, user_id, role_id, commit=True):

        query = delete(self.dbtables.GrantedRoleTable) \
            .where(
                and_(self.dbtables.GrantedRoleTable.c.user_id == user_id,
                     self.dbtables.GrantedRoleTable.c.role_id == role_id,
                    ))

        self.db.session.execute(query)

        if commit:
            self.db.session.commit()

    def addFeatureToRole(self, role_id, feature_id, commit=True):
        query = insert(self.dbtables.RoleFeatureTable) \
            .values({"role_id": role_id, "feature_id": feature_id})

        result = self.db.session.execute(query)

        if commit:
            self.db.session.commit()

    def removeFeatureFromRole(self, role_id, feature_id, commit=True):
        query = delete(self.dbtables.RoleFeatureTable) \
            .where(
                and_(self.dbtables.RoleFeatureTable.c.role_id == role_id,
                     self.dbtables.RoleFeatureTable.c.feature_id == feature_id,
                    ))

        self.db.session.execute(query)

        if commit:
            self.db.session.commit()

    def userHasRole(self, user_id, role_id):
        query = self.dbtables.GrantedRoleTable.select() \
            .where(
                and_(self.dbtables.GrantedRoleTable.c.user_id == user_id,
                     self.dbtables.GrantedRoleTable.c.role_id == role_id,
                    ))
        result = self.db.session.execute(query)
        return len(result.fetchall()) != 0

    def roleHasFeature(self, role_id, feature_id):
        query = self.dbtables.RoleFeatureTable.select() \
            .where(
                and_(self.dbtables.RoleFeatureTable.c.role_id == role_id,
                     self.dbtables.RoleFeatureTable.c.feature_id == feature_id,
                    ))
        result = self.db.session.execute(query)
        return len(result.fetchall()) != 0

    def roleHasNamedFeature(self, role_id, feature_name):

        FeatureTable = self.dbtables.FeatureTable
        RoleFeatureTable = self.dbtables.RoleFeatureTable

        query = select([column("feature"), ]) \
            .select_from(
                FeatureTable.join(
                    RoleFeatureTable,
                    and_(FeatureTable.c.id == RoleFeatureTable.c.feature_id),
                    isouter=True)) \
            .where(and_(RoleFeatureTable.c.role_id == role_id,
                        FeatureTable.c.feature == feature_name))
        result = self.db.session.execute(query)

        return len(result.fetchall()) != 0

    def listFeaturesByName(self, role_id):

        FeatureTable = self.dbtables.FeatureTable
        RoleFeatureTable = self.dbtables.RoleFeatureTable

        query = select([column("feature"), ]) \
            .select_from(
                FeatureTable.join(
                    RoleFeatureTable,
                    and_(FeatureTable.c.id == RoleFeatureTable.c.feature_id),
                    isouter=True)) \
            .where(and_(RoleFeatureTable.c.role_id == role_id))
        result = self.db.session.execute(query)
        return [r['feature'] for r in result.fetchall()]

