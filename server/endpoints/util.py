
from functools import wraps
from flask import after_this_request, request, jsonify, g
from flask_cors import cross_origin
from sqlalchemy.exc import IntegrityError

from io import BytesIO
import gzip

from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired, BadSignature

import base64
from bcrypt import gensalt
from ..index import app, db, dbtables
from ..dao.user import UserDao

TWO_WEEKS = 1209600

import traceback

_userDao = UserDao(db, dbtables)

class HttpException(Exception):
    """docstring for HttpException"""
    def __init__(self, message, code=400):
        super(HttpException, self).__init__(message)
        self.status = code

def httpError(code, message):
    return jsonify(error=message), code

def get_request_header(req, header):
    if header in request.headers:
        return request.headers[header]
    elif header.lower() not in request.headers:
        return request.headers[header.lower()]
    else:
        print(request.headers)
        raise HttpException("%s header not provided" % header, 401)

def generate_basic_token(username, password):
    """convert a username and possword into a basic token"""
    enc = (username + ":" + password).encode("utf-8", "ignore")
    return b"Basic " + base64.b64encode(enc)

def parse_basic_token(token):
    """return the username and password given a token"""
    if not token.startswith(b"Basic "):
        raise Exception("Invalid Basic Token")
    return base64.b64decode(token[6:]).decode("utf-8").split(":")

def generate_token(user, expiration=TWO_WEEKS):
    s = Serializer(app.config['SECRET_KEY'], expires_in=expiration)
    token = s.dumps({
        'id': user['id'],
        'email': user['email'],
        'domain_id': user['domain_id'],
        'role_id': user['role_id'],
    }).decode('utf-8')
    return token

def verify_token(token):
    s = Serializer(app.config['SECRET_KEY'])

    return s.loads(token)

def _handle_exceptions(f, args, kwargs):
    try:
        return f(*args, **kwargs)
    except HttpException as e:
        traceback.print_exc()
        return httpError(e.status, str(e))
    except Exception as e:
        traceback.print_exc()
        return httpError(400, "Unhandled Exception: " + str(e))

def _requires_token_auth_impl(f, args, kwargs, token):
    """
    token based authentication for client side state management

    example:
        curl -H "Authorization: <token>" -X GET localhost:4200/api/user

    """

    try:
        user_data = verify_token(token)

        g.current_user = user_data

        return _handle_exceptions(f, args, kwargs)

    except BadSignature:
        return httpError(401,
            "Bad token encountered")
    except SignatureExpired:
        return httpError(401,
            "Token has expired")
    except Exception as e:
        return httpError(401,
            "Authentication is required to access this resource")

def _requires_basic_auth_impl(f, args, kwargs, token):
    """
    basic auth enables easy testing

    example:
        curl -u username:password -X GET localhost:4200/api/user

    """
    # TODO: decompose email from user@domain/role
    # and set the domain and role correctly

    email, password = parse_basic_token(token)

    user = _userDao.findUserByEmailAndPassword(email, password)
    if user:
        # basic auth requires a db lookup to validate the user
        # store the user information in the same way as the token auth
        g.current_user = {
            "id": user.id,
            "email": user.email,
            "domain_id": user.domain_id,
            "role_id": user.role_id
        }
        return _handle_exceptions(f, args, kwargs)

    return httpError(401, "failed to authenticate user %s" % email)

def requires_auth(f):
    """
    endpoint decorator requiring authorization,
    and handles unhandled exceptions
    """
    @wraps(f)
    def decorated(*args, **kwargs):

        try:
            token = get_request_header(request, "Authorization")
        except HttpException as e:
            return httpError(401, str(e))

        bytes_token = token.encode('utf-8', 'ignore')
        if token.startswith("Basic "):
            return _requires_basic_auth_impl(f, args, kwargs, bytes_token)
        return _requires_token_auth_impl(f, args, kwargs, bytes_token)

    return decorated

def requires_auth_role(role=None):

    def impl(f):

        @wraps(f)
        def decorated(*args, **kwargs):

            try:
                token = get_request_header(request, "Authorization")
            except HttpException as e:
                return httpError(401, str(e))

            token = request.headers['Authorization']
            # TODO: check role for current user

            bytes_token = token.encode('utf-8', 'ignore')
            if token.startswith("Basic "):
                return _requires_basic_auth_impl(f, args, kwargs, bytes_token)
            return _requires_token_auth_impl(f, args, kwargs, bytes_token)
        return decorated
    return impl

def requires_no_auth(f):
    """
    endpoint decorator which handles unhandled exceptions
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        return _handle_exceptions(f, args, kwargs)
    return decorated

def compressed(f):
    """
    compress the output using gzip if the client supports it.
    """
    @wraps(f)
    def view_func(*args, **kwargs):
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

    return view_func




