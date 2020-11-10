
"""

https://editor.swagger.io/

"""
import sys
import os

from functools import wraps
from collections import namedtuple
import mimetypes
import time
import logging
import json
import http

from .server_core import Response, Namespace, CaseInsensitiveDict

##
# A tuple describing a RESTful endpoint
RegisteredEndpoint = namedtuple('RegisteredEndpoint',
    ['path', 'long_name', 'doc', 'methods', 'params', 'headers', 'body', 'returns', 'auth', 'scope'])

#-------------

def null_validator(item):
    """ a validator which returns the object given """
    return item

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

#-------------

Parameter = namedtuple('Parameter',
    ['name', 'type', 'default', 'required', 'repeated', 'doc'])

class RequestNamespace(object):
    def __init__(self, params, headers):
        super(RequestNamespace, self).__init__()
        self.params = params
        self.headers = headers

def _default_exception_handler(ex):
    logging.exception("unhandled exception")
    return Response(500, {}, {"error": "unhandled exception"})

class Request(object):
    def __init__(self, raw):
        super(Request, self).__init__()
        self.raw = raw
        self.current_user = None
        self.location = None
        self.headers = None
        self.query = None

_ordinal = 1

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

    global _ordinal
    f._ordinal = _ordinal
    _ordinal += 1

    @wraps(f)
    def wrapper(_, resource, request):
        t0 = time.time()

        scope = None
        if hasattr(f, '_scope'):
            scope = f._scope

        req = Request(request)
        req.raw_socket = request.request

        # extract authentication tokens
        if hasattr(f, '_security'):
            for strategy in f._security:
                # request: {query, headers}
                user = strategy(resource, scope, request.location.query, request.headers)
                if user:
                    req.current_user = user
                    break
            else:
                logging.error("all auth strategies failed")
                return Response(401, {}, {"error": "no authentication"})

        # .location.path : the full path given
        # .location.args : the components that matched
        # .location.query : dictionary of query parameters
        # .query : the query parameters that matched as an object

        req.location = request.location
        req.args = request.args

        # extract request query parameters
        req.query = Namespace()
        if hasattr(f, "_params"):
            for param in f._params:
                if param.required and param.name not in request.location.query:
                    error = "required query parameter `%s` not found" % param.name
                    return Response(400, {}, {"error": error})


                # validate the query parameter and add it to the request args

                try:
                    if param.repeated:
                        value = [param.type(v) for v in request.location.query[param.name]]
                    elif param.name in request.location.query:
                        value = param.type(request.location.query[param.name][0])
                    else:
                        value = param.default

                    setattr(req.query, param.name, value)

                except Exception as e:
                    logging.exception("%s" % e)
                    error = "unable to validate query parameter: %s=%s" % (
                            param.name, request.location.query[param.name]
                        )
                    return Response(400, {}, {"error": error})

        # extract request header parameters
        req.headers = CaseInsensitiveDict()
        if hasattr(f, "_headers"):
            for header in f._headers:
                name = header.name.encode("utf-8")
                if header.required and name not in request.headers:
                    error = "required query parameter `%s` not found" % header.name
                    return Response(400, {}, {"error": error})

                # validate the header parameter
                try:
                    if name in request.headers:
                        value = header.type(request.headers[name].decode("utf-8"))
                    else:
                        value = header.default
                except Exception as e:
                    logging.exception("%s" % e)
                    error = "unable to validate query parameter: %s=%s" % (
                            header.name, request.headers[name]
                        )
                    return Response(400, {}, {"error": error})

                req.headers[header.name] = value

        # extract the request body
        req.body = None
        if hasattr(f, "_body"):
            try:
                type_, _ = f._body

                content_type_raw = request.headers.get(b'Content-Type')
                if content_type_raw:
                    content_type = content_type_raw.decode("utf-8").split(';')
                else:
                    content_type = []

                # TODO: dispatch type_ based on the content type
                #       allow a default type_ when mimetype is not available

                mimetypes = type_.mimetype()
                if isinstance(mimetypes, str):
                    mimetypes = [mimetypes]

                req_is_json = 'application/json' in content_type
                req_requires_json = 'application/json' in mimetypes

                if req_requires_json:
                    # only decode request as json if we are given json
                    # and the request method is expecting json
                    if req_is_json:
                        binary_data = request.body.read()
                        obj = json.loads(binary_data.decode('utf-8'))
                        req.body = type_(obj)
                    else:
                        error = "Invalid Content-Type: %s" % content_type_raw
                        return Response(400, {}, {"error": error})
                else:
                    req.body = type_(request.body)

            except Exception as e:
                logging.exception("unable to validate body")
                return Response(400, {}, {"error": "unable to validate body"})

        # extract custom exception handlers for this method
        handlers = []
        if hasattr(f, "_handlers"):
            handlers = f._handlers

        # execute the endpoint method
        t1 = time.time()
        try:
            return_value = f(resource, req)
        except BaseException as ex:

            for handler in handlers:
                if isinstance(ex, handler.type):
                    return_value = handler.handle(resource, req, ex)
                    break
            else:
                return_value = _default_exception_handler(ex)

        t2 = time.time()
        if hasattr(f, '_timeout'):
            t = (t2 - t0) * 1000
            if t >= f._timeout:
                logging.warning("%s.%s ran for %.3fms", f.__module__,
                    f.__qualname__, t)

        if hasattr(f, '_compressed'):
            return_value.compress = True

        return return_value

    return wrapper

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

def body(type_=None):
    if type_ is None:
        type_ = BinaryStreamOpenApiBody()

    def decorator(f):
        f._body = (type_, None)
        return f
    return decorator

def returns(obj):
    def decorator(f):
        f._returns = obj
        return f
    return decorator

def compressed(f):
    f._compressed = True
    return f

def timed(timeout=100):
    def decorator(f):
        f._timeout = timeout
        return f
    return decorator

WebEndpoint = namedtuple('WebEndpoint',
    ['path', 'methods', 'name', 'method', 'params', 'headers', 'body', 'returns', 'auth', 'scope'])

class ResourceType(type):

    def __init__(cls, name, bases, namespace):

        # create the variable if it has not yet been created.
        # otherwise inherit the defaults from the parent class
        if not hasattr(cls, '_class_endpoints'):
            cls._class_endpoints = []
        else:
            cls._class_endpoints = cls._class_endpoints[:]

        for key, value in namespace.items():

            if hasattr(value, "_endpoint"):
                func = getattr(cls, key)
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

class Resource(object):
    def __init__(self):
        super(Resource, self).__init__()

        self._endpoints = []

        for name in dir(self):
            attr = getattr(self, name)
            if hasattr(attr, '_endpoint'):

                func = attr

                fname = self.__class__.__name__ + "." + func.__name__
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

                self._endpoints.append(endpoint)


    def endpoints(self):

        return [(self, e.methods[0], e.path, e.method) for e in self._endpoints]

#----------------------------

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

    def model(self):
        return {}

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
            try:
                self.object(item)
            except Exception as e:
                raise


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

class ObjectEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        raise TypeError(type(obj))

class OpenApi(object):
    def __init__(self, endpoints):
        super(OpenApi, self).__init__()
        self.attrs = {}

        self._generate(endpoints)

    def set(self, attr, value):
        self.attrs[attr] = value

    def __setitem__(self, key, value):
        self.attrs[key] = value

    def get(self, key):
        return self.attrs[key]

    def __getitem__(self, key):
        return self.attrs[key]

    def json(self):
        return self.attrs

    def jsons(self, **kwargs):
        return json.dumps(self.attrs, cls=ObjectEncoder, **kwargs)

    def description(self, value):
        self['info']['description'] = value
        return self

    def title(self, value):
        self['info']['title'] = value
        return self

    def version(self, value):
        self['info']['version'] = value
        return self

    def contact(self, url=None, email=None):

        if url is not None:
            self['info']['contact']['url'] = url
        elif 'url' in self['info']['contact']:
            del self['info']['contact']['url']

        if email is not None:
            self['info']['contact']['email'] = email
        elif 'email' in self['info']['contact']:
            del self['info']['contact']['email']

        return self

    def license(self, name=None, url=None):

        if url is not None:
            self['info']['license']['url'] = url
        elif 'info' in self['info']['license']:
            del self['info']['license']['url']

        if name is not None:
            self['info']['license']['name'] = name
        elif 'name' in self['info']['license']:
            del self['info']['license']['name']

        return self

    def servers(self, value):
        # value: list of objects
        # {"url": "https://..."}
        self['servers'] = value
        return self

    def __str__(self):
        return self.jsons()

    def _generate(self, endpoints):

        openapi = self

        openapi['openapi'] = '3.0.0'

        openapi['paths'] = {}

        openapi['servers'] = {}

        openapi['components'] = {}
        openapi['components']['schemas'] = {}

        openapi['info'] = {}
        self['info']['contact'] = {}
        self['info']['license'] = {}

        # todo: generate security using registered security settings
        # found inside the endpoints
        openapi['components']['securitySchemes'] = {
            "basicAuth": {"type": "http", "scheme": "basic"},
            "tokenAuth": {"type": "apiKey", 'in': 'header', 'name': 'Authorization'},
        }

        for endpoint in sorted(endpoints, key=lambda e: e.path):
            for method in sorted(endpoint.methods):

                if not endpoint.path.startswith("/api"):
                    continue

                path, desc = self._fmt_endpoint(method, endpoint)

                if path not in openapi['paths']:
                    openapi['paths'][path] = {}

                openapi['paths'][path][method.lower()] = desc

    def _fmt_endpoint(self, method, endpoint):

        desc = {}
        path = endpoint.path

        tag = endpoint.long_name.split('.')[0].replace("Resource", "")

        desc['tags'] = [tag]
        desc['summary'] = endpoint.long_name

        # reformat the description
        # trim whitespace at the start of the lines
        d = endpoint.doc or ""
        count = 0
        for c in d:
            if c == '\n':
                count = 0
            elif c == ' ':
                count += 1
            else:
                break
        if count > 1:
            d = d.replace('\n' + ' ' * count, "\n")
        d = d.strip()
        desc['description'] = d

        desc['parameters'] = []

        if isinstance(endpoint.returns, list):
            desc['responses'] = {}
            for code in endpoint.returns:
                desc['responses'][str(code)] = {
                    "description": http.client.responses[code]
                }
        elif isinstance(endpoint.returns, dict):
            desc['responses'] = {}
            for code, content in endpoint.returns.items():
                obj = desc['responses'][str(code)] = {
                    "description": http.client.responses[code]
                }

                if not isinstance(content, list):
                    content = [content]

                for model in content:
                    if model is None:
                        continue

                    if 'content' not in obj:
                        obj['content'] = {}

                    reg_name = self._reg_model(model)

                    mimetype = model.mimetype()

                    if isinstance(mimetype, str):
                        mimetype = [mimetype]

                    for m in mimetype:
                        obj['content'][m] = {
                            'schema': {'$ref': reg_name},
                        }
        else:
            desc['responses'] = {"200": {"description": "OK"}}

        _auth0 = {'basicAuth': endpoint.scope}
        _auth1 = {'tokenAuth': endpoint.scope}
        _auth = [[], [_auth0, _auth1]]

        desc['security'] = _auth[endpoint.auth]
        desc['operationId'] = endpoint.long_name

        path, desc['parameters'] = extract_path_parameters(path)

        sys.stderr.write("%-8s %s %s\n" % (method, 'FT'[endpoint.auth], path))

        for param in endpoint.params:
            p = extract_parameter("query", param)
            desc['parameters'].append(p)

        for param in endpoint.headers:
            p = extract_parameter("header", param)
            desc['parameters'].append(p)

        if method in ('POST', 'PUT'):
            items = endpoint.body
            if not isinstance(items, list):
                items = [items]
            for model in items:
                if model and hasattr(model, 'mimetype'):
                    self._reg_body(desc, model)
                else:
                    sys.stderr.write("%s: oldstyle body\n" % endpoint.long_name)

        return path, desc

    def _reg_body(self, desc, model):

            reg_name = self._reg_model(model)

            mimetype = model.mimetype()

            if isinstance(mimetype, str):
                mimetype = [mimetype]

            content = {
                "schema": {
                    "$ref": reg_name
                }
            }

            if mimetype and 'requestBody' not in desc:
                desc['requestBody'] = {
                    "description": "TODO",
                    "required": True,
                    "content": {}
                }

            for m in mimetype:
                desc['requestBody']['content'][m] = content

    def _reg_model(self, model):

        obj = self['components']['schemas'][model.name()] = {
            "type": model.type()
        }

        if obj['type'] == 'object':
            obj["properties"] = model.model()
            _required = []
            for key, value in obj["properties"].items():
                if isinstance(value, OpenApiBody):

                    obj['properties'][key] = {\
                        "$ref": self._reg_model(value)}
                else:
                    if 'required' in value:
                        if value['required']:
                            _required.append(key)
                        del value['required']
            if _required:
                obj['required'] = _required
        elif obj['type'] == 'array':
            obj['items'] = model.schema()
        elif obj['type'] == 'stream':
            obj['type'] = "string"
            obj['format'] = "binary"

        return '#/components/schemas/' + model.name()

def extract_parameter(kind, param):
    _type = param.type

    if hasattr(_type, 'schema'):

        return {
            "in": kind,
            "name": param.name,
            "required": _type.getRequired(),
            "description": _type.getDescription(),
            "schema": _type.schema()
        }

    else:
        sys.stderr.write("oldstyle parameter: %s\n" % param.name)
        return {
            "in": kind,
            "name": param.name,
            "required": param.required,
            "description": param.doc,
            "schema": {'type': 'string'}
        }

def extract_path_parameters(path):

    parameters = []
    parts = path.split("/")
    i=0;
    for i, part in enumerate(parts):
        if part.startswith(":"):

            type_name = "string"
            if part.endswith("+"):
                type_name = "path: 1 or more components"
                part = part[:-1]
            elif part.endswith("*"):
                type_name = "path: 0 or more components"
                part = part[:-1]

            part = part[1:]

            p = {
                "in": "path",
                "name": part,
                "required": True,
                "description": "type: " + type_name,
                "schema": {'type': 'string'}
            }

            parameters.append(p)

            parts[i] = '{%s}' % part

    return "/".join(parts), parameters

def fmtary(tab, width, prefix, suffix, sep, content):

    s = tab + prefix
    first = True
    for item in content:
        if len(s) + len(item) + len(sep) > width:
            yield s + sep + "\n "
            first = True
            s = tab

        if first:
            first = False
        else:
            s += sep

        s += str(item)

    s += suffix

    yield s + "\n"

def curldoc(endpoints, host):
    # endpoints = app._registered_endpoints_v2

    for endpoint in sorted(endpoints, key=lambda e: e.path):

        if not endpoint.path.startswith('/api'):
            continue

        for method in sorted(endpoint.methods):

            yield "\n\n%s\n%s\n\n" % ('-' * 80, endpoint.long_name)
            cmd = []

            if endpoint.auth:
                cmd.append("-u")
                cmd.append("username:password")

            cmd.append("-X")
            cmd.append(method)

            path, param_p_defs = extract_path_parameters(endpoint.path)

            params = []
            param_q_defs = []
            for param in endpoint.params:
                params.append("'\\\n    '%s={%s}" % (param.name, param.name))
                param_q_defs.append(extract_parameter('query', param))

            param_h_defs = []
            for param in endpoint.headers:
                cmd.append('\\\n  -H')
                cmd.append('%s=\'{%s}\'' % (param.name, param.name))
                param_h_defs.append(extract_parameter('header', param))

            mimeschema = {}
            if method in ('POST', 'PUT'):

                cmd.append("\\\n  -H")
                cmd.append("Content-Type='{Content-Type}'")
                items = endpoint.body

                if not isinstance(items, list):
                    items = [items]

                binary = False

                for model in items:
                    if model and hasattr(model, 'mimetype'):

                        name = model.name()
                        mimetype = model.mimetype()
                        if isinstance(mimetype, str):
                            mimetype = [mimetype]

                        type = model.type()
                        schema = {"type": type}
                        if type == 'object':
                            schema = model.model()

                        if type == 'array':
                            schema = [model.schema()]

                        if type == 'stream':
                            schema['type'] = "string"
                            schema['format'] = "binary"
                            binary = True

                        for m in mimetype:
                            mimeschema[m] = schema

                if binary:
                    cmd.append("\\\n  --data-binary")
                else:
                    cmd.append("\\\n  -d")

                cmd.append("'@{path}'")

            url = "%s%s" % (host, path)
            if params:
                url += '?' + '&'.join(params)

            cmd.append("\\\n  '%s'" % url)

            yield "curl %s\n" % (" ".join(cmd))

            for title, defs in [
              ("Path Parameters", param_p_defs),
              ("Query Parameters", param_q_defs),
              ("Header Parameters", param_h_defs)]:

                if len(defs):
                    yield "\n%s:\n" % title
                    for p in defs:
                        _default = None
                        if 'enum' in p['schema']:
                            _type = 'enum'
                        else:
                            _type = p['schema']['type']
                            _default = p['schema'].get('default', None)

                        m = "  %s - %s" % (p['name'], _type)

                        if _default:
                            m += " (%s)" % _default

                        if p['required']:
                            m += " required"

                        if p['description']:
                            pad = "\n    "
                            d = p['description'].replace("\n", pad)
                            m += pad + d

                        yield(m + "\n")

                        if 'enum' in p['schema']:
                            yield from fmtary("    ", 70,
                                "{", "}", ", ", sorted(p['schema']['enum']))

            if len(mimeschema) > 0:
                yield "\nContent-Type:\n"

            for mimetype, schema in sorted(mimeschema.items()):
                yield "\n  %s:\n" % mimetype
                s = json.dumps(schema, cls=ObjectEncoder, indent=2)
                s = "    " + s.replace("\n", "\n    ")
                yield "%s\n" % s

    yield("\n\n")

