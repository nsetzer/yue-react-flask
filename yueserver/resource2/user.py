
# curl -k -v -L -X POST -H "Content-Type: application/json" --data-binary '{"email": "admin", "password": "admin"}' https://localhost/api/user/login

import os

from yueserver.framework2.server_core import Response, send_file

from yueserver.framework2.openapi import Resource, \
    get, put, post, delete, \
    header, param, body, timed, returns, \
    String, Integer, URI, \
    BinaryStreamOpenApiBody, JsonOpenApiBody, OpenApiParameter, \
    RegisteredEndpoint, OpenApi, curldoc


from yueserver.framework2.security import requires_no_auth, requires_auth, \
    register_handler, register_security, ExceptionHandler

class UserLoginOpenApiBody(JsonOpenApiBody):

    def model(self):
        return {
            "email": {"type": "string", "required": True},
            "password": {"type": "string", "format": "password", "required": True},
        }

class UserTokenOpenApiBody(JsonOpenApiBody):

    def model(self):
        return {
            "token": {"type": "string", "required": True},
        }

class UserCreateOpenApiBody(JsonOpenApiBody):

    def model(self):
        return {
            "email": {"type": "string", "required": True},
            "password": {"type": "string", "format": "password", "required": True},
            "domain": {"type": "string", "required": True},
            "role": {"type": "string", "required": True},
        }

class UserPasswordOpenApiBody(JsonOpenApiBody):

    def model(self):
        return {
            "password": {"type": "string", "format": "password", "required": True},
        }

class XTokenOpenApiBody(JsonOpenApiBody):

    def model(self):

        model = {
            "X-TOKEN": {"type": "string"}
        }

        return model

class TokenOpenApiBody(JsonOpenApiBody):

    def model(self):

        model = {
            "result": XTokenOpenApiBody()
        }

        return model

class UserResource(Resource):
    def __init__(self):
        super(UserResource, self).__init__()

        self.user_service = None
        self.app_endpoints = []

    @post("/api/user/login")
    @requires_no_auth
    @body(UserLoginOpenApiBody())
    @returns([200, 400, 401])
    def login_user(self, request):

        token = self.user_service.loginUser(
            request.body["email"], request.body["password"])

        return Response(200, {}, {"token": token})

    @post("/api/user/token")
    @requires_no_auth
    @body(UserTokenOpenApiBody())
    @returns([200, 400, 401])
    def is_token_valid(self, request):

        token = request.body["token"]

        is_valid, reason = self.user_service.verifyToken(token)

        res = {
            "token_is_valid": is_valid,
            "reason": reason
        }
        return Response(200, {}, res)

    @get("/api/user")
    @requires_auth("user_read")
    @returns([200, 401])
    def get_user(self, request):
        info = self.user_service.listUser(request.current_user['id'])
        return Response(200, {}, {'result': info})

    #@get("/api/user/token")
    #@param("expiry", type_=Integer().default(2 * 60 * 60))
    #@requires_auth("user_read")
    #@returns({200: TokenOpenApiBody()})
    #def get_uuid_token(self, request):
    #    token = self.user_service.generateUUIDToken(
    #        request.current_user, request.query.expiry)
    #    return Response(200, {}, {'result': {"X-TOKEN": token}})

    @post("/api/user/create")
    @requires_auth("user_create")
    @body(UserCreateOpenApiBody())
    @returns([200, 400, 401, 404])
    def create_user(self, request):
        """
        TODO: return 404 if domain/role is not found
        TODO: return 400 is user exists
        """

        user_id = user = self.user_service.createUser(
            request.body["email"],
            request.body["domain"],
            request.body["role"],
            request.body["password"]
        )

        return jsonify(id=user_id)
        return Response(200, {}, {'id': user_id})

    @put("/api/user/password")
    @requires_auth("user_write")
    @body(UserPasswordOpenApiBody())
    @returns([200, 401])
    def change_password(self, request):

        self.user_service.changeUserPassword(request.current_user,
            request.body['password'])

        return Response(200, {}, {'result': 'OK'})

    @get("/api/user/list/domain/:domain")
    @requires_auth("user_power")
    @returns([200, 401])
    def list_users(self, request):
        """
        list all users for a given domain
        """

        user_info = self.user_service.listDomainUsers(request.args.domain)

        return Response(200, {}, {'result': user_info})

    @get("/api/user/list/user/:userId")
    @requires_auth("user_power")
    @returns([200, 401])
    def list_user(self, request):

        user_info = self.user_service.listUser(request.args.userId)

        return Response(200, {}, {'result': user_info})

    @get('/api/doc')
    @param("hostname", type_=URI().default(""))
    @requires_auth()
    @returns([200, 401])
    def doc(self, request):
        """ construct curl documentation for endpoints

        hostname: the hostname to use in examples
            if an empty string, the request url will be used
        """
        doc = "".join(list(curldoc(self.app_endpoints, request.query.hostname)))

        return Response(200, {"Content-Type": "text/plain"}, doc.encode("utf-8"))

    @get('/api/doc.js')
    @param("hostname", type_=URI().default(""))
    @requires_auth()
    @returns([200])
    def doc_js(self, request):
        """ construct curl documentation for endpoints

        hostname: the hostname to use in examples
            if an empty string, the request url will be used
        """

        api = OpenApi(self.app_endpoints)
        api.license("MIT", "https://mit-license.org/")
        api.contact(None, "nsetzer@noreply.github.com")
        api.version("0.0.0.0")
        api.title("YueApp")
        api.description("YueApp API Doc")
        api.servers([{"url": "https://%s" % request.query.hostname}])

        return Response(200, {"Content-Type": "application/json"}, api.jsons().encode("utf-8"))
