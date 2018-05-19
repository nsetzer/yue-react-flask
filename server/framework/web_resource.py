
from functools import wraps
from flask import after_this_request, request, g, jsonify
from collections import namedtuple

from io import BytesIO
import gzip
import datetime
import logging

WebEndpoint = namedtuple('WebEndpoint',
    ['path', 'methods', 'name', 'method', 'params', 'body'])

def validate(expr, value):
    if not expr:
        raise Exception("invalid input")
    return value

def vmin(target,value):
    return validate(target <= value, value)

def vmax(target, value):
    return validate(target >= value, value)

# validate that an integer is between two numbers
int_range = lambda min_, max_: lambda v: vmax(max_,vmin(min_, int(v)))
# validate that an integer is larger than some number
int_min = lambda min_: lambda v: vmin(min_, int(v))
# validate that an integer is smaller than some number
int_max = lambda max_: lambda v: vmax(max_, int(v))

def httpError(code, message):
    # TODO: this should be at loglevel debug
    logging.error("[%3d] %s" % (code, message))
    return jsonify(error=message), code

def _endpoint_mapper(f):


    @wraps(f)
    def wrapper(*args, **kwargs):
        g.args = lambda: None
        if hasattr(f, "_params"):
            for name, type_, default, required in f._params:
                if required and name not in request.args:
                    return httpError(400,
                        "required query parameter `%s` not found" % name)

                # validate the query parameter and add it to the request args
                try:
                    if name in request.args:
                        value = type_(request.args[name])
                    else:
                        value = default
                except Exception as e:
                    logging.exception("%s" % e)
                    return httpError(400,
                        "unable to validate query parameter: %s=%s" % (name, request.args[name]))
                setattr(g.args, name, value)
        if hasattr(f, "_body"):
            try:
                type_, json = f._body
                g.body = type_(request.get_json())
            except Exception as e:
                return httpError(400, "unable to validate body")
        return f(*args, **kwargs)

    return wrapper

def get(path):
    """decorator which registers a class method as a GET handler"""
    def decorator(f):
        f._endpoint = path
        f._methods = ['GET',]
        return _endpoint_mapper(f)
    return decorator

def put(path):
    """decorator which registers a class method as a PUT handler"""
    def decorator(f):
        f._endpoint = path
        f._methods = ['PUT',]
        return _endpoint_mapper(f)
    return decorator

def post(path):
    """decorator which registers a class method as a POST handler"""
    def decorator(f):
        f._endpoint = path
        f._methods = ['POST',]
        return _endpoint_mapper(f)
    return decorator

def delete(path):
    """decorator which registers a class method as a DELETE handler"""
    def decorator(f):
        f._endpoint = path
        f._methods = ['DELET',]
        return _endpoint_mapper(f)
    return decorator

def param(name, type_=str, default=None, required=False):
    """decorator which validates query parameters"""

    def decorator(f):
        if not hasattr(f, "_params"):
            f._params = []
        f._params.append((name, type_, default, required))
        return f
    return decorator

def body(type_, json=True):
    def decorator(f):
        f._body = (type_, json)
        return f
    return decorator

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

class MetaWebResource(type):
    """
    A metaclass which registers decorated methods as REST endpoints
    """
    def __init__(cls, name, bases, namespace):
        cls._class_endpoints = []
        for key, value in namespace.items():
            if hasattr(value,"_endpoint"):
                func = value
                fname = name + "." + func.__name__
                path = func._endpoint
                methods = func._methods

                _body = (None, False)
                if hasattr(func, "_body"):
                    _body = func._body

                _params = []
                if hasattr(func, "_params"):
                    _params = func._params

                endpoint = WebEndpoint(path, methods, fname,
                    func, _params, _body)

                cls._class_endpoints.append( endpoint )

class WebResource(object, metaclass = MetaWebResource):
    """base class for a WebResource

    A WebResource wraps a service with an http interface

    """


    def __init__(self, root="/"):
        super(WebResource, self).__init__()
        self.root = root
        self.__endpoints = []

    def endpoints(self):
        """
        Returns a list of endpoints that have been registered to this resource

        This includes any endpoint registered using the register() function
        or with the get, put, post, delete decorators
        """

        endpoints = self.__endpoints[:]

        for path, methods, name, func, _params, _body in self._class_endpoints:
            # get the instance of the method which is bound to self
            bound_func = getattr(self, func.__name__)
            if path == "":
                path = self.root
            elif not path.startswith("/"):
                path = (self.root + '/' + path).replace("//","/")

            endpoints.append( WebEndpoint(path, methods, name,
                bound_func, _params, _body) )

        return endpoints

    def register(self, path, func, methods):
        name = self.__class__.__name__ + "." + func.__name__
        if not path.startswith("/"):
            path = (self.root + '/' + path).replace("//","/")
        # todo, support _body, _params somehow
        _body = (None, False)
        _params = []
        self.__endpoints.append( WebEndpoint(path, methods, name,
            func, _params, _body) )