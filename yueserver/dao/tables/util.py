
"""
Helper functions for defining database tables
"""
import os, sys
import json
from sqlalchemy import Table
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.types import Integer, String, TypeDecorator
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.sql.expression import Executable, ClauseElement

from sqlalchemy.dialects.sqlite.pysqlite import SQLiteDialect_pysqlite
from sqlalchemy.dialects.postgresql import JSONB

import uuid

import datetime, time

def generate_uuid():
    return str(uuid.uuid4())

class StringArrayType(TypeDecorator):
    """
    String Array for SQite and PostreSQL
        http://docs.sqlalchemy.org/en/latest/core/custom_types.html#sqlalchemy.types.TypeDecorator
    """

    impl = String

    # found sql bug related to this function
    # def load_dialect_impl(self, dialect):
    #    # dialect.name -> 'sqlite'
    #    # dialect.dialect_description -> 'sqlite+pysqlite'
    #    # dialect.encoding -> 'utf-8'
    #    # dialect.driver -> 'pysqlite'
    #    # if dialect.name == "sqlite":
    #    if dialect.name == 'postgresql':
    #        return ARRAY(String)
    #    else:
    #        return String

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value

    def copy(self):
        return StringArrayType(self.impl.length)

class JsonType(TypeDecorator):
    """
    String Array for SQite and PostreSQL
        http://docs.sqlalchemy.org/en/latest/core/custom_types.html#sqlalchemy.types.TypeDecorator
    """

    impl = String

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(JSONB())
        else:
            return dialect.type_descriptor(String())

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value

    def copy(self):
        return JsonType(self.impl.length)

class CreateView(Executable, ClauseElement):
    def __init__(self, name, select):
        self.name = name
        self.select = select

@compiles(CreateView)
def visit_create_view(element, compiler, **kw):
    text = "CREATE VIEW IF NOT EXISTS %s AS %s" % (
         element.name,
         compiler.process(element.select, literal_binds=True)
    )
    return text

