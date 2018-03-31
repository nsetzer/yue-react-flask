
from flask import jsonify, render_template, g

from server.framework.web_resource import WebResource

from .util import requires_auth

class UserResource(WebResource):
    """docstring for UserResource"""
    def __init__(self, user_service):
        super(UserResource, self).__init__()

        self.user_service = user_service


        self.register("/api/user", self.get_user, ['GET'])
        self.register("/api/user/login", self.get_token, ['POST'])
        self.register("/api/user/token", self.is_token_valid, ['POST'])
        self.register("/api/user/create", self.create_user, ['POST'])
        self.register("/api/user/password", self.change_user_password, ['PUT'])
        self.register("/api/user/list/domain/<domain>", self.list_users, ['GET'])
        self.register("/api/user/list/user/<userId>", self.list_user, ['GET'])

    def get_user(self, app):
        return jsonify(result=get_user_info(g.current_user))

    def get_token(self, app):
        incoming = request.get_json()

        if not incoming:
            return jsonify(error="invalid request body"), 400
        if 'email' not in incoming:
            return jsonify(error="email not specified"), 400
        if 'password' not in incoming:
            return jsonify(error="password not specified"), 400

        token = self.user_service.loginUser(
            incoming["email"], incoming["password"])

        return jsonify(token=token)

    def is_token_valid(app):

        incoming = request.get_json()

        if not incoming:
            return jsonify(error="invalid request body"), 400
        if 'token' not in incoming:
            return jsonify(error="token not specified"), 400

        is_valid, reason = self.user_service.verifyToken(incoming["token"])

        return jsonify(token_is_valid=is_valid,
                   reason=reason)

    def create_user(app):
        incoming = request.get_json()

        try:
            user_id = user = self.user_service.createUser(
                incoming["email"],
                incoming["domain"],
                incoming["role"],
                incoming["password"]
            )

        except:
            return jsonify(message="Unable to create user"), 409

        return jsonify(
            id=user_id,
        )

    def change_user_password(app):
        incoming = request.get_json()

        if not incoming:
            return jsonify(error="invalid request body"), 400
        if 'password' not in incoming:
            return jsonify(error="password not specified"), 400

        user = g.current_user

        self.user_service.changeUserPassword(user, incoming['password'])

        return jsonify(result="OK")

    def list_users(app, domainName):

        user_info = self.user_service.listDomainUsers(domainName)

        return jsonify(result=user_info)

    def list_user(app, userId):

        user_info = self.user_service.listUser(userId)

        return jsonify(result=user_info)