
from functools import wraps
from flask import after_this_request, request
from collections import namedtuple

from io import BytesIO
import gzip
import datetime

WebEndpoint = namedtuple('WebEndpoint', ['path', 'methods', 'name', 'method'])

def get(path):
    """decorator which registers a class method as a GET handler"""
    def decorator(f):
        f._endpoint = path
        f._methods = ['GET',]
        return f
    return decorator

def put(path):
    """decorator which registers a class method as a PUT handler"""
    def decorator(f):
        f._endpoint = path
        f._methods = ['PUT',]
        return f
    return decorator

def post(path):
    """decorator which registers a class method as a POST handler"""
    def decorator(f):
        f._endpoint = path
        f._methods = ['POST',]
        return f
    return decorator

def delete(path):
    """decorator which registers a class method as a DELETE handler"""
    def decorator(f):
        f._endpoint = path
        f._methods = ['DELET',]
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
                endpoint = WebEndpoint(path, methods, fname, func)
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

        for path, methods, name, func in self._class_endpoints:
            # get the instance of the method which is bound to self
            bound_func = getattr(self, func.__name__)
            if path == "":
                path = self.root
            elif not path.startswith("/"):
                path = (self.root + '/' + path).replace("//","/")
            endpoints.append( WebEndpoint(path, methods, name, bound_func) )

        return endpoints

    def register(self, path, func, methods):
        name = self.__class__.__name__ + "." + func.__name__
        if not path.startswith("/"):
            path = (self.root + '/' + path).replace("//","/")
        self.__endpoints.append( WebEndpoint(path, methods, name, func) )