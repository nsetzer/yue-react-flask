
import os
import sys
import flask
from flask import url_for, request, g, jsonify
from ..cli.managedb import db_connect

"""
    Application Stack:
        Flask Application
            A collection of resources, the confgiuration
            database and web resources that make up a web app.
        Web Resource Layer
            REST Endpoints for Service logic
        Service Layer
            Application logic built on top of Dao objects
        Dao Layer
            object which have direct access to the database
        Database
            A database client to SQLite or PostgreSQL.
"""

class FlaskApp(object):
    """FlaskApp"""
    def __init__(self, config):
        super(FlaskApp, self).__init__()
        self.config = config

        self.app = flask.Flask(self.__class__.__name__,
            static_folder=self.config.static_dir,
            template_folder=self.config.build_dir)

        self.app.config['SECRET_KEY'] = self.config.secret_key

        self.db = db_connect(self.config.database.url)

        self.log = self.app.logger

        if not os.path.exists(self.config.build_dir):
            self.log.warn("not found: %s\n" % cfg.build_dir)

        if not os.path.exists(self.config.static_dir):
            self.log.warn("not found: %s\n" % cfg.static_dir)

    def add_resource(self, res):

        for path, methods, name, func in res.endpoints():
            self.register(path, name, func, methods=methods)

        # this does not work at all
        #for path, methods, name, func in res._class_endpoints:
        #    print(name, path, func.__name__)
        #    f=lambda *x,**y : func(* ([res, self,] + list(x)), **y)
        #    self.app.add_url_rule(path, name, f, methods=methods)

    def register(self, path, name, callback, **options):
        f=lambda *x,**y : callback(*x, **y)
        self.app.add_url_rule(path, name, f, **options)

    def list_routes(self):
        """return a list of (endpoint, method, url)
        """
        output = []
        with self.app.test_request_context():

            for rule in self.app.url_map.iter_rules():

                options = {}
                for arg in rule.arguments:
                    options[arg] = "[{0}]".format(arg)

                methods = ','.join(rule.methods)
                url = url_for(rule.endpoint, **options)
                url = url.replace("%5B", ":").replace("%5D", "")
                output.append([rule.endpoint, methods, url])

        output.sort(key=lambda x:(x[0],x[2]))
        #for endpoint, methods, url in sorted(output, key=lambda x: x[2]):
        #    print("{:30s} {:20s} {}".format(endpoint, methods, url))

        return output

    def test_client(self):
        return self.app.test_client()

    def run(self, ssl_context=None):

        self.app.run(host=self.config.host,
                     port=self.config.port,
                     ssl_context=ssl_context);



