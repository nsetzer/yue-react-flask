
# curl --compressed http://example.com/
# curl -header "Transfer-Encoding: chunked"  http://example.com/


# head -c 128 /dev/urandom > test.bin
# echo test.bin > gzip > test.bin.gz

# curl -v -X POST -H "Content-Type: application/json" -d '{"abc": "def"}' localhost:1234/upload
# curl -v -X POST -F 'upload=@test' localhost:1234/upload
# curl -v -X POST --data-binary '@test.bin' localhost:1234/upload
# curl -v -X POST -H'Content-Encoding: gzip' --data-binary '@test.bin.gz' localhost:1234/upload
# curl -v -X POST --data-binary '@test.bin' -header "Transfer-Encoding: chunked" localhost:1234/upload


import os
import sys

import io
import socket
import threading
import socketserver
import select
import gzip
import logging
import argparse
import ssl
import time
import inspect
import gzip
import json
from datetime import datetime

from collections import defaultdict

from urllib.parse import urlparse, unquote, parse_qs
from http.client import responses

from .server_core import readword, readline, Namespace, \
    SocketFile, SocketWriteFile, \
    CaseInsensitiveDict, UploadChunkedFile, UploadMultiPartFile, \
    Response, \
    TLSSocketClosed, ProtocolError


class Protocol(object):

    def handshake(self, request, sock):
        if hasattr(sock, 'do_handshake'):
            try:
                sock.do_handshake()
            except ssl.SSLError as err:
                sock.close()
                host, port = self.client_address
                logging.error("%016X %s:%d %s" % (threading.get_ident(), host, port, err))
                return

    def prepare(self, request):

        request.method = b"n/a"
        request.transport_protocol = b"n/a"
        request.path = b"n/a"
        request.path_safe = b"n/a"

        request.headers = CaseInsensitiveDict()

        request.body = None

        request.location = None

        request.rfile = SocketFile(request.request)

        request.request.settimeout(30.0)

        request.t0 = time.perf_counter()

    def parse_headers(self, request):

        # first line contains method, path, protocol
        request.method = readword(request.rfile, 16)

        if request.method not in (b'OPTIONS', b'GET', b'POST', b'PUT', b'DELETE'):
            raise ProtocolError("invalid method")

        request.path = readword(request.rfile, 4096)
        request.path_safe = request.path

        if not request.path:
            raise ProtocolError("invalid path")

        request.transport_protocol = readline(request.rfile, 16)

        if request.transport_protocol not in (b'HTTP/1.0', b'HTTP/1.1'):
            raise ProtocolError("invalid protocol")

        if b'<' in request.path:
            raise ProtocolError("Suspicious Path")

        if request.path.startswith(b"/vendor") or \
           request.path.startswith(b"/api/jsonws") or \
           request.path.startswith(b"/solr") or \
           request.path.startswith(b"/console") or \
           request.path.startswith(b"/wp-content") or \
           request.path.startswith(b"/webmail") or \
           request.path.startswith(b"/menu") or \
           request.path.startswith(b"/base") or \
           request.path.startswith(b"/.svn") or \
           request.path.startswith(b"/rest") or \
           request.path.startswith(b"/iwc") or \
           request.path.startswith(b"/IMS-AA-IDP") or \
           request.path.startswith(b"/owa") or \
           request.path.startswith(b"/streaming") or \
           request.path.startswith(b"/stalker_portal") or \
           request.path.startswith(b"/client_area") or \
           request.path.startswith(b"/index.php"):
            raise ProtocolError("Suspicious Path")

        if request.path == b"/?XDEBUG_SESSION_START=phpstorm" or \
           request.path == b"/c/version.js" or \
           request.path == b"/system_api.php":
            raise ProtocolError("Suspicious Path")

        url = urlparse(request.path.decode("utf-8"))

        #raw_query_args = [unquote(part).split('=', 1) for part in url.query.split("&") if part]
        #print(raw_query_args)
        #query = defaultdict(list)
        #for k, v in raw_query_args:
        #    # TODO: require unquote of rhs
        #    if v.startswith("\""):
        #        try:
        #            v = json.loads(v)
        #        except Exception as e:
        #            print(e)
        #            pass
        #    query[k].append(v)
        #print(query)

        raw_query_args = parse_qs(url.query)
        query = {}
        for key, values in raw_query_args.items():
            query[key] = []
            for value in values:
                if value.startswith("\""):
                    try:
                        value = json.loads(value)
                    except Exception as e:
                        pass
                query[key].append(value)

        path = unquote(url.path)
        fragment = unquote(url.fragment)

        request.location = Namespace(
            scheme = "https://", # http or https based on router?
            origin="0.0.0.0:1234", # from header host?
            raw_query_args=raw_query_args,
            path=path,
            query=query,
            fragment=fragment,
        )

        request.path_safe = url.path

        # remaining lines contain the headers

        while True:
            line = readline(request.rfile, 4096)

            if len(line) == 0:

                if b'Content-Length' in request.headers and \
                   b'Transfer-Encoding' in request.headers:
                    raise ProtocolError("found Content-Length and Transfer-Encoding")

                break

            else:
                k, v = line.split(b":", 1)
                k = k.strip()
                # TODO: reject request if any header is duplicated
                if k in request.headers:
                    raise ProtocolError("duplicate header")

                request.headers[k] = v.strip()

        #print(request.headers)

    def parse_body(self, request):

        body = None

        if request.method in (b'POST', b'PUT'):
            #request.request.sendall(b"HTTP/1.1 100 Continue\r\n")

            if b'Transfer-Encoding' in request.headers:
                if request.headers[b'Transfer-Encoding'] == b'chunked':
                    body = UploadChunkedFile(request.headers, request.rfile)
                else:
                    raise ProtocolError("invalid Transfer-Encoding")
            elif b'Content-Length' in request.headers:
                body = UploadMultiPartFile(request.headers, request.rfile)
            else:
                body = io.BytesIO()  # no body

            # check for a compressed upload and wrap the file
            if body and b'Content-Encoding' in request.headers:
                if request.headers[b'Content-Encoding'].lower() in [b'gzip', b'deflate']:
                    body = gzip.open(body, "rb")
        else:
            # check that there is no body for the DELETE/GET request
            # allow a Content-Length if it is zero
            size = 0
            te = request.headers.get(b'Transfer-Encoding', None)
            cl = request.headers.get(b'Content-Length', None)

            if cl:
                try:
                    size = int(cl)
                except ValueError as e:
                    size = -1

            if te or size != 0:
                raise ProtocolError("%s with body" % request.method)

        request.body = body

    def handle_request(self, request, router):

        response = None

        if request.method == b"OPTIONS":

            if b'Access-Control-Request-Method' in request.headers:
                headers = router.getPreflight(request.location.path, request.headers)
                status = 200
            else:
                options = router.getOptions(request.location.path)
                status = 204
                headers = {}
                headers['Allow'] = ", ".join(options)

            response = Response(status, headers)

        else:

            result = router.getRoute(request.method.decode("utf-8"), request.location.path)
            if result:
                resource, callback, matches = result

                request.args = matches

                try:
                    response = callback(resource, request)
                except Exception as e:
                    logging.exception("unhandled user exception")
                    response = None

            else:
                logging.error("route not found ")
                response = Response(404, {}, {'error': 'endpoint not found'})

        if not response:
            response = Response(500, {}, {'error':
                'endpoint failed to return a response'})

        return response

    def post_request(self, request, response):

        if "Access-Control-Allow-Origin" not in response.headers:
            response.headers['Access-Control-Allow-Origin'] = "http://localhost:4100"

        if "Access-Control-Allow-Credentials" not in response.headers:
            response.headers['Access-Control-Allow-Credentials'] = "true"

        #response.headers['Allow'] = "OPTIONS, GET, POST, PUT, DELETE"
        #response.headers['Access-Control-Allow-Origin'] = "*"

        #response.headers['Access-Control-Allow-Credentials'] = "true"
        #response.headers['Access-Control-Allow-Methods'] = "OPTIONS, GET, POST, PUT, DELETE"
        #response.headers['Access-Control-Allow-Headers'] = "Content-Type, Content-Length, Authorization"
        #response.headers['Access-Control-Max-Age'] = 86400

    def send_response(self, request, response):

        # parse headers:
        chunked = False
        content_length = -1
        if 'Content-Length' in response.headers:
            chunked = False
            content_length = int(response.headers['Content-Length'])
        elif 'Transfer-Encoding' in response.headers:
            chunked = True

        # send update
        elapsed = int((time.perf_counter() - request.t0) * 1000)
        transport_protocol = request.transport_protocol.decode()
        method = request.method.decode()
        #path = request.path.decode()
        path = request.path_safe
        host, port = request.client_address
        logging.info("%016X %s:%d %s %3d %6d %-8s %s [%d]" % (
            threading.get_ident(), host, port, transport_protocol,
            response.status, elapsed, method, path, content_length))

        wsock = request.request

        # send status
        status_str = responses[response.status].encode("utf-8")
        resp_str = b"%s %d %s\n" % (request.transport_protocol, response.status, status_str)
        wsock.sendall(resp_str)

        # send headers

        if 'Content-Length' not in response.headers and \
           'Transfer-Encoding' not in response.headers:
            response.headers['Content-Length'] = "0"

        for hdr, val in response.headers.items():
            hdr_str = b"%s: %s\r\n" % (hdr.encode("utf-8"), str(val).encode("utf-8"))
            wsock.sendall(hdr_str)
        wsock.sendall(b"\r\n")

        # send body

        if not response.payload:
            return

        wfile = SocketWriteFile(request.request, chunked)


        #
        # wfile = gzip.GzipFile(mode="wb", fileobj=wfile)

        if isinstance(response.payload, bytes):

            wfile.write(response.payload)
            wfile.close()

        elif hasattr(response.payload, 'read'):

            data = response.payload.read(2048)
            while data:
                wfile.write(data)
                data = response.payload.read(2048)
            wfile.close()

            if hasattr(response.payload, 'close'):
                response.payload.close()

        elif inspect.isgenerator(response.payload):

            for data in response.payload:
                wfile.write(data)
            wfile.close()

        elif callable(response.payload):
            response.payload(wfile)
            wfile.close()
        else:
            raise NotImplementedError(type(response.payload))

class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    router = None
    protocol = None

    def handle(self):

        self.protocol.handshake(self, self.request)

        while True:

            try:

                self.protocol.prepare(self)

                self.protocol.parse_headers(self)

                # todo check security here, on fail close connection
                self.protocol.parse_body(self)

                response = self.protocol.handle_request(self, self.router)

                self.protocol.post_request(self, response)

                self.protocol.send_response(self, response)

            except ConnectionResetError as e:
                logging.error(*self.fmtError(e))
                break

            except ssl.SSLError as e:
                logging.error(*self.fmtError(e))
                break

            except BrokenPipeError as e:
                logging.error(*self.fmtError(e))
                break

            except socket.timeout as e:
                logging.error(*self.fmtError(e))
                break

            except TLSSocketClosed as e:
                if self.method != b"n/a":
                    logging.error(*self.fmtError(e))
                break

            except ProtocolError as e:
                logging.error(*self.fmtError(e))
                #self.request.close()
                break
            except BaseException as e:
                logging.exception("unhandled exception")
                #self.request.close()
                break

    def fmtError(self, e):

        elapsed = int((time.perf_counter() - self.t0) * 1000)
        transport_protocol = self.transport_protocol
        method = self.method
        #path = self.path.decode()
        path = self.path_safe
        host, port = self.client_address
        fmt = "%016X %s:%d %s %-8s %s %s"
        args = (fmt, threading.get_ident(), host, port,
            transport_protocol, method, path, e)
        return args

def RequestHandlerFactory(_router, _protocol):

    _log = logging.getLogger("server.request")

    class RequestHandler(ThreadedTCPRequestHandler):
        router = _router
        protocol = _protocol
        log = _log

    return RequestHandler

class TCPServer(socketserver.TCPServer):
    allow_reuse_address = 1

    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True):
        super(TCPServer, self).__init__(server_address, RequestHandlerClass, bind_and_activate)

        self.ssl_version = ssl.PROTOCOL_TLSv1_2
        self.certfile = None
        self.keyfile = None
        self.password = None

        self.blocked_ips = {
            '91.241.19.84',
            '128.14.134.134',
            '74.82.47.3',
            '188.166.65.216',
            '162.243.128.166',
            '151.106.6.62',
        }

    def setCert(self, certfile, keyfile, password):
        self.certfile = certfile
        self.keyfile = keyfile
        self.password = password

    def get_request(self):
        sock, fromaddr = self.socket.accept()
        if self.certfile:
            # wrap the socket but delay performing the handshake until
            # the main request handler is reached
            sock = ssl.wrap_socket(sock,
                do_handshake_on_connect=False,
                server_side=True,
                certfile=self.certfile,
                keyfile=self.keyfile,
                ssl_version=self.ssl_version)

        return sock, fromaddr

    def verify_request(self, request, client_address):
        host, port = client_address
        if host in self.blocked_ips:
            logging.error("blocked request from address: %s", host)
            return False
        return True

class ThreadingMixIn(socketserver.ThreadingMixIn):
    daemon_threads = True

class ThreadedTCPServer(ThreadingMixIn, TCPServer):
    pass

class Site(object):
    def __init__(self, host, protocol=None):
        super(Site, self).__init__()
        self.host = host
        self.threads = []
        self.protocol = Protocol() if protocol is None else protocol

    def listenTLS(self, router, port, certfile, keyfile, password=None):

        if not os.path.exists(certfile):
            raise FileNotFoundError(certfile)
        if not os.path.exists(keyfile):
            raise FileNotFoundError(keyfile)
        factory = RequestHandlerFactory(router, self.protocol)
        server = ThreadedTCPServer((self.host, port), factory)
        server.router = router
        server.setCert(certfile, keyfile, password)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.server = server
        server_thread.ssl = True
        self.threads.append(server_thread)

    def listenTCP(self, router, port):
        factory = RequestHandlerFactory(router, self.protocol)
        server = ThreadedTCPServer((self.host, port), factory)
        server.router = router
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.server = server
        server_thread.ssl = False
        self.threads.append(server_thread)

    def start(self):
        for thread in self.threads:
            host, port = thread.server.server_address
            for method, pattern, _ in thread.server.router.endpoints:
                # count is a score which could be used for sorting the endpoints
                # count could be used for solving the longest match problem
                parts = pattern.split("/")
                count = sum([0 if not p or p.endswith("*") else 1 for p in parts])

                logging.info("%5d %-8s %2d %s" % (port, method, count, pattern))
            proto = "https://" if thread.ssl else "http://"
            logging.info("now listening on %s%s:%d" % (proto, host, port))
            thread.start()

    def join(self):
        for thread in self.threads:
            thread.join()