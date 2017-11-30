
from functools import wraps
from flask import request, jsonify, g
from flask_cors import cross_origin
from sqlalchemy.exc import IntegrityError

from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired, BadSignature

import base64
from bcrypt import gensalt
from ..index import app, db, dbtables
from ..dao.user import UserDao

TWO_WEEKS = 1209600

def httpError(code, message):
    return jsonify(result=message), code

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
    except Exception as e:
        return httpError(400, str(e))

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
    except Excpetion as e:
        return httpError(401,
            "Authentication is required to access this resource")


def _requires_basic_auth_impl(f, args, kwargs, token):
    """
    basic auth enables easy testing

    example:
        curl -u username:password -X GET localhost:4200/api/user

    """
    email, password = parse_basic_token(token)

    user = UserDao(db, dbtables).findUserByEmailAndPassword(email, password)
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

        if "Authorization" not in request.headers:
            return httpError(401, "Authorization header not provided")

        token = request.headers['Authorization']

        bytes_token = token.encode('utf-8', 'ignore')
        if token.startswith("Basic "):
            return _requires_basic_auth_impl(f, args, kwargs, bytes_token)
        return _requires_token_auth_impl(f, args, kwargs, bytes_token)

    return decorated

def requires_no_auth(f):
    """
    endpoint decorator which handles unhandled exceptions
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        return _handle_exceptions(f, args, kwargs)
    return decorated




