
"""
Helper functions for implementing Web Resources
"""
import logging
from functools import wraps
from flask import after_this_request, request, jsonify, g
import traceback
import time
from uuid import UUID

from ..dao.util import parse_iso_format
from ..dao.library import Song
from ..dao.exception import BackendException

from ..service.exception import ServiceException

from ..framework.web_resource import httpError, ArrayOpenApiBody, OpenApiParameter
from ..service.transcode_service import ImageScale

class HttpException(Exception):
    """docstring for HttpException"""
    def __init__(self, message, code=400):
        super(HttpException, self).__init__(message)
        self.status = code

class _FileNotFoundError(object):

    type = FileNotFoundError

    def handle(self, ex):

        reason = "File Not Found Error: "

        if hasattr(g, 'current_user') and g.current_user is not None:
            reason = "File Not Found (current user: %s): " % \
                g.current_user['email']

        logging.exception(reason)

        return httpError(404, reason + str(ex))

class _BackendException(object):

    type = BackendException

    def handle(self, ex):

        reason = "Unhandled Backend Exception: "

        if hasattr(g, 'current_user') and g.current_user is not None:
            reason = "Unhandled Backend Exception (current user: %s): " % \
                g.current_user['email']

        logging.exception(reason)

        return httpError(ex.HTTP_STATUS, reason + str(ex))

class _ServiceException(object):

    type = ServiceException

    def handle(self, ex):

        reason = "Unhandled Service Exception: "

        if hasattr(g, 'current_user') and g.current_user is not None:
            reason = "Unhandled Service Exception (current user: %s): " % \
                g.current_user['email']

        logging.exception(reason)

        return httpError(ex.HTTP_STATUS, reason + str(ex))

class _Exception(object):

    type = Exception

    def handle(self, ex):

        reason = "Unhandled Exception: "

        if hasattr(g, 'current_user') and g.current_user is not None:
            reason = "Unhandled Exception (current user: %s): " % \
                g.current_user['email']

        logging.exception(reason)

        return httpError(500, reason + str(ex))

_handlers = [
    _FileNotFoundError(),
    _BackendException(),
    _BackendException(),
    _ServiceException(),
    _Exception()
]

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

def SecurityBasic(resource, scope, request):

    token = request.headers.get("Authorization")

    if token is None or not token.startswith('Basic '):
        return False

    token = token.encode('utf-8', 'ignore')

    try:
        service = resource.user_service
        g.current_user = service.getUserFromBasicToken(token, scope)

        return True
    except Exception as e:
        logging.exception("Basic Authentication Failed")

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
        logging.exception("token error: %s" % e)

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

def SecurityUUIDToken(resource, scope, request):

    token = request.headers.get("X-TOKEN")

    if token is None:
        return False

    try:
        service = resource.user_service
        g.current_user = service.getUserFromUUIDToken(token, scope)

        return True
    except Exception as e:
        pass

    return False

def requires_no_auth(f):
    f._auth = False
    f._handlers = _handlers
    return f

def requires_auth(features=None):

    if features is None:
        features = []
    elif isinstance(features, str):
        features = [features]
    __add_feature(features)

    def impl(f):
        f._auth = True
        f._scope = features
        f._security = [
            SecurityBasic,
            SecurityApiKey,
            SecurityToken,
            SecurityUUIDToken
        ]
        f._handlers = _handlers

        return f
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

def search_order_validator(s):
    # todo: support multiple fields

    if s.lower() == 'forest':
        return [Song.artist_key, Song.album, Song.title]

    if s in Song.fields() or s.lower() == "random":
        return s
    raise Exception("Invalid column name")

class UUIDOpenApiBody(object):

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
        return self.__class__.__name__.replace("OpenApiBody", "")

    def mimetype(self):
        return "application/json"

    def type(self):
        return "string"

uuid_validator = UUIDOpenApiBody()
uuid_list_validator = ArrayOpenApiBody(uuid_validator)

def files_generator(fs, filepath, buffer_size=2048):

    with fs.open(filepath, "rb") as rb:
        buf = rb.read(buffer_size)
        while buf:
            yield buf
            buf = rb.read(buffer_size)

def files_generator_v2(stream, buffer_size=2048):

    count = 0
    success = False
    start = time.time()
    try:
        buf = stream.read(buffer_size)
        while buf:
            count += len(buf)
            yield buf
            buf = stream.read(buffer_size)
        success = True
    except BaseException:
        logging.exception("exception while streaming data")
        raise
    finally:
        duration = (time.time() - start)
        stream.close()
        if success:
            logging.info("successfully transfered stream (%d bytes in %.3f seconds)", count, duration)
        else:
            logging.error("failed to transfered stream (%d bytes in %.3f seconds)", count, duration)

class ImageScaleType(OpenApiParameter):
    def __init__(self):
        super(ImageScaleType, self).__init__("string")
        self.enum(ImageScale.names())

    def __call__(self, value):

        index = ImageScale.fromName(value)
        if index == 0:
            raise Exception("invalid: %s" % value)
        return index



