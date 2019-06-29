
"""

A Web Resource defines the mapping between a url endpoint and the function
that will be executed. This file contains all of the python decorators
for creating a resource.

TODO:
    allow registering an authentication strategy
        e.g. resource.addAuthStrategy(strategy)
        strategy := request => boolean

    get/post/put/delete should wrap with an exception handler
    allow registering aditional exception types and handlers
        e.g. resource.registerException(FooException, FooHandler)
        application.registerException would map the handler
        to all registered resources

"""
import os
import sys
import time
import traceback

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
    ['path', 'methods', 'name', 'method', 'params', 'headers', 'body', 'returns', 'auth', 'scope'])

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
    logging.error("request: %s" % (request.url))
    logging.error("request: %s" % dict(request.headers))
    # traceback.print_stack()
    return jsonify(error=message), code

class ParameterNamespace(object):
    pass

class RequestNamespace(object):
    def __init__(self, params, headers):
        super(RequestNamespace, self).__init__()
        self.params = params
        self.headers = headers

def _default_exception_handler(ex):
    logging.exception("unhandled exception")
    return httpError(500, "Unhandled Exception")

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
        t0 = time.time()

        if len(args) == 0:
            return httpError(500, "endpoint not registered correctly")
        # first arg is always the web resource which
        # registered the endpoint
        resource = args[0]

        scope = None
        if hasattr(f, '_scope'):
            scope = f._scope

        # extract authentication tokens
        if hasattr(f, '_security'):
            for strategy in f._security:
                namespace = RequestNamespace(request.args, request.headers)
                if strategy(resource, scope, namespace):
                    break
            else:
                logging.error("all auth strategies failed")
                return httpError(401, "no authentication")

        # extract request query parameters
        g.args = ParameterNamespace()
        if hasattr(f, "_params"):
            for param in f._params:
                if param.required and param.name not in request.args:
                    return httpError(400,
                        "required query parameter `%s` not found" % param.name)

                # validate the query parameter and add it to the request args

                try:
                    if param.repeated:
                        value = [param.type(v) for v in request.args.getlist(param.name)]
                    elif param.name in request.args:
                        value = param.type(request.args[param.name])
                    else:
                        value = param.default

                    setattr(g.args, param.name, value)

                except Exception as e:
                    logging.exception("%s" % e)
                    return httpError(400,
                        "unable to validate query parameter: %s=%s" % (
                            param.name, request.args[param.name]))



        # extract request header parameters
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

        # extract the request body
        g.body = None
        if hasattr(f, "_body"):
            try:
                type_, content_type = f._body
                # logging.info("body: %s %s %s", type_, content_type, request.headers['Content-Type'])
                content_type = request.headers.get('Content-Type')
                accept = content_type.split(';')
                # TODO: dispatch type_ based on the content type
                #       allow a default type_ when mimetype is not available
                if 'application/x-www-form-urlencoded' in accept:
                    g.body = type_(BytesIO(request.get_data()))
                elif 'application/json' in accept:
                    g.body = type_(request.get_json())
                else:
                    g.body = type_(request.stream)
            except Exception as e:
                logging.exception("unable to validate body")
                return httpError(400, "unable to validate body")

        # extract custom exception handlers for this method
        g.handlers = []
        if hasattr(f, "_handlers"):
            g.handlers = f._handlers

        # execute the endpoint method
        t1 = time.time()
        try:
            return_value = f(*args, **kwargs)
        except BaseException as ex:

            for handler in g.handlers:
                if isinstance(ex, handler.type):
                    return_value = handler.handle(ex)
                    break
            else:
                return_value = _default_exception_handler(ex)

        t2 = time.time()
        if hasattr(f, '_timeout'):
            t = (t2 - t0) * 1000
            if t >= f._timeout:
                logging.warning("%s.%s ran for %.3fms", f.__module__,
                    f.__qualname__, t)

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

def param(name, type_=str):
    """decorator which validates query parameters"""

    def decorator(f):
        if not hasattr(f, "_params"):
            f._params = []

        if isinstance(type_, OpenApiParameter):
            f._params.append(Parameter(name, type_,
                type_.getDefault(),
                type_.getRequired(),
                type_.getRepeated(),
                type_.getDescription()))
        else:
            # f._params.append(Parameter(name, type_, default, False, False, doc))
            raise TypeError("%s" % type_)
        return f
    return decorator

def header(name, type_=None, default=None, required=False, doc=""):
    """decorator which validates query parameters"""

    if type_ is None:
        type_ = String().required(required).description(doc).default(default)

    def decorator(f):
        if not hasattr(f, "_headers"):
            f._headers = []
        f._headers.append(Parameter(name, type_, default, required, False, doc))
        return f
    return decorator

def body(type_, content_type="application/json"):
    def decorator(f):
        f._body = (type_, content_type)
        return f
    return decorator

def returns(obj):
    def decorator(f):
        f._returns = obj
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

                _returns = None
                if hasattr(func, "_returns"):
                    _returns = func._returns

                _auth = False
                if hasattr(func, "_auth"):
                    _auth = func._auth

                _scope = []
                if hasattr(func, '_scope'):
                    _scope = func._scope

                endpoint = WebEndpoint(path, methods, fname,
                    func, _params, _headers, _body, _returns, _auth, _scope)

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

        for path, methods, name, func, _params, _headers, _body, _returns, _auth, _scope in self._class_endpoints:
            # get the instance of the method which is bound to self
            bound_method = getattr(self, func.__name__)
            if path == "":
                path = self.root
            elif not path.startswith("/"):
                path = (self.root + '/' + path).replace("//", "/")

            endpoints.append(WebEndpoint(path, methods, name,
                bound_method, _params, _headers, _body, _returns, _auth, _scope))

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
        _returns = None
        _auth = False
        _scope = False
        self.__endpoints.append(WebEndpoint(path, methods, name,
            func, _params, _headers, _body, _returns, _auth, _scope))

    def _start(self):
        """called just before the web listener is started"""
        pass

    def _end(self):
        """called while tearing down the resource"""
        pass

class OpenApiParameter(object):
    def __init__(self, type_):
        super(OpenApiParameter, self).__init__()
        self.attrs = {"type": type_}
        self.__name__ = self.__class__.__name__
        self._default = None
        self._required = False
        self._description = ""
        self._case_sensitive = False
        self._repeated = False

    def __call__(self, obj):
        raise NotImplementedError()

    def schema(self):
        obj = dict(self.attrs)

        if self._repeated:
            obj['type'] = 'array'
            obj['items'] = {'type': self.attrs['type']}

        if self._default is not None:
          obj['default'] = self._default
        return obj

    def default(self, value):
        self._default = value
        return self

    def getDefault(self):
        return self._default

    def description(self, value):
        self._description = value
        return self

    def getDescription(self):
        return self._description

    def required(self, value=True):
        self._required = value
        return self

    def not_required(self, value=False):
        self._required = value
        return self

    def getRequired(self):
        return self._required

    def repeated(self, value=True):
        """
        the query parameter can be given multiple times
        """
        self._repeated = value
        return self

    def getRepeated(self):
        return self._repeated

    def enum(self, value, case_sensitive=False):

        self._case_sensitive = case_sensitive

        if not self._case_sensitive:
            self.attrs['enum'] = set([s.lower() for s in value])
        else:
            self.attrs['enum'] = set(value)

        return self

class String(OpenApiParameter):
    def __init__(self):
        super(String, self).__init__("string")

    def __call__(self, value):

        v = str(value)

        if 'enum' in self.attrs:

            if not self._case_sensitive:
                v = v.lower()

            if v not in self.attrs['enum']:
                raise Exception("invalid input. not in enum range")

        return v

class Boolean(OpenApiParameter):
    def __init__(self):
        super(Boolean, self).__init__("boolean")

    def __call__(self, value):
        s = value.lower()
        if s == "true":
            return True
        if s == "false":
            return False
        try:
            return int(s) != 0
        except:
            pass

        raise Exception("Invalid input")

class Integer(OpenApiParameter):
    def __init__(self):
        super(Integer, self).__init__("integer")

    def __call__(self, value):

        v = int(value)

        if 'minimum' in self.attrs:
            if v < self.attrs['minimum']:
                raise Exception("invalid input. value >= %d" % self.attrs['minimum'])

        if 'maximum' in self.attrs:
            if v > self.attrs['maximum']:
                raise Exception("invalid input. value <= %d" % self.attrs['maximum'])

        if 'enum' in self.attrs:
            if v not in self.attrs['enum']:
                raise Exception("invalid input. not in enum range")

        return v

    def min(self, value):
        self.attrs["minimum"] = value
        return self

    def max(self, value):
        self.attrs["maximum"] = value
        return self

    def range(self, vmin, vmax):
        self.attrs["minimum"] = vmin
        self.attrs["maximum"] = vmax
        return self

class URI(String):

    def __call__(self, s):

        # https://en.wikipedia.org/wiki/Hostname

        org = s

        for prefix in ("http://", "https://"):
            if s.startswith(prefix):
                s = s[len(prefix):]
                break

        if '/' in s:
            s, path = s.split('/', 1)

        if ':' in s:

            s, p = s.split(':', 1)

            try:
                port = int(p)
            except Exception as e:
                port = 0

            if port <= 0 or port > 65536:
                raise Exception("Invalid URI: port out of range")

        if len(s.strip()) == 0:
            return ""

        # check that the hostname component is a dotted
        # sequence of alphanumeric characters
        if len(s) > 253:
            raise Exception("Invalid URI: hostname too long")

        for part in s.split('.'):
            if len(s) > 63 or not part.isalnum():
                raise Exception("Invalid URI: component part too long")

        return org

class OpenApiBody(object):
    def __init__(self, mimetype=None):
        super(OpenApiBody, self).__init__()
        self._mimetype = mimetype

        # todo legacy endpoint support
        self.__name__ = self.__class__.__name__

    def name(self):
        return self.__class__.__name__.replace("OpenApiBody", "")

    def __call__(self, obj):
        raise NotImplementedError()

    def type(self):
        """openapi data type

        string|integer|object
        """
        raise NotImplementedError()

    def mimetype(self):
        """ """
        return self._mimetype

    def schema(self):
        raise NotImplementedError()

class ArrayOpenApiBody(OpenApiBody):
    def __init__(self, object):
        super()
        self.__name__ = self.__class__.__name__
        self.object = object

    def __call__(self, obj):

        if not isinstance(obj, (tuple, list)):
            raise Exception("invalid object")

        for item in obj:
            self.object(item)

        return obj

    def name(self):
        return self.object.name() + self.__class__.__name__.replace("OpenApiBody", "")

    def mimetype(self):
        return "application/json"

    def type(self):
        return "array"

    def schema(self):
        obj = {
            "type": self.object.type(),

        }
        if obj['type'] == 'object':
            obj["properties"] = self.object.model()

            obj['required'] = []
            for key, value in obj["properties"].items():
                if 'required' in value:
                    if value['required']:
                        obj['required'].append(key)
                    del value['required']

        return obj

class StringOpenApiBody(OpenApiBody):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __call__(self, obj):

        if hasattr(obj, 'read'):
            obj = obj.read().decode("utf-8").strip()

        if not isinstance(obj, str):
            raise Exception("invalid object: %s %s" % (type(obj), content_type))

        return obj

    def type(self):
        return "string"

class JsonOpenApiBody(OpenApiBody):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __call__(self, obj):
        model = self.model()
        for key in model.keys():
            if key not in obj and model[key].get('required', False):
                raise Exception("invalid request body. missing: %s" % key)
        return obj

    def name(self):
        return self.__class__.__name__.replace("OpenApiBody", "")

    def mimetype(self):
        return "application/json"

    def type(self):
        return "object"

class EmptyBodyOpenApiBody(OpenApiBody):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __call__(self, obj):
        return obj

    def mimetype(self):
        return []

    def type(self):
        return "stream"

class TextStreamOpenApiBody(OpenApiBody):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __call__(self, obj):
        return obj

    def mimetype(self):
        return ['text/plain', 'application/octet-stream', 'application/x-www-form-urlencoded']

    def type(self):
        return "stream"

class BinaryStreamOpenApiBody(OpenApiBody):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __call__(self, obj):
        return obj

    def mimetype(self):
        return ['application/octet-stream', 'application/x-www-form-urlencoded']

    def type(self):
        return "stream"

class BinaryStreamResponseOpenApiBody(OpenApiBody):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __call__(self, obj):
        return obj

    def mimetype(self):
        return 'application/octet-stream'

    def type(self):
        return "stream"
