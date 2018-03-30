
from functools import wraps
from flask import after_this_request

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
    compress the output using gzip if the client supports it.
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
                fname = name + "." + value.__name__
                path = value._endpoint
                methods = value._methods
                print("meta", fname, path)
                cls._class_endpoints.append( (path, methods, fname, value) )

# , metaclass = MetaWebResource
class WebResource(object):
    """base class for a WebResource

    A WebResource wraps a service with a number of REST endpoints

    """


    def __init__(self, root="/"):
        super(WebResource, self).__init__()
        self.root = root
        self.__endpoints = []

    def endpoints(self):
        return self.__endpoints

    def register(self, path, func, methods):
        name = self.__class__.__name__ + "." + func.__name__
        path = (self.root + path).replace("//","/")
        self.__endpoints.append( (path, methods, name, func) )