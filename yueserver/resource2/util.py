

import time
import logging

from uuid import UUID

from ..framework2.server import Response

from ..dao.util import parse_iso_format
from ..dao.library import Song

from ..framework2.openapi import ArrayOpenApiBody, OpenApiParameter

from ..service.transcode_service import ImageScale

from ..dao.exception import BackendException
from ..service.exception import ServiceException

from yueserver.framework2.security import requires_no_auth, requires_auth, \
    register_handler, register_security, ExceptionHandler

class _FileNotFoundError(ExceptionHandler):

    type = FileNotFoundError

    def handle(self, resource, request, ex):

        reason = "File Not Found Error: "

        if request.current_user is not None:
            reason = "%s (current user: %s): " % (
                reason, request.current_user['email'])

        logging.exception(reason)

        return Response(404, {"error": reason + str(ex)})

class _BackendException(ExceptionHandler):

    type = BackendException

    def handle(self, resource, request, ex):

        reason = "Unhandled Backend Exception: "

        if request.current_user is not None:
            reason = "%s (current user: %s): " % (
                reason, request.current_user['email'])

        logging.exception(reason)

        return Response(ex.HTTP_STATUS, {"error": reason + str(ex)})

class _ServiceException(ExceptionHandler):

    type = ServiceException

    def handle(self, resource, request, ex):

        reason = "Unhandled Service Exception: "

        if request.current_user is not None:
            reason = "%s (current user: %s): " % (
                reason, request.current_user['email'])

        logging.exception(reason)

        return Response(ex.HTTP_STATUS, {"error": reason + str(ex)})

class _Exception(ExceptionHandler):

    type = Exception

    def handle(self, resource, request, ex):

        reason = "Unhandled Exception: "

        if request.current_user is not None:
            reason = "%s (current user: %s): " % (
                reason, request.current_user['email'])

        logging.exception(reason)

        return Response(500, {"error": reason + str(ex)})

def SecurityBasic(resource, scope, query, headers):
    token = headers.get(b"Authorization")

    if token is None or not token.startswith(b'Basic '):
        return None

    #token = token.encode('utf-8', 'ignore')

    try:
        service = resource.user_service
        return service.getUserFromBasicToken(token, scope)
    except Exception as e:
        logging.exception("Basic Authentication Failed")

    return None

def SecurityToken(resource, scope, query, headers):

    token = headers.get(b"Authorization")

    if not token:
        if "token" not in query or not query['token']:
            return None

        token = query['token'][0].encode('utf-8', 'ignore')

    if token.startswith(b"APIKEY "):
        return None

    try:
        service = resource.user_service
        return service.getUserFromToken(token, scope)
    except Exception as e:
        logging.exception("token error: %s" % e)

    return None

def SecurityApiKey(resource, scope, query, headers):

    token = headers.get(b"Authorization")

    if token is None or not token.startswith(b'APIKEY '):

        token = query.get('apikey', None)

        if token is None:
            return None

        # convert to bytes
        token = ('APIKEY ' + token).encode('utf-8', 'ignore')

    try:
        service = resource.user_service
        return service.getUserFromApikey(token, scope)

    except Exception as e:
        pass

    return None

def SecurityUUIDToken(resource, scope, query, headers):

    token = headers.get("X-TOKEN")

    if token is None:
        return None

    try:
        service = resource.user_service
        return service.getUserFromUUIDToken(token, scope)
    except Exception as e:
        pass

    return None

def register_handlers():

    register_handler(_FileNotFoundError())
    register_handler(_BackendException())
    register_handler(_ServiceException())
    register_handler(_Exception())

    register_security(SecurityBasic)
    register_security(SecurityToken)
    register_security(SecurityApiKey)
    register_security(SecurityUUIDToken)

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

        if not isinstance(uuid_string, str):
            raise Exception("Invalid uuid")

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
