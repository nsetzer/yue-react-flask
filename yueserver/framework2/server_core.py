
import os
import sys
import io
import re
import socket
import threading
import socketserver
import select
import gzip
import logging
import argparse
import json
import mimetypes

from datetime import datetime

from collections import defaultdict

from urllib.parse import urlparse, unquote
from http.client import responses

# from http import HTTPStatus

HTTP_STATUS_CODES = {
    100: "Continue",
    101: "Switching Protocols",
    102: "Processing",
    103: "Early Hints",  # see RFC 8297
    200: "OK",
    201: "Created",
    202: "Accepted",
    203: "Non Authoritative Information",
    204: "No Content",
    205: "Reset Content",
    206: "Partial Content",
    207: "Multi Status",
    208: "Already Reported",  # see RFC 5842
    226: "IM Used",  # see RFC 3229
    300: "Multiple Choices",
    301: "Moved Permanently",
    302: "Found",
    303: "See Other",
    304: "Not Modified",
    305: "Use Proxy",
    306: "Switch Proxy",  # unused
    307: "Temporary Redirect",
    308: "Permanent Redirect",
    400: "Bad Request",
    401: "Unauthorized",
    402: "Payment Required",  # unused
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    406: "Not Acceptable",
    407: "Proxy Authentication Required",
    408: "Request Timeout",
    409: "Conflict",
    410: "Gone",
    411: "Length Required",
    412: "Precondition Failed",
    413: "Request Entity Too Large",
    414: "Request URI Too Long",
    415: "Unsupported Media Type",
    416: "Requested Range Not Satisfiable",
    417: "Expectation Failed",
    418: "I'm a teapot",  # see RFC 2324
    421: "Misdirected Request",  # see RFC 7540
    422: "Unprocessable Entity",
    423: "Locked",
    424: "Failed Dependency",
    425: "Too Early",  # see RFC 8470
    426: "Upgrade Required",
    428: "Precondition Required",  # see RFC 6585
    429: "Too Many Requests",
    431: "Request Header Fields Too Large",
    449: "Retry With",  # proprietary MS extension
    451: "Unavailable For Legal Reasons",
    500: "Internal Server Error",
    501: "Not Implemented",
    502: "Bad Gateway",
    503: "Service Unavailable",
    504: "Gateway Timeout",
    505: "HTTP Version Not Supported",
    506: "Variant Also Negotiates",  # see RFC 2295
    507: "Insufficient Storage",
    508: "Loop Detected",  # see RFC 5842
    510: "Not Extended",
    511: "Network Authentication Failed",  # see RFC 6585
}

class ProtocolError(Exception):
    pass

class TLSSocketClosed(Exception):
    pass

def readword(file, maxlen=4096):
    data = []

    b = file.read(1)
    if not b:
        raise TLSSocketClosed("no data")

    while True:

        if b == b" ":
            break

        data.append(b)

        if len(data) > maxlen:
            logging.error("received header: %r" % (b"".join(data[:32])))
            raise ProtocolError("header too large")

        b = file.read(1)
        if not b:
            raise TLSSocketClosed("no data")

    return b"".join(data)

def readline(file, maxlen=4096):
    data = []
    a = file.read(1)
    if not a:
        # an issue when using ssl and invalid certificates
        raise TLSSocketClosed("no data")
    b = file.read(1)
    if not b:
        raise TLSSocketClosed("no data")

    while True:

        if a == b'\r' and b == b'\n':
            break;

        data.append(a)

        if len(data) > maxlen:
            logging.error("received header: %r" % (b"".join(data[:32])))
            raise ProtocolError("header too large")

        a = b
        b = file.read(1)
        if not b:
            raise TLSSocketClosed("no data")
    return b"".join(data)

def setupLogger(logger_name, log_file):
    parent, _ = os.path.split(log_file)

    if not os.path.exists(parent):
        os.makedirs(parent)

    l = logging.getLogger(logger_name)
    formatter = logging.Formatter('%(asctime)-15s %(levelname)s %(pathname)s:%(funcName)s:%(lineno)d: %(message)s')

    size = 1024 * 1024
    backupCount = 5
    fileHandler = RotatingFileHandler(
        log_file, maxBytes=size, backupCount=backupCount)
    fileHandler.setFormatter(formatter)
    l.addHandler(fileHandler)
    #if logger_name is not None:
    #    streamHandler = logging.StreamHandler()
    #    streamHandler.setFormatter(formatter)
    #    l.addHandler(streamHandler)

    return l

class Namespace(object):
    def __init__(self, **props):
        super(Namespace, self).__init__()
        for k, v in props.items():
            setattr(self, k, v)

    def __str__(self):
        attrs = ["%s=%s" % (name, getattr(self,name))
            for name in dir(self)
            if not name.startswith("_")]
        return "<Namespace(%s)>" % (', '.join(attrs))

class SocketFile(object):
    def __init__(self, sock):
        super(SocketFile, self).__init__()

        self.sock = sock

        self.recv = self.sock.recv

        self.closed = False

    def fileno(self):
        return self.sock.fileno()

    def readable(self):
        return True

    def writable(self):
        return True

    def seekable(self):
        return False

    def read(self, n=None):
        return self.sock.recv(n)

    def write(self, b):
        self.sock.sendall(b)
        return len(b)

    def flush(self):
        pass

    def close(self):
        self.closed = True

class SocketWriteFile(object):
    """wrap a socket with a writable file like object

    used for implementing streaming for a response payload
    """
    def __init__(self, sock, chunked):
        super(SocketWriteFile, self).__init__()

        self.sock = sock
        self.chunked = chunked
        self.closed = False

        self.bytes_written = 0

    def fileno(self):
        return self.sock.fileno()

    def readable(self):
        return False

    def writable(self):
        return True

    def seekable(self):
        return False

    def read(self, n=None):
        raise NotImplementedError()

    def write(self, data):
        if self.closed:
            return

        if self.chunked:
            self.sock.sendall(b"%X\r\n" % len(data))
            self.sock.sendall(data)
            self.sock.sendall(b"\r\n")
        else:
            self.sock.sendall(data)

        n = len(data)
        self.bytes_written += n
        return n

    def flush(self):
        pass

    def close(self):
        if self.closed:
            return

        if self.chunked:
            self.sock.sendall(b"0\r\n\r\n")
        self.closed = True

class CaseInsensitiveDict(dict):
    def __setitem__(self, key, value):
        super().__setitem__(key.upper(), value)

    def __getitem__(self, key):
        return super().__getitem__(key.upper())

    def __in__(self, key):
        return super().__in__(key.upper())

    def __contains__(self, key):
        return super().__contains__(key.upper())

    def get(self, key, default=None):
        return super().get(key.upper(), default)

class UploadChunkedFile(object):
    def __init__(self, headers, rfile):
        super(UploadChunkedFile, self).__init__()
        self.headers = headers
        self.rfile = rfile
        self.closed = False
        self._init = False
        self.counter = 0

    def fileno(self):
        return self.rfile.fileno()

    def read(self, size=-1):

        if self.closed:
            logging.debug("read on closed file")
            return b""

        if not self._init:
            self._init_body()

        parts = []

        if size == -1:
            # read all fragments and return the remainder of the file
            if self.fragment:
                parts.append(self.fragment)
            data = self._read_chunk()
            while data:
                parts.append(data)
                data = self._read_chunk()
        else:
            # read at most 'size' bytes

            if len(self.fragment) == size:
                parts.append(self.fragment)
                self.fragment = b""

            elif len(self.fragment) > size:
                parts.append(self.fragment[:size])
                self.fragment = self.fragment[size:]

            else:
                count = 0

                if self.fragment:
                    parts.append(self.fragment)
                    count += len(self.fragment)
                    self.fragment = b""

                while count < size:

                    data = self._read_chunk()

                    if not data:
                        break

                    elif len(data) + count >= size:
                        n = size - count
                        parts.append(data[:n])
                        self.fragment = data[n:]
                        break

                    else:
                        parts.append(data)
                        count += len(data)

        if parts:
            data = b"".join(parts)
        else:
            data = b""

        logging.debug("%8d -- expected: %6d read: %d", self.counter, size, len(data))
        return data

    def _read_chunk(self):
        """ read a single chunk of data from the request

        each chunk is composed of 2 "lines"

        * a hex-encoded integer followed by a newline.
            indicates the size of the chunk
        * the number of bytes
        * a new line

        The upload is terminated by an empty chunk b"0\r\n\r\n"

        """

        if self.closed:
            return b""

        self.counter += 1

        size = int(readline(self.rfile), 16)
        if size > 0:
            data = self.rfile.read(size)
        else:
            self.closed = True
            return b""

        readline(self.rfile) # terminating \r\n for this chunk

        return data

    def detach(self):
        pass

    def _init_body(self):
        self.fragment = b""

        if b'Expect' in self.headers:
            if self.headers[b'Expect'] == b'100-continue':
                #todo: wfile
                self.rfile.write(b"HTTP/1.1 100 Continue\r\n")

        self._init = True

class UploadMultiPartFile(object):
    def __init__(self, headers, rfile):
        super(UploadMultiPartFile, self).__init__()
        self.rfile = rfile
        self.headers = headers
        self._init = False
        self.closed = False

        self.length = 0 # remaining bytes to read
        self.content_length = 0 # total content length
        self.content_extra_length = 0 # footer length

        self.bytes_read = 0
        self.counter = 0

    def fileno(self):
        return self.rfile.fileno()

    def read(self, size=-1):
        # curl -u "admin:admin" -X POST --upload-file 333.7z "localhost:4200/api/fs/userdata/path/333.7z"
        # curl -u "admin:admin" -X POST -H "Transfer-Encoding: chunked" --upload-file 333.7z "localhost:4200/api/fs/userdata/path/333_chunked.7z"
        """
                  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                                 Dload  Upload   Total   Spent    Left  Speed
                 99  375M    0     0  100  375M      0   663k  0:09:39  0:09:39 --:--:--     0
                 {"result": "OK", "file_info": {"size": 0, "mtime": 1604752199, "encryption": null, "permission": 420, "version": 5}}
                100  375M    0   117  100  375M      0   662k  0:09:39  0:09:39 --:--:--     0

              % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                             Dload  Upload   Total   Spent    Left  Speed
            100  375M    0     0  100  375M      0   467k  0:13:42  0:13:43 --:--:--     0

            botocore.exceptions.ReadTimeoutError

        """
        if not self._init:
            self._init_body()

        if self.closed:
            logging.debug("read on closed file")
            return b""

        # read at most the remaining bytes
        if size >= 0:
            n = min(size, self.length)
        else:
            n = self.length

        blocks = []

        while n > 0:
            self.counter += 1

            data = self.rfile.read(n)

            if data:
                blocks.append(data)

            self.length -= len(data)
            n -= len(data)
            self.bytes_read += len(data)

        if self.length == 0:
            logging.debug("received all bytes for upload: %d %d", self.content_length, self.bytes_read)
            self.rfile.read(self.content_extra_length)
            self.closed = True

        data = b"".join(blocks)
        logging.debug("%8d -- expected: %6d read: %d", self.counter, size, len(data))
        return data

    def fileno(self):
        return self.rfile.fileno()

    def detach(self):
        pass

    def _init_body(self):

        s_length = self.headers.get(b'content-length', None)
        if not s_length:
            raise ProtocolError("missing content-length")

        length = int(s_length)

        boundary = None
        if b'content-type' in self.headers:
            content_type = self.headers[b'content-type']
            parts = content_type.split(b";")
            boundary = None
            for part in parts:
                part = part.strip()
                if part.startswith(b"boundary="):
                    boundary = part[len(b"boundary="):]

        self.metadata = []

        if boundary:
            line = readline(self.rfile)

            # readline does not return \r\n, +2
            length -= 2

            # subtract the boundary at the end of the file
            # '\r\n<boundary>--\r\n'

            self.content_extra_length = len(line) + 6
            length -= self.content_extra_length

            while len(line) > 2:
                length -= len(line) + 2
                line = readline(self.rfile)
                self.metadata.append(line)

        self.length = length # remaining bytes to read
        self.content_length = length # total content length

        if b'Expect' in self.headers:
            if self.headers[b'Expect'] == b'100-continue':
                #todo: wfile
                self.rfile.write(b"HTTP/1.1 100 Continue\r\n")

        self._init = True

class Response(object):
    """
        if compress:
            gzip_buffer = io.BytesIO()
            gzip_file = gzip.GzipFile(mode='wb',
                                      fileobj=gzip_buffer)
            gzip_file.write(self.payload)
            gzip_file.close()

            self.payload = gzip_buffer.getvalue()

            self.headers['Vary'] = 'Accept-Encoding'
            self.headers['Content-Encoding'] = 'gzip'
            self.headers['Content-Length'] = len(self.payload)
    """
    def __init__(self, status=200, headers=None, payload=None):
        super(Response, self).__init__()
        self.status = status
        self.headers = {} if headers is None else headers
        self.payload = payload
        self.compress = False

        if isinstance(self.payload, dict):
            self.payload = json.dumps(self.payload).encode("utf-8") + b"\n"
            self.headers['Content-Type'] = "application/json"
            self.headers['Content-Length'] = str(len(self.payload))

        elif isinstance(self.payload, str):
            self.payload = self.payload.encode("utf-8")
            self.headers['Content-Length'] = str(len(self.payload))
        elif isinstance(self.payload, bytes):
            self.headers['Content-Length'] = str(len(self.payload))




class Router(object):
    def __init__(self):
        super(Router, self).__init__()
        self.route_table = {
            "DELETE": [],
            "GET": [],
            "POST": [],
            "PUT": [],
        }
        self.endpoints = []

    def registerEndpoints(self, endpoints):
        for resource, method, pattern, callback in sorted(endpoints, key=lambda x:x[3]._ordinal):
            regex, tokens = self.patternToRegex(pattern)
            self.route_table[method].append((regex, tokens, resource, callback))
            self.endpoints.append((method, pattern, callback._ordinal))

    def getPreflight(self, path, headers):

        method = headers.get(b'Access-Control-Request-Method', b"").decode("utf-8")
        allowed_headers = headers.get(b'Access-Control-Request-Headers', b"").decode("utf-8")

        allowed_headers = set([hdr.strip().title() for hdr in allowed_headers.split(",")])
        allowed_headers.add("Content-Type")
        allowed_headers.add("Authentication")
        if "" in allowed_headers:
            allowed_headers.remove("")

        options = self.getOptions(path)

        response_headers = {}

        response_headers['Allow'] = ", ".join(options)
        response_headers['Access-Control-Allow-Origin'] = "*"
        response_headers['Access-Control-Allow-Methods'] = ", ".join(options)
        response_headers['Access-Control-Allow-Headers'] = ", ".join(sorted(allowed_headers))
        response_headers['Access-Control-Max-Age'] = 86400

        return response_headers

    def getOptions(self, path):

        if path == "*":
            return ['OPTIONS', 'GET', 'POST', 'PUT', 'DELETE']

        options = []

        for method, table in self.route_table.items():
            for re_ptn, tokens, resource, callback in table:
                m = re_ptn.match(path)
                if m:
                    options.append(method)

        if options:
            options.insert(0, 'OPTIONS')

        return options

    def getRoute(self, method, path):
        for re_ptn, tokens, resource, callback in self.route_table[method]:
            m = re_ptn.match(path)
            if m:
                matches = Namespace(**{k: v for k, v in zip(tokens, m.groups())})
                return resource, callback, matches
        return None

    def patternToRegex(self, pattern):
        # convert a url pattern into a regular expression
        #
        #   /abc        - match exactly
        #   /:abc       - match a path compenent exactly once
        #   /:abc?      - match a path component 0 or 1 times
        #   /:abc+      - match a path component 1 or more times
        #   /:abc*      - match a path component 0 or more times
        #
        # /:abc will match '/foo' with
        #  {'abc': foo}
        # /:bucket/:key* will match '/mybucket/dir1/dir2/fname' with
        #  {'bucket': 'mybucket', key: 'dir1/dir2/fname'}

        parts = [part for part in pattern.split("/") if part]
        tokens = []
        re_str = "^"
        for part in parts:
            if (part.startswith(':')):
                c = part[-1]
                if c == '?':
                    tokens.append(part[1: -1])
                    re_str += "\\/([^\\/]*)"
                elif c == '*':
                    tokens.append(part[1: -1])
                    # todo: match '\\/?'' or '\\/()'
                    # otherwise the / ends up being optional
                    re_str += "\\/?(.*)"
                elif c == '+':
                    tokens.append(part[1: -1])
                    re_str += "\\/?(.+)"
                else:
                    tokens.append(part[1:])
                    re_str += "\\/([^\\/]+)"
            else:
                re_str += '\\/' + part

        if re_str != "^\\/":
            re_str += "\\/?"

        re_str += '$'
        return (re.compile(re_str), tokens)

def send_file(root_directory, filename, headers=None, attachment=False):

    root_directory = root_directory.replace("\\", "/")
    filename = filename.replace("\\", "/")

    parts = set(filename.split("/"))
    if ".." in parts or "." in parts:
        raise ValueError("invalid path")

    path = os.path.join(root_directory, filename)
    path = os.path.abspath(path)

    st = os.stat(path)

    if headers is None:
        headers = {}

    headers['Content-Length'] = str(st.st_size)

    mimetype, encoding = mimetypes.guess_type(path)

    if mimetype:
        headers['Content-Type'] = mimetype
    else:
        headers['Content-Type'] = "application/octet-stream"

    if encoding:
        headers['Content-Encoding'] = encoding

    _, attachment_name = os.path.split(path)

    mode = "attachment" if attachment else "inline"
    mode += "; filename=%s" % (json.dumps(attachment_name))
    headers['Content-Disposition'] = mode

    return Response(200, headers, open(path, "rb"))

def send_generator(go, attachment_name, file_size=None, headers=None, attachment=False):
    """
    this may not work on chrome, although that may also be a webkit
    issue with mp3 files...

    attachment: under certain browser senarios, such as 'right click > view image'
        if there is a attachment header then the file will be downloaded
        instead of being displayed in the browser
    """

    if headers is None:
        headers = {}

    mimetype, encoding = mimetypes.guess_type(attachment_name)

    if not mimetype:
        mimetype = 'application/octet-stream'

    if 'Content-Type' not in headers:
        if mimetype:
            headers['Content-Type'] = mimetype
        else:
            headers['Content-Type'] = "application/octet-stream"

    if 'Content-Encoding' not in headers:
        if encoding:
            headers['Content-Encoding'] = encoding

    if 'Content-Length' not in headers and 'Transfer-Encoding' not in headers:
        if file_size is not None:
            headers['Content-Length'] = str(file_size)
        else:
            headers['Transfer-Encoding'] = "chunked"

    mode = "attachment" if attachment else "inline"
    mode += "; filename=%s" % (json.dumps(attachment_name))
    headers['Content-Disposition'] = mode
    print("sending file", file_size, headers.get('Content-Length', None), headers.get('Transfer-Encoding', None))

    return Response(200, headers, go)
