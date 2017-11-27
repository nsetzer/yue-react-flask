
from functools import wraps
from flask import request, jsonify, g
from flask_cors import cross_origin
from sqlalchemy.exc import IntegrityError

from ..dao.library import Song, Library

from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired, BadSignature

import base64
from bcrypt import gensalt
from ..index import app, db

TWO_WEEKS = 1209600

def generate_basic_token(username, password):
    """convert a username and possword into a basic token"""
    return "Basic " + base64.b64encode(username + ":" + password)

def parse_basic_token(token):
    """return the username and password given a token"""
    if not token.startswith("Basic "):
        raise Exception("Invalid Basic Token")
    return base64.b64decode(token[6:]).split(":")

def generate_token(user, expiration=TWO_WEEKS):
    s = Serializer(app.config['SECRET_KEY'], expires_in=expiration)
    token = s.dumps({
        'id': user.id,
        'email': user.email,
        'domain_id': user.domain_id,
        'role_id': user.role_id,
    }).decode('utf-8')
    return token

def verify_token(token):
    s = Serializer(app.config['SECRET_KEY'])
    try:
        data = s.loads(token)
    except (BadSignature, SignatureExpired):
        return None
    return data

def _requires_token_auth_impl(f, args, kwargs, token):
    """
    token based authentication for client side state management

    example:
        curl -H "Authorization: <token>" -X GET localhost:4200/api/user

    """
    user_data = verify_token(token)

    if user_data:
        # token based auth does not require a db lookup to verify the user
        # all information is contained in the token
        # user = User.get_user_with_email(user_data['email'])
        g.current_user = user_data
        g.library = Library(user_data['id'], user_data['domain_id'])
        return f(*args, **kwargs)

    return jsonify(
        message="Authentication is required to access this resource"), 401

def _requires_basic_auth_impl(f, args, kwargs, token):
    """
    basic auth enables easy testing

    example:
        curl -u username:password -X GET localhost:4200/api/user

    """
    email, password = parse_basic_token(token)

    user = User.get_user_with_email_and_password(email, password)
    if user:
        # basic auth requires a db lookup to validate the user
        # store the user information in the same way as the token auth
        g.current_user = user.as_dict()
        return f(*args, **kwargs)

    return jsonify(message="failed to authenticate user %s" % email), 401

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):

        if "Authorization" not in request.headers:
            return jsonify(message="Authorization header not provided"), 401

        token = request.headers['Authorization']

        string_token = token.encode('ascii', 'ignore')
        if token.startswith("Basic "):
            return _requires_basic_auth_impl(f, args, kwargs, string_token)
        return _requires_token_auth_impl(f, args, kwargs, string_token)

    return decorated




