
import os

from yueserver.framework2.server_core import Response, send_file

from yueserver.framework2.openapi import Resource, \
    get, put, post, delete, \
    header, param, body, timed, returns, \
    String, BinaryStreamOpenApiBody, JsonOpenApiBody, OpenApiParameter

from yueserver.framework2.security import requires_no_auth, requires_auth, \
    register_handler, register_security, ExceptionHandler

class HttpResource(Resource):
    def __init__(self):
        super(HttpResource, self).__init__()

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

    @get("/:path*")
    @header("Host", type_=String())
    @requires_no_auth
    def root(self, request):
        host = request.headers['Host']
        if host is not None:
            location = "https://%s/%s" % (host, request.args.path)
            headers = {
                "Location": location
            }
            response = Response(308, headers, None)
        else:
            response = Response(404, {}, None)
        return response