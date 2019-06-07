
"""
Helper functions for implementing Web Resources
"""
import logging
from functools import wraps
from flask import after_this_request, request, jsonify, g
import traceback
from uuid import UUID

from ..dao.util import parse_iso_format
from ..dao.library import Song
from ..dao.exception import BackendException

from ..service.exception import ServiceException

from ..framework.web_resource import httpError, ArrayValidator, OpenApiParameter
from ..service.transcode_service import ImageScale

class HttpException(Exception):
    """docstring for HttpException"""
    def __init__(self, message, code=400):
        super(HttpException, self).__init__(message)
        self.status = code

def _handle_exceptions(f, args, kwargs):
    try:
        return f(*args, **kwargs)
    except HttpException as e:
        traceback.print_exc()
        return httpError(e.status, str(e))

    except FileNotFoundError as e:

        reason = "File Not Found Error: "
        if hasattr(g, 'current_user') and g.current_user is not None:
            reason = "Unhandled Exception (current user: %s): " % \
                g.current_user['email']

        return httpError(404, reason + str(e))

    except BackendException as e:

        reason = "Unhandled Backend Exception: "
        if hasattr(g, 'current_user') and g.current_user is not None:
            reason = "Unhandled Exception (current user: %s): " % \
                g.current_user['email']

        if e.HTTP_STATUS >= 500:
            logging.exception(reason)

        return httpError(e.HTTP_STATUS, reason + str(e))

    except ServiceException as e:

        reason = "Unhandled Service Exception: "
        if hasattr(g, 'current_user') and g.current_user is not None:
            reason = "Unhandled Exception (current user: %s): " % \
                g.current_user['email']

        #if e.HTTP_STATUS >= 500:
        logging.exception(reason)

        return httpError(e.HTTP_STATUS, reason + str(e))

    except Exception as e:
        # traceback.print_exc()

        reason = "Unhandled Exception: "
        if hasattr(g, 'current_user') and g.current_user is not None:
            reason = "Unhandled Exception (current user: %s): " % \
                g.current_user['email']

        logging.exception(reason)

        return httpError(500, reason + str(e))

def get_request_header(req, header):
    # TODO: can this method be deprecated?
    if header in request.headers:
        return request.headers[header]
    elif header.lower() in request.headers:
        return request.headers[header.lower()]
    else:
        raise HttpException("%s header not provided" % header, 401)

__g_features = set()
def __add_feature(features):
    """record features used by this application

    Every decorator adds the feature used to this set.
    this allows listing of all features used by the application
    """
    global __g_features
    if features is not None:
        for f in features:
            __g_features.add(f)

def get_features():
    return frozenset(__g_features)

def _requires_token_auth_impl(service, f, args, kwargs, features, token):
    """
    token based authentication for client side state management

    example:
        curl -H "Authorization: TOKEN <token>" -X GET localhost:4200/api/user

    """

    try:
        user_data = service.getUserFromToken(token, features)

        g.current_user = user_data

        return _handle_exceptions(f, args, kwargs)
    except Exception as e:

        logging.error("%s" % e)

    return httpError(401, "failed to authenticate user")

def _requires_basic_auth_impl(service, f, args, kwargs, features, token):
    """
    basic auth enables easy testing

    example:
        curl -u username:password -X GET localhost:4200/api/user
        curl -H "Authorization: BASIC <token>" -X GET localhost:4200/api/user

    """

    try:
        user_data = service.getUserFromBasicToken(token, features)

        g.current_user = user_data

        return _handle_exceptions(f, args, kwargs)
    except Exception as e:

        logging.error("%s" % e)

    return httpError(401, "failed to authenticate user")

def _requires_apikey_auth_impl(service, f, args, kwargs, features, token):
    """
    basic auth enables easy testing

    example:
        curl -H "Authorization: APIKEY <apikey>" -X GET localhost:4200/api/user

    """

    try:
        user_data = service.getUserFromApikey(token, features)

        g.current_user = user_data

        return _handle_exceptions(f, args, kwargs)
    except Exception as e:

        logging.error("%s" % e)

    return httpError(401, "failed to authenticate user")

def SecurityBasic(resource, scope, request):

    token = request.headers.get("Authorization")
    print("*****", token)

    if token is None or not token.startswith('Basic '):
        return False

    token = token.encode('utf-8', 'ignore')

    try:
        print("*****", token)
        service = resource.user_service
        g.current_user = service.getUserFromBasicToken(token, scope)

        return True
    except Exception as e:
        pass

    return False

def SecurityToken(resource, scope, request):

    token = request.headers.get("Authorization")

    if token is None:
        token = request.params.get('token', None)

        if token is None:

            return False

    token = token.encode('utf-8', 'ignore')

    try:
        service = resource.user_service
        g.current_user = service.getUserFromToken(token, scope)

        return True
    except Exception as e:
        pass

    return False

def SecurityApiKey(resource, scope, request):

    token = request.headers.get("Authorization")

    if token is None or not token.startswith('APIKEY '):

        token = request.params.get('apikey', None)

        if token is None:

            return False

        token = 'APIKEY ' + token

    token = token.encode('utf-8', 'ignore')

    try:
        service = resource.user_service
        g.current_user = service.getUserFromApikey(token, scope)

        return True
    except Exception as e:
        pass

    return False

def requires_no_auth(f):
    #@wraps(f)
    #def wrapper(*args, **kwargs):
    #    return _handle_exceptions(f, args, kwargs)
    #return wrapper
    f._auth = False
    #f._scope = []
    #f._security = []
    return f

def requires_auth(features=None):

    if isinstance(features, str):
        features = [features]
    __add_feature(features)

    def impl(f):
        f._auth = True
        f._scope = features
        f._security = [SecurityBasic, SecurityApiKey, SecurityToken]

        return f
        ###@wraps(f)
        ###def wrapper(resource, *args, **kwargs):
        ###
        ###    args = list(args)
        ###    args.insert(0, resource)
        ###
        ###    print("decodeing auth for wrapped function: %s" % f)
        ###    service = resource.user_service
        ###
        ###    # check the request parameters for auth tokens
        ###
        ###    token = request.args.get('token', None)
        ###    if token is not None:
        ###        bytes_token = (token).encode("utf-8")
        ###        return _requires_token_auth_impl(service, f, args, kwargs,
        ###            features, bytes_token)
        ###
        ###    token = request.args.get('apikey', None)
        ###    if token is not None:
        ###        bytes_token = ("APIKEY " + token).encode("utf-8")
        ###        return _requires_apikey_auth_impl(service, f, args, kwargs,
        ###            features, bytes_token)
        ###
        ###    # check therequest headers for auth tokens
        ###
        ###    try:
        ###        token = get_request_header(request, "Authorization")
        ###    except HttpException as e:
        ###        return httpError(401, str(e))
        ###
        ###    token = request.headers['Authorization']
        ###    bytes_token = token.encode('utf-8', 'ignore')
        ###    if token.startswith("Basic "):
        ###        return _requires_basic_auth_impl(service, f, args, kwargs,
        ###            features, bytes_token)
        ###    elif token.startswith("APIKEY "):
        ###        return _requires_apikey_auth_impl(service, f, args, kwargs,
        ###            features, bytes_token)
        ###    return _requires_token_auth_impl(service, f, args, kwargs,
        ###        features, bytes_token)
        ###
        ###return wrapper
    return impl

class DateTimeType(OpenApiParameter):
    def __init__(self):
        super(DateTimeType, self).__init__("integer")

        self.attrs["format"] = "date"

    def __call__(self, value):

        t = 0
        if value is not None:
            try:
                try:
                    t = int(value)
                except ValueError:
                    t = int(parse_iso_format(value).timestamp())
                return t
            except Exception as e:
                logging.exception("unable to parse (%r) : %s" % (value, e))
        raise Exception("Invalid datetime")

datetime_validator = DateTimeType()

def search_order_validator(s):
    # todo: support multiple fields

    if s.lower() == 'forest':
        return [Song.artist_key, Song.album, Song.title]

    if s in Song.fields() or s.lower() == "random":
        return s
    raise Exception("Invalid column name")

class UUIDValidator(object):

    def __init__(self):
        super()
        self.__name__ = self.__class__.__name__

    def __call__(self, uuid_string):
        try:
            val = UUID(uuid_string, version=4)
        except ValueError:
            return False

        if str(val) != uuid_string:
            raise Exception("Invalid uuid")

        return uuid_string

    def name(self):
        return self.__class__.__name__.replace("Validator", "")

    def mimetype(self):
        return "application/json"

    def type(self):
        return "string"

uuid_validator = UUIDValidator()
uuid_list_validator = ArrayValidator(uuid_validator)

def files_generator(fs, filepath, buffer_size=2048):

    with fs.open(filepath, "rb") as rb:
        buf = rb.read(buffer_size)
        while buf:
            yield buf
            buf = rb.read(buffer_size)

def files_generator_v2(stream, buffer_size=2048):

    try:
        buf = stream.read(buffer_size)
        while buf:
            yield buf
            buf = stream.read(buffer_size)
    finally:
        stream.close()

class ImageScaleType(OpenApiParameter):
    def __init__(self):
        super(ImageScaleType, self).__init__("string")
        self.enum(ImageScale.names())

    def __call__(self, value):

        index = ImageScale.fromName(value)
        if index == 0:
            raise Exception("invalid: %s" % value)
        return index



