
"""

A Web Resource defines the mapping between a url endpoint and the function
that will be executed. This file contains all of the python decorators
for creating a resource.
"""
import os
import sys
import time
from functools import wraps
from flask import (after_this_request, request, g, jsonify,
    stream_with_context, Response, send_file as flask_send_file)
from collections import namedtuple

from .client import Parameter

from io import BytesIO
import gzip
import datetime
import logging

import mimetypes
from re import findall

WebEndpoint = namedtuple('WebEndpoint',
    ['path', 'methods', 'name', 'method', 'params', 'headers', 'body'])

def validate(expr, value):
    if not expr:
        raise Exception("invalid input")
    return value

def vmin(target, value):
    return validate(target <= value, value)

def vmax(target, value):
    return validate(target >= value, value)

# validate that an integer is between two numbers
int_range = lambda min_, max_: lambda v: vmax(max_, vmin(min_, int(v)))
# validate that an integer is larger than some number
int_min = lambda min_: lambda v: vmin(min_, int(v))
# validate that an integer is smaller than some number
int_max = lambda max_: lambda v: vmax(max_, int(v))

def boolean(s):
    return s.lower() == "true"

def httpError(code, message):
    # TODO: this should be at loglevel debug
    logging.error("[%3d] %s" % (code, message))
    return jsonify(error=message), code

def _endpoint_mapper(f):

    if f.__name__ in globals():
        # this causes a confusing error, for example:
        #  @delete("/api/delete")
        #  def delete(self):             <-------------------------------+
        #      return "OK"                                               |
        #  @delete("/api/delete2")   <-- this delete is now this method -+
        #  def delete2(self):            and not the original imported
        #      return "OK"               annotation
        m = "Function name (%s) cannot be a web resource reserved word (%s)"
        raise RuntimeError(m % (f.__qualname__, f.__name__))

    @wraps(f)
    def wrapper(*args, **kwargs):
        g.args = lambda: None
        if hasattr(f, "_params"):
            for param in f._params:
                if param.required and param.name not in request.args:
                    return httpError(400,
                        "required query parameter `%s` not found" % param.name)

                # validate the query parameter and add it to the request args
                try:
                    if param.name in request.args:
                        value = param.type(request.args[param.name])
                    else:
                        value = param.default
                except Exception as e:
                    logging.exception("%s" % e)
                    return httpError(400,
                        "unable to validate query parameter: %s=%s" % (
                            param.name, request.args[param.name]))

                setattr(g.args, param.name, value)
        g.headers = dict()
        if hasattr(f, "_headers"):
            for header in f._headers:
                if header.required and header.name not in request.headers:
                    return httpError(400,
                        "required query parameter `%s` not found" % header.name)

                # validate the header parameter
                try:
                    if header.name in request.headers:
                        value = header.type(request.headers[header.name])
                    else:
                        value = header.default
                except Exception as e:
                    logging.exception("%s" % e)
                    return httpError(400,
                        "unable to validate query parameter: %s=%s" % (
                            header.name, request.headers[header.name]))

                g.headers[header.name] = value

        if hasattr(f, "_body"):
            try:
                type_, content_type = f._body
                logging.info("body: %s %s %s", type_, content_type, request.headers['Content-Type'])
                if request.headers['Content-Type'] == 'application/x-www-form-urlencoded':
                    g.body = type_(BytesIO(request.get_data()))
                elif content_type == 'application/json':
                    g.body = type_(request.get_json())
                else:
                    g.body = type_(request.stream)
            except Exception as e:
                logging.exception("unable to validate body")
                return httpError(400, "unable to validate body")

        s = time.time()
        return_value = f(*args, **kwargs)
        e = time.time()
        if hasattr(f, '_timeout'):
            t = (e - s) * 1000
            if t >= getattr(f, '_timeout'):
                logging.warning("%s.%s ran for %.3fms", f.__module__,
                    f.__wrapped__.__qualname__, t)
        return return_value

    return wrapper

def _websocket_wrapper(f):
    """
    decorator for websocket handlers which logs unhandled exceptions
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logging.exception("Unhandled websocket exception")
    return wrapper

def websocket(event, namespace):
    """decorator which registers a class method as a websocket handler
        event: one of: connect, message, disconnect
        namespace: the request path

        events:
            connect: can return false to reject the connection

        decorated function should accept (sid, msg)
            sid: the session id
            msg: payload
    """
    def decorator(f):
        f._namespace = namespace
        f._event = event
        return _websocket_wrapper(f)
    return decorator

def timed(timeout=100):
    def decorator(f):
        f._timeout = timeout
        return f
    return decorator

def get(path):
    """decorator which registers a class method as a GET handler"""
    def decorator(f):
        f._endpoint = path
        f._methods = ['GET']
        return _endpoint_mapper(f)
    return decorator

def put(path):
    """decorator which registers a class method as a PUT handler"""
    def decorator(f):
        f._endpoint = path
        f._methods = ['PUT']
        return _endpoint_mapper(f)
    return decorator

def post(path):
    """decorator which registers a class method as a POST handler"""
    def decorator(f):
        f._endpoint = path
        f._methods = ['POST']
        return _endpoint_mapper(f)
    return decorator

def delete(path):
    """decorator which registers a class method as a DELETE handler"""
    def decorator(f):
        f._endpoint = path
        f._methods = ['DELETE']
        return _endpoint_mapper(f)
    return decorator

def param(name, type_=str, default=None, required=False, doc=""):
    """decorator which validates query parameters"""

    def decorator(f):
        if not hasattr(f, "_params"):
            f._params = []
        f._params.append(Parameter(name, type_, default, required, doc))
        return f
    return decorator

def header(name, type_=str, default=None, required=False, doc=""):
    """decorator which validates query parameters"""

    def decorator(f):
        if not hasattr(f, "_headers"):
            f._headers = []
        f._headers.append(Parameter(name, type_, default, required, doc))
        return f
    return decorator

def body(type_, content_type="application/json"):
    def decorator(f):
        f._body = (type_, content_type)
        return f
    return decorator

def null_validator(item):
    """ a validator which returns the object given """
    return item

def compressed(f):
    """
    decorator that compresses the output using gzip if the client supports it.

    If the client request indicates that it accepts gzip compression,
    then compress the return payload.

    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        @after_this_request
        def zipper(response):
            accept_encoding = request.headers.get('Accept-Encoding', '')

            if 'gzip' not in accept_encoding.lower():
                return response

            response.direct_passthrough = False

            if (response.status_code < 200 or
               response.status_code >= 300):
                return response

            gzip_buffer = BytesIO()
            gzip_file = gzip.GzipFile(mode='wb',
                                      fileobj=gzip_buffer)
            gzip_file.write(response.data)
            gzip_file.close()

            response.data = gzip_buffer.getvalue()

            response.headers['Content-Encoding'] = 'gzip'
            response.headers['Vary'] = 'Accept-Encoding'
            response.headers['Content-Length'] = len(response.data)

            return response

        return f(*args, **kwargs)

    return wrapper

def local_file_generator(filepath, buffer_size=2048):

    with open(filepath, "rb") as rb:
        buf = rb.read(buffer_size)
        while buf:
            yield buf
            buf = rb.read(buffer_size)

def send_file(filepath):
    """
    this may not work on chrome, although that may also be a webkit
    issue with mp3 files...
    """

    attachment_name = os.path.split(filepath)[1]
    mimetype = mimetypes.guess_type(filepath)[0] or 'application/octet-stream'
    file_size = os.stat(filepath).st_size

    if "Range" not in request.headers:

        g = local_file_generator(filepath)
        response = Response(g, mimetype=mimetype)
    else:

        ranges = findall(r"\d+", request.headers["Range"])
        begin  = int(ranges[0])

        end = file_size
        if len(ranges) > 1:
            end = min(file_size, int(ranges[1]))

        nbytes = max(end - begin, 1024)

        with open(filepath, "rb") as rf:
            rf.seek(begin)
            data = rf.read(nbytes)

        ext = os.path.splitext(filepath)[1]

        response = Response(data, 200,
            mimetype=mimetype, direct_passthrough=True)

        byterange = 'bytes {0}-{1}/{2}'.format(
            begin, begin + len(data), len(data))
        response.headers.add('Content-Range', byterange)
        response.headers.add('Accept-Ranges', 'bytes')

    response.headers.set('Content-Length', file_size)

    response.headers.add('Content-Disposition', 'attachment',
        filename=attachment_name)

    return response

def send_generator(go, attachment_name, file_size=None, headers=None, attachment=True):
    """
    this may not work on chrome, although that may also be a webkit
    issue with mp3 files...

    attachment: under certain browser senarios, such as 'right click > view image'
        if there is a attachment header then the file will be downloaded
        instead of being displayed in the browser
    """

    mimetype = mimetypes.guess_type(attachment_name)[0] or \
        'application/octet-stream'

    response = Response(go, mimetype=mimetype)

    if file_size is not None:
        response.headers.set('Content-Length', file_size)

    if headers is not None:
        for key, val in headers.items():
            response.headers.set(key, str(val))

    if attachment:
        response.headers.add('Content-Disposition', 'attachment',
            filename=attachment_name)
    else:
        response.headers.add('Content-Disposition', "",
            filename=attachment_name)

    return response

def streamjs(document, array_key, array_values):
    """
    stream a json array

    used in conjunction with send_generator
    """

    s = "{"

    first = True
    for key, value in document.items():

        if key == array_key:
            continue;

        if not first:
            s += ",\"%s\":" % key
        else:
            s += "\"%s\":" % key

        s += json.dumps(value, separators=(',', ':'))

        first = False

        if len(s) > 2048:
            yield s.encode("utf-8")
            s = ""

    if not first:
        s += ",\"%s\":[" % array_key
    else:
        s += "\"%s\":[" % array_key

    yield s.encode("utf-8")

    first = True
    for value in array_values:
        if not first:
            s = "," + json.dumps(value, separators=(',', ':'))
            yield s.encode("utf-8")
        else:
            s = json.dumps(value, separators=(',', ':'))
            yield s.encode("utf-8")
        first = False

    s = "]}"
    yield s.encode("utf-8")

def send_js_generator(go, headers=None, attachment=True):

    mimetype = 'application/json'

    response = Response(go, mimetype=mimetype)

    if headers is not None:
        for key, val in headers.items():
            response.headers.set(key, str(val))

    return response

class MetaWebResource(type):
    """
    A metaclass which registers decorated methods as REST endpoints
    """
    def __init__(cls, name, bases, namespace):
        # create the variable if it has not yet been created.
        # otherwise inherit the defaults from the parent class
        if not hasattr(cls, '_class_endpoints'):
            cls._class_endpoints = []
        else:
            cls._class_endpoints = cls._class_endpoints[:]

        if not hasattr(cls, '_class_websockets'):
            cls._class_websockets = []
        else:
            cls._class_websockets = cls._class_websockets[:]

        for key, value in namespace.items():
            if hasattr(value, "_event"):
                func = value
                socket_handler = (value._event, value._namespace, func)
                cls._class_websockets.append(socket_handler)
            elif hasattr(value, "_endpoint"):
                func = value
                fname = name + "." + func.__name__
                path = func._endpoint
                methods = func._methods

                _body = (None, None)
                if hasattr(func, "_body"):
                    _body = func._body

                _params = []
                if hasattr(func, "_params"):
                    _params = func._params

                _headers = []
                if hasattr(func, "_headers"):
                    _headers = func._headers

                endpoint = WebEndpoint(path, methods, fname,
                    func, _params, _headers, _body)

                cls._class_endpoints.append(endpoint)

class WebResource(object, metaclass=MetaWebResource):
    """base class for a WebResource

    A WebResource wraps a service with an http interface

    """

    def __init__(self, root="/"):
        super(WebResource, self).__init__()
        self.root = root
        self.__endpoints = []
        self.__websockets = []

    def endpoints(self):
        """
        Returns a list of endpoints that have been registered to this resource

        This includes any endpoint registered using the register() function
        or with the get, put, post, delete decorators
        """

        endpoints = self.__endpoints[:]

        for path, methods, name, func, _params, _headers, _body in self._class_endpoints:
            # get the instance of the method which is bound to self
            bound_method = getattr(self, func.__name__)
            if path == "":
                path = self.root
            elif not path.startswith("/"):
                path = (self.root + '/' + path).replace("//", "/")

            endpoints.append(WebEndpoint(path, methods, name,
                bound_method, _params, _headers, _body))

        return endpoints

    def websockets(self):

        websockets = self.__websockets[:]

        for event, namespace, func in self._class_websockets:
            bound_method = getattr(self, func.__name__)
            name = self.__class__.__name__ + "." + func.__name__
            websockets.append((name, event, namespace, bound_method))

        return websockets

    def register(self, path, func, methods):
        name = self.__class__.__name__ + "." + func.__name__
        if not path.startswith("/"):
            path = (self.root + '/' + path).replace("//", "/")
        # todo, support _body, _params somehow
        _body = (None, None)
        _params = []
        _headers = []
        self.__endpoints.append(WebEndpoint(path, methods, name,
            func, _params, _headers, _body))

    def _start(self):
        """called just before the web listener is started"""
        pass

    def _end(self):
        """called while tearing down the resource"""
        pass
