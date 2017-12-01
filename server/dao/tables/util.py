import os, sys
import json
from sqlalchemy.types import Integer, String, TypeDecorator
from sqlalchemy.dialects.postgresql import ARRAY

from sqlalchemy.dialects.sqlite.pysqlite import SQLiteDialect_pysqlite

import uuid

import datetime, time

def generate_uuid():
    return str(uuid.uuid4())

def generate_null_timestamp():
    return datetime.datetime.utcfromtimestamp(0)

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
