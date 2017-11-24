import os, sys

from flask import Flask, render_template, jsonify, url_for

from .index import db, app, cors

from .models.user import User
from .models.test_message import TestMessage

from .endpoints import user
from .endpoints import test

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

    username = "admin"
    password = "admin"
    domain = app.config['DEFAULT_DOMAIN']
    role = "admin"

    user = User(username, password, domain, role)
    sys.stdout.write("Creating User: %s@%s/%s\n" % (username, domain, role))
    db.session.add(user)

    if app.config['DEFAULT_DOMAIN'] == "test":
        for i in range(10):
            username = "user%03d" % i
            password = username
            domain = "test"
            role = app.config['DEFAULT_ROLE']

            user = User(username, password, domain, role)
            sys.stdout.write("Creating User: %s@%s/%s\n" %
                (username, domain, role))
            db.session.add(user)

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

