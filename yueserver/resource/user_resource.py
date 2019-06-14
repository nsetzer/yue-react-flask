
"""
a resource for user management and authentication
"""
import logging

from flask import jsonify, render_template, g, request

from ..framework.web_resource import WebResource, \
    body, returns, get, post, put, delete, httpError, JsonValidator, \
    send_generator

from ..framework.openapi import curldoc

from .util import requires_auth, requires_no_auth

class UserLoginValidator(JsonValidator):

    def model(self):
        return {
            "email": {"type": "string", "required": True},
            "password": {"type": "string", "format": "password", "required": True},
        }

class UserTokenValidator(JsonValidator):

    def model(self):
        return {
            "token": {"type": "string", "required": True},
        }

class UserCreateValidator(JsonValidator):

    def model(self):
        return {
            "email": {"type": "string", "required": True},
            "password": {"type": "string", "format": "password", "required": True},
            "domain": {"type": "string", "required": True},
            "role": {"type": "string", "required": True},
        }

class UserPasswordValidator(JsonValidator):

    def model(self):
        return {
            "password": {"type": "string", "format": "password", "required": True},
        }

class UserResource(WebResource):
    """UserResource

    features:
        user_read   - user can read data
        user_write  - user can update their data
        user_create - user can create new users
        user_power  - user can retrieve information on other users
    """
    def __init__(self, app, user_service):
        super(UserResource, self).__init__("/api/user")

        self.app = app
        self.user_service = user_service

    @post("login")
    @requires_no_auth
    @body(UserLoginValidator())
    @returns([200, 400, 401])
    def login_user(self):

        token = self.user_service.loginUser(
            g.body["email"], g.body["password"])

        return jsonify(token=token)

    @post("token")
    @requires_no_auth
    @body(UserTokenValidator())
    @returns([200, 400, 401])
    def is_token_valid(self):

        token = g.body["token"]

        is_valid, reason = self.user_service.verifyToken(token)

        return jsonify(token_is_valid=is_valid,
                   reason=reason)

    @get("")
    @requires_auth("user_read")
    @returns([200, 401])
    def get_user(self):
        info = self.user_service.listUser(g.current_user['id'])
        return jsonify(result=info)

    @post("create")
    @requires_auth("user_create")
    @body(UserCreateValidator())
    @returns([200, 400, 401, 404])
    def create_user(self):
        """
        TODO: return 404 if domain/role is not found
        TODO: return 400 is user exists
        """
        incoming = request.get_json()

        user_id = user = self.user_service.createUser(
            g.body["email"],
            g.body["domain"],
            g.body["role"],
            g.body["password"]
        )

        return jsonify(id=user_id)

    @put("password")
    @requires_auth("user_write")
    @body(UserPasswordValidator())
    @returns([200, 401])
    def change_password(self):

        self.user_service.changeUserPassword(g.current_user,
            g.body['password'])

        return jsonify(result="OK")

    @get("list/domain/<domain>")
    @requires_auth("user_power")
    @returns([200, 401])
    def list_users(self, domain):
        """
        list all users for a given domain
        """

        user_info = self.user_service.listDomainUsers(domain)

        return jsonify(result=user_info)

    @get("list/user/<userId>")
    @requires_auth("user_power")
    @returns([200, 401])
    def list_user(self, userId):

        user_info = self.user_service.listUser(userId)

        return jsonify(result=user_info)


    @get('/api/doc')
    @requires_auth()
    def doc(self):

        go = curldoc(self.app, 'https://localhost:4200')
        return send_generator(go, 'doc.txt', attachment=False)


