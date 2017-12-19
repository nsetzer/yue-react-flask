
from flask import request, jsonify, g
from flask_cors import cross_origin
from sqlalchemy.exc import IntegrityError

from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired, BadSignature

import base64
from bcrypt import gensalt
from ..index import app, db, dbtables

from ..dao.user import UserDao

from .util import requires_auth, requires_no_auth, verify_token, generate_token

userDao = UserDao(db, dbtables)

@app.route("/api/user", methods=["GET"])
@requires_auth
def get_user():
    user = g.current_user
    user['features'] = userDao.listFeaturesByName(user['role_id'])
    user['apikey'] = userDao.getUserApiKey(user['id'])
    return jsonify(result=user)

@app.route("/api/user", methods=["POST"])
def create_user():
    incoming = request.get_json()

    try:
        user_id = userDao.createUser(
            incoming["email"],
            app.config["DEFAULT_DOMAIN"],
            app.config["DEFAULT_ROLE"],
            incoming["password"]
        )

    except:
        return jsonify(message="User with that email already exists"), 409

    new_user = userDao.findUserByEmail(incoming["email"])

    return jsonify(
        id=user_id,
        token=generate_token(new_user)
    )

@app.route("/api/user/login", methods=["POST"])
def get_token():
    incoming = request.get_json()

    if not incoming:
        return jsonify(error="invalid request body"), 400
    if 'email' not in incoming:
        return jsonify(error="email not specified"), 400
    if 'password' not in incoming:
        return jsonify(error="password not specified"), 400

    # TODO: decompose email from user@domain/role
    # and set the domain and role correctly

    user = userDao.findUserByEmailAndPassword(
        incoming["email"], incoming["password"])
    if user:
        app.logger.info('%s logged in successfully', incoming["email"])
        return jsonify(token=generate_token(user))
    else:
        app.logger.warn('%s not found', incoming["email"])
    return jsonify(error="user not found"), 403

@app.route("/api/user/token", methods=["POST"])
@cross_origin(supports_credentials=True)
@requires_no_auth
def is_token_valid():
    incoming = request.get_json()

    is_valid = False
    reason = ""
    try:
        if verify_token(incoming["token"]):
            is_valid = True
            reason = "OK"
    except BadSignature:
        is_valid = False
        reason = "Bad Signature"
    except SignatureExpired:
        is_valid = False
        reason = "Expired Signature"

    return jsonify(token_is_valid=is_valid,
                   reason=reason)
