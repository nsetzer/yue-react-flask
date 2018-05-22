
import os
import sys
import flask
from flask import url_for, request, g, jsonify
import json
import gzip
import argparse

from .client import RegisteredEndpoint, Parameter, AuthenticatedRestClient, \
    FlaskAppClient, generate_argparse

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
            static_folder=None)
            #static_folder=self.config.static_dir,
            #template_folder=self.config.build_dir)

        # set the max upload file size limit to 100MB
        self.app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

        self.log = self.app.logger

        if not os.path.exists(self.config.build_dir):
            self.log.warn("not found: %s\n" % cfg.build_dir)

        if not os.path.exists(self.config.static_dir):
            self.log.warn("not found: %s\n" % cfg.static_dir)

        self.app.after_request(self._add_cors_headers)

        self._registered_endpoints = []

    def add_resource(self, res):

        for path, methods, name, func, params, body in res.endpoints():
            self.register(path, name, func,
                params=params, body=body, methods=methods)

    def register(self, path, name, callback, params=None, body=None, **options):
        msg = ""
        try:
            self.app.add_url_rule(path, name, callback, **options)

            body = body or (None, False)

            if body[0] is not None:
                body = (body[0].__name__, body[1])

            params = params or []
            new_params = []
            for param in params:
                data = param._asdict()
                data['type'] = param.type.__name__
                new_params.append(Parameter(**data))

            endpoint = RegisteredEndpoint(path, name, callback.__doc__,
                options['methods'], params, body)
            self._registered_endpoints.append(endpoint)

            return
        except AssertionError as e:
            msg = "%s" % e

        # likely case is double registering a resource,
        msg = "Error registering %s: %s"  % (name, msg)
        msg += " or endpoint already mapped"
        raise Exception(msg)

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

    def generate_argparse(self):
        return generate_argparse(self._registered_endpoints)

    def client(self, hostname, username, password, domain, role):
        client = AuthenticatedRestClient(hostname,
            username, password, domain, role)
        return FlaskAppClient(client, self._registered_endpoints)

    def test_client(self, token = None):
        return AppTestClientWrapper(self.app.test_client(), token)

    def run(self, ssl_context=None):

        routes = self.list_routes()
        for endpoint, methods, url in routes:
            sys.stdout.write("{:40s} {:20s} {}\n".format(endpoint, methods, url))
        sys.stdout.flush()

        self.app.run(host=self.config.host,
                     port=self.config.port,
                     ssl_context=ssl_context);

    def _add_cors_headers(self, response):

        response.headers["Access-Control-Allow-Origin"] = self.config.cors.origin
        response.headers["Access-Control-Allow-Headers"] = self.config.cors.headers
        response.headers["Access-Control-Allow-Methods"] = self.config.cors.methods

        return response


class AppTestClientWrapper(object):
    """
    A Test client wrapper for a flask application

    perform common http requests with authentication
    """

    def __init__(self, app, token=None):
        super(AppTestClientWrapper, self).__init__()
        self.app = app

        if token:
            self.headers = {"Authorization": token}
        else:
            self.headers = {}

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        pass

    def get(self, *args, **kwargs):
        return self._wrapper(self.app.get, args, kwargs)

    def post(self, *args, **kwargs):
        return self._wrapper(self.app.post, args, kwargs)

    def put(self, *args, **kwargs):
        return self._wrapper(self.app.put, args, kwargs)

    def delete(self, *args, **kwargs):
        return self._wrapper(self.app.delete, args, kwargs)

    def get_json(self, *args, compressed=False, **kwargs):
        if compressed:
            if "headers" not in kwargs:
                kwargs['headers'] = {}
            kwargs['headers']["Accept-Encoding"] = "gzip"
        res = self._wrapper(self.app.get, args, kwargs)
        if res.status_code < 200 or res.status_code >= 300:
            raise Exception(res.data)
        data = res.data
        if compressed:
            data = gzip.decompress(data)
        body = json.loads(data.decode("utf-8"))
        return body['result']

    def post_json(self, url, data, *args, **kwargs):
        args = list(args)
        args.insert(0, url)
        kwargs['data'] = json.dumps(data)
        kwargs['content_type'] = 'application/json'
        return self._wrapper(self.app.post, args, kwargs)

    def put_json(self, url, data, *args, **kwargs):
        args = list(args)
        args.insert(0, url)
        kwargs['data'] = json.dumps(data)
        kwargs['content_type'] = 'application/json'
        return self._wrapper(self.app.put, args, kwargs)

    def _wrapper(self, method, args, kwargs):
        if "headers" not in kwargs:
            kwargs['headers'] = self.headers
        else:
            kwargs['headers'].update(self.headers)
        return method(*args, **kwargs)
