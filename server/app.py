import os, sys

from flask import Flask, render_template, jsonify, url_for

from .index import db, dbtables, app, cors
from .service.audio_service import AudioService

AudioService.init(db, dbtables)

from .dao.user import UserDao

from .endpoints import user
from .endpoints import message
from .endpoints import library
from .endpoints import queue

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
    db.session.commit()

    userDao = UserDao(db, dbtables)

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


"""
userDao = UserDao(db, dbtables)
user = userDao.findUserByEmail("user000")
results = AudioService.instance().search(user, "beast", limit=5)
for song in results:
    print("/api/library/%s/audio" % song['id'])
curl -u user000:user000 \
  http://localhost:4200/api/library/7a3068e5-cdb0-46ec-b330-388e57340c7c/audio
  -o out.mp3
"""
