"""

A declarative web application framework.

Create Web Resources and define RESTful endpoints using python
decorators. The resources can then be registered add run time to build
an application.

The mix of declarative and imperative styles enables
easy testing and development
"""
import os
import sys
import flask
from flask import url_for, request, g, jsonify
import json
import gzip
import argparse
import logging

import eventlet
import eventlet.wsgi

from socketio import Server as SocketServer, Middleware as SocketMiddleware
import ssl

from .client import RegisteredEndpoint, Parameter, AuthenticatedRestClient, \
    FlaskAppClient, generate_argparse, split_auth, Response

from http.server import HTTPServer, BaseHTTPRequestHandler

# monkey patch workzeug to remove Server header
# found in workzeug.serving
def _send_header(self, key, value):
    if key not in ('Server', 'Date'):
        BaseHTTPRequestHandler._send_header(self, key, value)
BaseHTTPRequestHandler._send_header = BaseHTTPRequestHandler.send_header
BaseHTTPRequestHandler.send_header = _send_header

class FlaskApp(object):
    """FlaskApp is a flask application wrapper

    resources can be registered to add endpoints to the application
    """
    def __init__(self, config):
        super(FlaskApp, self).__init__()
        self.config = config

        # sio is only configured if a websocket listener is defined
        self.sio = None

        self.app = flask.Flask(self.__class__.__name__,
            static_folder=None)
            #static_folder=self.config.static_dir,
            #template_folder=self.config.build_dir)

        # set the max upload file size limit to 100MB
        self.app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

        self.log = self.app.logger

        if not self.config.null and not os.path.exists(self.config.build_dir):
            self.log.warn("not found: %s" % self.config.build_dir)

        if not self.config.null and not os.path.exists(self.config.static_dir):
            self.log.warn("not found: %s" % self.config.static_dir)

        self.app.after_request(self._add_cors_headers)

        self._registered_endpoints = []
        self._registered_websockets = []
        self._registered_resources = []

        self.async_mode = "eventlet"

    def _enable_sio(self):
        if self.sio is None:
            # todo: support gunicorn, eventlet
            self.sio = SocketServer()
            self.app.wsgi_app = SocketMiddleware(self.sio, self.app.wsgi_app)

    def add_resource(self, res):

        self._registered_resources.append(res)

        for path, methods, name, func, params, body in res.endpoints():
            self.register(path, name, func,
                params=params, body=body, methods=methods)

        websockets = res.websockets()
        if len(websockets) > 0:
            self._enable_sio()

            res.sio = self.sio

            for name, event, namespace, func in websockets:
                self.sio.on(event, func, namespace=namespace)

                self._registered_websockets.append((name, event, namespace, func))

    def register(self, path, name, callback, params=None, body=None, **options):
        msg = ""
        try:
            self.app.add_url_rule(path, name, callback, **options)

            body_name = None
            body_type = None

            body = body or (None, None)

            if body[0] is not None:
                body_name = body[0].__name__

                # if we have a body, determine the default mimetype
                if body[1] is not None:
                    body_type = body[1]
                else:
                    # TODO: what should the default be?
                    body_type = "application/octet-stream"

            new_body = (body_name, body_type)

            params = params or []
            new_params = []
            for param in params:
                data = param._asdict()
                data['type'] = param.type.__name__
                new_params.append(Parameter(**data))

            endpoint = RegisteredEndpoint(path, name, callback.__doc__,
                options['methods'], new_params, new_body)
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
                output.append((rule.endpoint, methods, url))

            for (name, event, namespace, meth) in self._registered_websockets:
                url = "%s <%s>" % (namespace, event)
                output.append((name, "WEBSOCKET", url))

        output.sort(key=lambda x: (x[0], x[2]))

        return output

    def generate_argparse(self):
        return generate_argparse(self._registered_endpoints)

    def client(self, hostname, username, password):
        username, domain, role = split_auth(username)
        client = AuthenticatedRestClient(hostname,
            username, password, domain, role)
        return FlaskAppClient(client, self._registered_endpoints)

    def test_client(self, token=None):
        client = AppTestClientWrapper(self.app.test_client(), token)
        client.host = lambda: "test://localhost"
        return client

    def run(self):

        for res in self._registered_resources:
            res._start()

        ssl_context = self.get_ssl_context()

        routes = self.list_routes()
        for endpoint, methods, url in routes:
            logging.info("{:40s} {:20s} {}".format(
                endpoint, methods, url))

        s = "s" if ssl_context else ""
        logging.info("running on: http%s://%s:%s" % (s,
            self.config.host, self.config.port))

        if self.async_mode == 'eventlet':
            socket = eventlet.listen((self.config.host, self.config.port))
            eventlet.wsgi.server(socket, self.app)
        else:
            self.app.run(host=self.config.host,
                         port=self.config.port,
                         ssl_context=ssl_context,
                         threaded=True)

    def _add_cors_headers(self, response):

        response.headers["Access-Control-Allow-Origin"] = self.config.cors.origin
        response.headers["Access-Control-Allow-Headers"] = self.config.cors.headers
        response.headers["Access-Control-Allow-Methods"] = self.config.cors.methods

        return response

    def get_ssl_context(self):
        context = None
        if os.path.exists(self.config.ssl.private_key) and \
           os.path.exists(self.config.ssl.certificate):
            context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            context.load_cert_chain(self.config.ssl.certificate,
                                    self.config.ssl.private_key)
        return context

    def __call__(self, env, start_response):
        # uwsgi support
        return self.app(env, start_response)

    def tearDown(self):

        for res in self._registered_resources:
            res._stop()

class TestResponse(Response):

    def json(self):

        if self._response.status_code < 200 or self._response.status_code >= 300:
            raise Exception(self._response.data)
        data = self._response.data

        if 'Content-Encoding' in self._response.headers:
            if self._response.headers['Content-Encoding'] == "gzip":
                data = gzip.decompress(data)

        return json.loads(data.decode("utf-8"))

    def stream(self, chunk_size=1024):
        return [self._response.data]

    def iter_content(self, chunk_size=1024):
        return self.stream()

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
        response = self._wrapper(self.app.get, args, kwargs)
        # TODO: deprecate getting the result by default,
        # and / or deprecate the json specific functions
        return response.json()['result']

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
        # convert the client format arguments into flask format
        if 'params' in kwargs:
            kwargs['query_string'] = kwargs['params']
            del kwargs['params']
        # stream is not supported on the test client
        # required as part of the client interface
        if 'stream' in kwargs:
            del kwargs['stream']

        response = TestResponse(method(*args, **kwargs))

        return response





