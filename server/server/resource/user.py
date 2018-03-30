
from flask import jsonify, render_template, g

from server.framework.web_resource import WebResource, get, put, post, delete

class UserResource(WebResource):
    """docstring for UserResource"""
    def __init__(self, user_service):
        super(UserResource, self).__init__()

        self.user_service = user_service

    @get("/api/user")
    def get_user(self, app):
        return jsonify(result=get_user_info(g.current_user))

    @get("/api/user/login")
    def get_token(self, app):
        incoming = request.get_json()

        if not incoming:
            return jsonify(error="invalid request body"), 400
        if 'email' not in incoming:
            return jsonify(error="email not specified"), 400
        if 'password' not in incoming:
            return jsonify(error="password not specified"), 400

        # TODO: decompose email from user@domain/role
        # and set the domain and role correctly

        user = self.user_service.getUserByPassword( \
            incoming["email"], incoming["password"])

        if user:
            app.logger.info('%s logged in successfully', incoming["email"])
            return jsonify(token=generate_token(user))
        else:
            app.logger.warn('%s not found', incoming["email"])

        return jsonify(error="user not found"), 403