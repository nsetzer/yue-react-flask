import re
import http.server
import socketserver
import json
import os
import sys
import io
import gzip
import ssl
from urllib.parse import urlparse, unquote
import mimetypes
from threading import Thread
import logging

class RequestHandler(http.server.BaseHTTPRequestHandler):

    BUFFER_RX_SIZE = 16384
    BUFFER_TX_SIZE = 16384

    def __init__(self, router, *args):
        self.router = router
        super(RequestHandler, self).__init__(*args)
        self.protocol_version = 'HTTP/1.1'

    def _handleMethod(self, method):
        url = urlparse(unquote(self.path))
        result = self.router.getRoute(method, url.path)
        if result:
            # TODO: try-block around user code
            resource, callback, matches = result

            parts = url.query.split("&")
            self.query = {k: [v] for k,v in part.split("=") for part in parts if '=' in part}

            try:
                response = callback(self, self.path, matches)
            except Exception as e:
                logging.exception("unhandled user exception")
                response = None

            if not response:
                response = JsonResponse({'error':
                    'endpoint failed to return a response'}, 500)

        else:
            response = JsonResponse({'error': 'path not found'}, 404)

        try:
            self.send_response(response.status_code)
            for k, v in response.headers.items():
                self.send_header(k, v)
            self.end_headers()
            if hasattr(response.payload, "read"):
                buf = response.payload.read(RequestHandler.BUFFER_TX_SIZE)
                while buf:
                    self.wfile.write(buf)
                    buf = response.payload.read(RequestHandler.BUFFER_TX_SIZE)
            else:
                self.wfile.write(response.payload)
        except ConnectionAbortedError as e:
            sys.stderr.write("%s aborted\n" % url.path)
        except BrokenPipeError as e:
            sys.stderr.write("%s aborted\n" % url.path)
        finally:
            if hasattr(response.payload, "close"):
                response.payload.close()

    def do_DELETE(self):
        return self._handleMethod("DELETE")

    def do_GET(self):
        return self._handleMethod("GET")

    def do_POST(self):
        return self._handleMethod("POST")

    def do_PUT(self):
        return self._handleMethod("PUT")

    def json(self):
        length = int(self.headers['content-length'])
        binary_data = self.rfile.read(length)
        obj = json.loads(binary_data.decode('utf-8'))
        return obj

    def json(self):
        data = self.get_file().read()
        print("data", data)
        return json.loads(data.decode('utf-8'))

    def get_file(self):

        # curl -v -X POST -H "Content-Type: application/json" -d '{"abc": "def"}' localhost:1234/upload
        # curl -v -X POST -F 'upload=@test' localhost:1234/upload
        # curl -v -X POST --data-binary '@test' localhost:1234/upload

        return UploadFile(self.headers, self.rfile)

    def accepts_gzip(self):
        return "gzip" in self.headers['Accept-Encoding'].lower()

class TcpServer(socketserver.TCPServer):
    allow_reuse_address = True

    def __init__(self, addr, factory):
        super().__init__(addr, factory)
        self.certfile = None
        self.keyfile = None

    def setCert(self, certfile=None, keyfile=None):
        self.certfile = certfile
        self.keyfile = keyfile

    def getProtocol(self):
        return "http" if self.certfile is None and self.keyfile is None else "https"

    def get_request(self):
        socket, fromaddr = self.socket.accept()

        if self.certfile is not None and self.keyfile is not None:
            socket = ssl.wrap_socket(
                socket,
                server_side=True,
                certfile=self.certfile,
                keyfile=self.keyfile,
                ssl_version=ssl.PROTOCOL_TLS
            )

        return socket, fromaddr

class Server(object):
    def __init__(self, host, port):
        super(Server, self).__init__()
        self.host = host
        self.port = port
        self.certfile = None
        self.keyfile = None

    def setCert(self, certfile=None, keyfile=None):
        self.certfile = certfile
        self.keyfile = keyfile

    def buildRouter(self):
        raise NotImplementedError()

    def run(self):
        addr = (self.host, self.port)
        router = self.buildRouter()
        # construct a factory for a RequestHandler that is aware
        # of the current router.
        factory = lambda *args: RequestHandler(router, *args)
        with TcpServer(addr, factory) as httpd:

            httpd.setCert(self.certfile, self.keyfile)

            for endpoint in router.endpoints:
                print("%-8s %s" % endpoint)

            proto = httpd.getProtocol()

            print(f"Daedalus Server listening on {proto}://{self.host}:{self.port}. Not for production use!")

            httpd.serve_forever()

class ThreadedServer(Server):
    def __init__(self, host, port, router):
        super(ThreadedServer, self).__init__(host, port)
        self.router = router

    def buildRouter(self):
        return self.router

class _ServerThread(Thread):
    def __init__(self, router, host, port, certificate=None, privatekey=None, password=None):
        super(_ServerThread, self).__init__()
        self.daemon = True

        self.server = ThreadedServer(host, port, router)
        if certificate and privatekey:
            self.server.setCert(certificate, privatekey)

    def run(self):

        self.server.run()

class Site(object):
    def __init__(self, host):
        super(Site, self).__init__()
        self.host = host
        self.threads = []

    def listenTLS(self, router, port, certificate, privatekey, password):
        thread = _ServerThread(router, self.host, port, certificate, privatekey, password)
        self.threads.append(thread)

    def listenTCP(self, router, port):
        thread = _ServerThread(router, self.host, port)
        self.threads.append(thread)

    def start(self):
        for thread in self.threads:
            thread.start()

    def join(self):
        for thread in self.threads:
            thread.join()

def main():  # pragma: no cover

    class DemoResource(Resource):

        def endpoints(self):
            return [
                ("GET", "/greet", self.greet)
            ]

        def greet(self, request, location, matches):
            name = request.query.get("name", "World")
            return JsonResponse({"response": f"Hello {name}!"})

    class DemoServer(Server):

        def buildRouter(self):
            router = Router()

            router.registerEndpoints(DemoResource().endpoints())

            return router

    server = DemoServer("0.0.0.0", 80)

    server.run()

if __name__ == '__main__':  # pragma: no cover
    main()
