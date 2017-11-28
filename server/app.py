import os, sys

from flask import Flask, render_template, jsonify, url_for

from .index import db, app, cors

from .models.song import SongData, SongUserData
from .models.tables import DatabaseTables

from .dao.user import UserDao
from .dao.queue import SongQueue
from .dao.library import Song, SongSearchGrammar, Library

from .endpoints import user
from .endpoints import message
from .endpoints import library
from .endpoints import queue

db.tables = DatabaseTables(db.metadata)

# serve the bundle
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/<path:path>', methods=['GET'])
def any_root_path(path):
    return render_template('index.html')

def list_routes():
    """List application endpoints"""

    output = []
    for rule in app.url_map.iter_rules():

        options = {}
        for arg in rule.arguments:
            options[arg] = "[{0}]".format(arg)

        methods = ','.join(rule.methods)
        url = url_for(rule.endpoint, **options)
        url = url.replace("%5B", ":").replace("%5D", "")
        output.append([rule.endpoint, methods, url])

    for endpoint, methods, url in sorted(output, key=lambda x: x[2]):
        line = "{:30s} {:20s} {}".format(endpoint, methods, url)

        print(line)

def db_init(*args):
    """initialize the database"""
    sys.stdout.write("Creating Database...\n")
    db.create_all()

    userDao = UserDao(db)

    default_domain = userDao.createDomain({'name': app.config['DEFAULT_DOMAIN']})
    sys.stdout.write("Creating Domain: %s\n" % app.config['DEFAULT_DOMAIN'])

    admin_role = userDao.createRole({'name': 'admin'})
    sys.stdout.write("Creating Role: admin\n")

    user_role = userDao.createRole({'name': app.config['DEFAULT_ROLE']})
    sys.stdout.write("Creating Role: %s\n" % app.config['DEFAULT_ROLE'])

    username = "admin"
    password = "admin"
    domain = app.config['DEFAULT_DOMAIN']
    role = "admin"

    userDao.createUser(username, password, default_domain, admin_role)
    sys.stdout.write("Creating User: %s@%s/%s\n" % (username, domain, role))

    if app.config['DEFAULT_DOMAIN'] == "test":
        for i in range(3):
            username = "user%03d" % i
            password = username
            domain = "test"
            role = app.config['DEFAULT_ROLE']

            userDao.createUser(username, password, default_domain, user_role)
            sys.stdout.write("Creating User: %s@%s/%s\n" %
                (username, domain, role))

    db.session.commit()

def db_drop():
    """ drop all tables from database """
    if input("drop tables? [yN] ")[:1] == "y":
        db.drop_all()
        db.session.commit()
        sys.stderr.write("successfully dropped all tables")
    else:
        sys.stderr.write("user aborted.")

def db_reset():
    """ drop all tables then create default database """
    db.drop_all()
    db_init()

