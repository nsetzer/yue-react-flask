
"""
tables for Role Based User Management

User access is controlled by two basic features, the domain and role.
The domain controls what set of data a user can access, while the role
allows for fine tuning of CRUD operations to that data.

The domain and role tables are designed in a way so that features
can be added or removed per environment without requireing schema changes

"""
from sqlalchemy.schema import Table, Column, ForeignKey
from sqlalchemy.types import Integer, String
from .util import generate_uuid, JsonType

def DomainTable(metadata):
    """
    returns a table for domains enabled in the environment

    Each user has a default and active domain. the active domain
    controls what data they are able to see.
    """
    return Table('user_domain', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String, unique=True, nullable=False),
    )

def GrantedDomainTable(metadata):
    """
    returns a table which maps users to domains they can access
    """
    return Table('user_granted_domain', metadata,
        Column('user_id', ForeignKey("user.id"), nullable=False),
        Column('domain_id', ForeignKey("user_domain.id"), nullable=False),
    )

def RoleTable(metadata):
    """
    returns a table for domains enabled in the environment

    Each user has a default and active role. the active role
    controls what features are enabled for the user
    """
    return Table('user_role', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String, unique=True, nullable=False),
    )

def GrantedRoleTable(metadata):
    """
    returns a table which maps users to roles they can access
    """
    return Table('user_granted_role', metadata,
        Column('user_id', ForeignKey("user.id"), nullable=False),
        Column('role_id', ForeignKey("user_role.id"), nullable=False),
    )

def FeatureTable(metadata):
    """
    returns a table describing features in this environment
    """
    return Table('user_feature', metadata,
        Column('id', Integer, primary_key=True),
        Column('feature', String, unique=True, nullable=False),
    )

def RoleFeatureTable(metadata):
    """
    returns a table which indicates what features are enabled for a role
    """
    return Table('user_role_feature', metadata,
        Column('role_id', ForeignKey("user_role.id"), nullable=False),
        Column('feature_id', ForeignKey("user_feature.id"), nullable=False),
    )

def UserTable(metadata):
    """
    returns a table describing basic information of a user

    email:
    password: a bcrypt password hash
    apikey: serves as a username and password
            can be null to prevent api based authentication
    domain_id: id for the users default domain
    role_id: id for the users default role
    """
    return Table('user', metadata,
        Column('id', String, primary_key=True, default=generate_uuid),
        Column('email', String),
        Column('password', String),
        Column('apikey', String, default=generate_uuid,
               unique=True, nullable=True),
        Column('domain_id', ForeignKey("user_domain.id"),
               nullable=False),
        Column('role_id', ForeignKey("user_role.id"),
               nullable=False)
    )

def UserSessionTable(metadata):
    """
    returns a table describing basic information of a user

    email:
    user_id: foregin key for a user
    session_id: unique key for the users session
    """
    return Table('user_session', metadata,
        Column('user_id', ForeignKey("user.id"), nullable=False),
        Column('session_id', String, default=generate_uuid),
        Column('creation_time', Integer, default=lambda: int(time.time())),
    )

def UserPreferencesTable(metadata):
    """
    returns a table describing basic information of a user

    email:
    user_id: foregin key for a user
    session_id: unique key for the users session
    """
    return Table('user_preference', metadata,
        Column('user_id', ForeignKey("user.id"), nullable=False),
        Column('key', String, nullable=False),
        Column('json', JsonType, nullable=False),
    )

