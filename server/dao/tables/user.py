
"""
tables for Role Based User Management
"""
from sqlalchemy.schema import Table, Column, ForeignKey
from sqlalchemy.types import Integer, String

def DomainTable(metadata):
    """
    returns a table for domains enabled in the environment

    Each user has a default and active domain. the active domain
    controls what data they are able to see.
    """
    return Table('domain', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String),
    )

def GrandtedDomainTable(metadata):
    """
    returns a table which maps users to domains they can access
    """
    return Table('granted_domain', metadata,
        Column('user_id', ForeignKey("user.id")),
        Column('domain_id', ForeignKey("domain.id")),
    )

def GrandtedRoleTable(metadata):
    """
    returns a table which maps users to roles they can access
    """
    return Table('granted_role', metadata,
        Column('user_id', ForeignKey("user.id")),
        Column('role_id', ForeignKey("role.id")),
    )

def RoleTable(metadata):
    """
    returns a table for domains enabled in the environment

    Each user has a default and active role. the active role
    controls what features are enabled for the user
    """
    return Table('role', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String),
    )

def FeatureTable(metadata):
    """
    returns a table describing features in this environment
    """
    return Table('feature', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String),
    )

def RoleFeatureTable(metadata):
    """
    returns a table which indicates what features are enabled for a role
    """
    return Table('role_permission', metadata,
        Column('feature_id', ForeignKey("feature.id")),
        Column('role_id', ForeignKey("role.id")),
    )

def UserTable(metadata):
    """
    returns a table describing basic information of a user
    """
    return Table('user', metadata,
        Column('id', Integer, primary_key=True),
        Column('email', String),
        Column('password', String),
        Column('domain_id', Integer, ForeignKey("domain.id")),
        Column('role_id', Integer, ForeignKey("role.id"))
    )


