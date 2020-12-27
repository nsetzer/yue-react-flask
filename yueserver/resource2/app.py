
import os

from yueserver.framework2.server_core import Response, send_file

from yueserver.framework2.openapi import Resource, \
    get, put, post, delete, \
    header, param, body, timed, returns, \
    String, BinaryStreamOpenApiBody, JsonOpenApiBody, OpenApiParameter

from yueserver.framework2.security import requires_no_auth, requires_auth, \
    register_handler, register_security, ExceptionHandler



notfound = """
<!DOCTYPE html>
<meta charset="UTF-8">
<html lang="en">
<head>
<title>Not Found</title>
</head>
<body>
<div><center>404 Not Found</center></div>
</body>
</html>
"""

class AppResource(Resource):
    def __init__(self):
        super(AppResource, self).__init__()

        self.config = None
        self.db = None

    @get("/health")
    @requires_no_auth
    def health(self, request):
        """ return status information about the application
        """

        from yueserver.dao.health import server_health

        # showing stats on an un-authenticated endpoint seems risky
        health = self.db.health()
        del health['stats']

        result = {
            "status": "OK",
            "database": health,
            "server": server_health()
        }

        return Response(200, {}, {"result": result})

    @get("/robots.txt")
    @requires_no_auth
    def robots(self, request):
        headers = {"Content-Type": 'text/plain'}
        payload = b"User-agent: *\nDisallow: /\n"
        return Response(200, headers, payload)

    @get("/manifest.json")
    @requires_no_auth
    def manifest(self, request):
        keys = {
            "manifest_version": 2,
            "version": "0.0.0",
            "name": "yueapp",
        }
        return Response(200, {}, keys)

    @get("/static/:path*")
    @requires_no_auth
    def static(self, request):
        response = send_file(self.config.static_dir, request.args.path)
        response.headers['Cache-Control'] = 'max-age=31536000'
        return response

    @get("/.well-known/:path*")
    @requires_no_auth
    def well_known(self, request):
        """ return files from a well known directory

        support for Lets Encrypt certificates
        """
        base = os.path.join(os.getcwd(), ".well-known")
        return send_file(base, request.args.path)

    @get("/favicon.ico")
    @requires_no_auth
    def favicon(self, request):
        response = send_file(self.config.build_dir, "favicon.ico")
        response.headers['Cache-Control'] = 'max-age=31536000'
        return response

    @get("/:part/:path*")
    @requires_no_auth
    def root_one(self, request):
        if request.args.part not in {"u", "p", "login", "doc"}:
            return Response(404, {"Content-Type": "text/html"}, notfound)
        return send_file(self.config.build_dir, "index.html")

    @get("/:path*")
    @requires_no_auth
    def root(self, request):
        return send_file(self.config.build_dir, "index.html")