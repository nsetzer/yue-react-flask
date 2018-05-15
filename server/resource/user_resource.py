
import logging

from flask import jsonify, render_template, g, request

from ..framework.web_resource import WebResource, \
    body, get, post, put, delete, httpError

from .util import requires_auth

def login_validator(info):
    if 'email' not in info:
        return Exception("invalid request body")
    if 'password' not in info:
        return Exception("invalid request body")
    return info

class UserResource(WebResource):
    """UserResource

    features:
        user_read   - user can read data
        user_write  - user can update their data
        user_create - user can create new users
        user_power  - user can retrieve information on other users
    """
    def __init__(self, user_service):
        super(UserResource, self).__init__("/api/user")

        self.user_service = user_service

    @get("")
    @requires_auth("user_read")
    def get_user(self):
        info=self.user_service.listUser(g.current_user['id'])
        return jsonify(result=info)

    @post("login")
    @body(login_validator)
    def login_user(self):

        token = self.user_service.loginUser(
            g.body["email"], g.body["password"])

        return jsonify(token=token)

    @post("token")
    def is_token_valid(self):
        # TODO: is this endpoint still required?

        incoming = request.get_json()

        if not incoming:
            return httpError(400, "invalid request body")
        if 'token' not in incoming:
            return httpError(400, "token not specified")

        is_valid, reason = self.user_service.verifyToken(incoming["token"])

        return jsonify(token_is_valid=is_valid,
                   reason=reason)

    @post("create")
    @requires_auth("user_create")
    def create_user(self):
        incoming = request.get_json()
        # I think i could remove this try/catch block
        # trust that the framework will catch the exception and log it

        try:
            user_id = user = self.user_service.createUser(
                incoming["email"],
                incoming["domain"],
                incoming["role"],
                incoming["password"]
            )

        except Exception as e:
            logging.error("%s" % e)
            return httpError(400, "Unable to create user")

        return jsonify(id=user_id)

    @put("password")
    @requires_auth("user_write")
    def change_password(self):
        incoming = request.get_json()

        if not incoming:
            return httpError(400, "invalid request body")
        if 'password' not in incoming:
            return httpError(400, "password not specified")

        user = g.current_user

        self.user_service.changeUserPassword(user, incoming['password'])

        return jsonify(result="OK")

    @get("list/domain/<domain>")
    @requires_auth("user_power")
    def list_users(self, domain):

        user_info = self.user_service.listDomainUsers(domain)

        return jsonify(result=user_info)

    @get("list/user/<userId>")
    @requires_auth("user_power")
    def list_user(self, userId):

        user_info = self.user_service.listUser(userId)

        return jsonify(result=user_info)