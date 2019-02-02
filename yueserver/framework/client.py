
"""
Framework to auto generate a Python Requests client.

When the application registers a WebResource, the endpoints are stored
in an array of RegisteredEndpoints. This file defines a way to generate
an argument parser and RESTful client using that list of endpoints.

"""

import sys
import json
import requests
import base64
import argparse
import requests.exceptions as exceptions
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
from requests.utils import quote
import logging
from io import BytesIO

from collections import namedtuple

##
# A tuple describing a RESTful endpoint
RegisteredEndpoint = namedtuple('RegisteredEndpoint',
    ['path', 'long_name', 'doc', 'methods', 'params', 'headers', 'body'])

##
# A tuple describing a query parameter
Parameter = namedtuple('Parameter',
    ['name', 'type', 'default', 'required', 'doc'])

def split_auth(authas):
    """ parse a string into authorization parts

    e.g. username@host#domain/role into (username@host, domain, role)

    username can be a name, or an email address.

    returns a 3-tuple: username, domain, role
    domain and role are optional, if not provided an empty
    string will be returned

    """
    domain = ""
    role = ""

    if "#" in authas:
        user, extra = authas.split("#")
        if "/" in extra:
            domain, role = extra.split("/")
        else:
            domain = extra
    else:
        user = authas

    return user, domain, role

def url_encode(url, f):
    """
    format a url-string by populating the elements to replace

    a url can be of the form "/api/<foo>". this function will replace the
    section "<foo>" with the result from calling f("foo").

    optionally, the url may contain type information. e.g.:
        <path:MyPath> (value is a string and may contain path separators)

    """
    i = url.find('<')
    while i >= 0:
        j = url.find('>', i)
        varname = url[i + 1:j]
        if ':' in varname:
            varname = varname.split(":")[1]

        error = None
        try:
            s = str(quote(f(varname)))
        except Exception as e:
            error = "error formating variable: %s" % varname

        if error is not None:
            raise UrlEncodeException(error)

        url = url[:i] + s + url[j + 1:]

        i = url.find('<', i)

    return url

def url_decode(url):
    """ return the list of variable names inside the url string

    see url_encode
    """
    variables = []
    i = url.find('<')
    while i >= 0:
        j = url.find('>', i)
        varname = url[i + 1:j]

        typename = "str"
        if ':' in varname:
            typename, varname = varname.split(":")

        variables.append((typename, varname))

        i = url.find('<', i + 1)

    return variables

class ClientException(Exception):
    pass

class UrlEncodeException(ClientException):
    pass

class ParameterException(ClientException):
    pass

class Response(object):
    """
    wrap the requests response object to throw an exception when the
    json data is accessed and the response is successful
    """
    def __init__(self, response):
        super(Response, self).__init__()
        self._response = response
        self.status_code = self._response.status_code

    def __getattr__(self, attr):

        if hasattr(self._response, attr):
            return getattr(self._response, attr)

    def json(self):

        data = self._response.json()
        if self._response.status_code >= 400:
            message = "server returned error statues: %s" % \
                self._response.status_code
            if 'error' in data:
                message = data['error']
            raise ClientException(message)
        return data

    def stream(self, chunk_size=1024):
        for chunk in self._response.iter_content(chunk_size=chunk_size):
            if chunk:
                yield chunk

class AuthenticatedRestClient(object):
    """a basic https client for making authenticated requests"""
    def __init__(self, host, username, password, domain, role):
        super(AuthenticatedRestClient, self).__init__()
        self.username = username
        self.password = password
        self.domain = domain
        self.role = role

        self._host = host

        self.verify_ssl = False

        self._session = requests.Session()

    def host(self):
        return self._host

    def setSession(self, session):
        """
        set a session context to use for subsequent requests

        by default, create a new http(s) connection for every request
        by providing a session (requests.Session()) connections can be
        reused between method calls
        """
        self._session = session

    def get(self, url, **kwargs):
        """
            kwargs can contain the following:
                params: dictionary of query string encoded parameters
        """
        return self._makeRequest(self._session.get, url, **kwargs)

    def put(self, url, **kwargs):
        payload = kwargs['data']
        del kwargs['data']
        return self._makeRequest(self._session.put, url, data=payload, **kwargs)

    def post(self, url, **kwargs):
        """ Send a post request to the configured server

        url: the api endpoint (sans host and port)
        payload: the post body content

        Streaming uploads can be done by passing the payload as an iterator.
            For example, the output of a function which yields bytes.
            the iterator should yield bytes

        """
        payload = kwargs['data']
        del kwargs['data']
        return self._makeRequest(self._session.post, url, data=payload, **kwargs)

    def delete(self, url, **kwargs):
        return self._makeRequest(self._session.delete, url, **kwargs)

    def _makeRequest(self, method, url, **kwargs):
        """
            kwargs supports all of the default requests options

        """

        if "headers" not in kwargs:
            kwargs['headers'] = {}

        if 'json' in kwargs:
            if kwargs['json']:
                kwargs['headers']["Content-Type"] = "application/json"
            del kwargs['json']

        if self.domain:
            kwargs['headers']["X-Domain"] = self.domain
        if self.role:
            kwargs['headers']["X-Role"]   = self.role

        if self.password.startswith("APIKEY"):
            kwargs['headers']["Authorization"] = self.password
        else:
            auth = "Basic %s" % (base64.b64encode(b"%s:%s" % (
                self.username.encode("utf-8"),
                self.password.encode("utf-8")))).decode("utf-8")
            kwargs['headers']["Authorization"] = auth

        url = "%s%s" % (self._host, url)

        # ignore the SSL cert
        kwargs['verify'] = self.verify_ssl
        # allow redirections (e.g. getting files from the datastore)
        kwargs['allow_redirects'] = True

        result = method(url, **kwargs)

        # Authorization header may have been lost in case of redirect
        # attempt the request again
        if result.status_code != 200 and len(result.history) > 0:
            response = result.history[-1]
            if 300 <= response.status_code < 400:
                result = method(result.url, **kwargs)

        return result

    def __str__(self):
        return "%s" % (self._host)

    def __repr__(self):
        return "<%s(%s)>" % (self.__class__.__name__, self._host)

def _request_builder(endpoint, *args, **kwargs):
    """
    args: the positional arguments that compose the URL
           for PUT and POST methods, the final positional
           argument should be a file like object implementing read(),
           the body of the request.

    special kwarg options:
        stream: set True for a streaming download of the response body
        method: specify the exact method to use (GET, PUT, POST, DELETE)

    returns:
        method: the method name to process the request,
                get, put, post, delete
        url:    the request URL
        options: an options dictionary formatted for the requests library

    """

    positional = list(args)

    options = {"headers": {}}

    if 'method' in kwargs:
        # TODO: may want to assert that the chosen method
        # is a valid method in the set of defined methods
        # on this endpoint
        method = kwargs['method'].lower()
        del kwargs['method']
    else:
        method = endpoint.methods[0].lower()

    if 'headers' in kwargs:
        options['headers'] = kwargs['headers']
        del kwargs['headers']

    if 'stream' in kwargs:
        options['stream'] = kwargs['stream']
        del kwargs['stream']

    _type, _mimetype = endpoint.body
    if _type is not None and method in ["put", "post"]:
        options['data'] = positional.pop()

        if 'Content-Type' not in options['headers']:
            options['headers']['Content-Type'] = _mimetype
    elif method in ["put", "post"]:
        options['data'] = '/dev/null'

    for header in endpoint.headers:
        if header.name in kwargs:
            options['headers'][header.name] = kwargs[header.name]
            del kwargs[header.name]

    # TODO: this is a bug waiting to happen
    #       keep this for now, but also accept
    #       a kwarg 'params' which accepts a dictionary to do the same
    param_names = {p.name for p in endpoint.params}
    for key in kwargs.keys():
        if key not in param_names:
            raise ParameterException("Unknown keyword argument: %s" % key)

    if len(kwargs) > 0:
        # we get this for free using the requests library, null parameters
        # are not sent as part of the request. However, make this behavior
        # explicit, so that we do not depend on the underlying library
        # doing the right thing.
        for key in list(kwargs.keys()):
            if kwargs[key] is None:
                del kwargs[key]
        options['params'] = kwargs

    url = url_encode(endpoint.path, lambda v: positional.pop(0))

    if len(positional) > 0:
        raise UrlEncodeException("too many positional arguments provided")

    return method, url, options

def _request_args_builder(endpoint, args):
    positional = []
    for typename, varname in url_decode(endpoint.path):
        positional.append(getattr(args, varname))

    kwargs = {param[0]: getattr(args, param.name) for param in endpoint.params}
    kwargs.update({header[0]: getattr(args, header.name.replace("-", "_")) for header in endpoint.headers})

    for extra in ['stream', 'json', 'method']:
        if hasattr(args, extra):
            kwargs[extra] = getattr(args, extra)

    headers = {}

    if hasattr(args, "content_type"):
        headers["Content-Type"] = getattr(args, "content_type")
    for hstr in args.headers:
        if ':' not in hstr:
            raise Exception("Invalid header string: `%s`" % hstr)
        name, value = hstr.split(":", 1)
        value = value.lstrip()
        name = name.rstrip()
        headers[name] = value
    kwargs['headers'] = headers

    if hasattr(args, 'data'):
        data = getattr(args, 'data')
        if data == "-":
            # support seeking the input
            data = BytesIO(sys.stdin.buffer.read())
        else:
            data = open(data, "rb")

        positional.append(data)

    return _request_builder(endpoint, *positional, **kwargs)

class FlaskAppClient(object):
    """docstring for FlaskAppClient
    """
    def __init__(self, rest_client, registered_endpoints):
        super(FlaskAppClient, self).__init__()

        self._client = rest_client
        self._endpoints = {}
        for endpoint in registered_endpoints:
            name = endpoint.long_name \
                .lower() \
                .replace("resource", "") \
                .replace(".", "_")
            self._endpoints[name] = endpoint

    def host(self):
        return self._client.host()

    def __getattr__(self, attr):

        if attr in self._endpoints:

            def impl(*args, **kwargs):
                return self._method_impl(attr, *args, **kwargs)
            impl.__doc__ = self._endpoints[attr].doc
            impl.__name__ = attr

            return impl

    def _method_impl(self, name, *args, **kwargs):
        """

        name: the name of the endpoint to invoke.
              this is a normalized name, for an endpoint
              AppResource.index, name should be app_index
        """
        endpoint = self._endpoints[name]

        method, url, options = _request_builder(endpoint, *args, **kwargs)

        return Response(getattr(self._client, method)(url, **options))

    def endpoints(self):
        return self._endpoints.keys()

def generate_argparse(registered_endpoints):
    """return an ArgumentParser instance enumerating all endpoints

    use the registered endpoints to generate a series of subparsers.
    Query parameters become optional arguments, and path parameters
    become positional arguments. Requests that have a body will have
    a final positional argument which can be a file path, or "-" for
    stdin.

    when arguments are parsed, the returned args object will have a
    member function 'func' which is used to unpack the supplied
    arguments into the url endpoint to call.
    """

    parser = argparse.ArgumentParser(description='client')

    parser.add_argument('--username', required=True,
                    help='username')
    parser.add_argument('--password', required=False,
                    help='password')
    parser.add_argument('--host', dest='host',
                    default="https://localhost:4200",
                    help='the database connection string')
    parser.add_argument('-v', '--verbose', dest='verbose',
                    action='store_true',
                    help='enable verbose logging')

    subparsers = parser.add_subparsers()

    index_name = ["1st", "2nd", "3rd", "4th", "5th",
                  "6th", "7th", "8th", "9th", "10th"]
    for endpoint in registered_endpoints:

        name = endpoint.long_name.lower().replace("resource", "")

        # create the subparser
        doc = "%s" % (endpoint.path)
        end_parser = subparsers.add_parser(name, help=doc)
        end_parser.set_defaults(
            func=lambda args, endpoint=endpoint:
                _request_args_builder(endpoint, args))

        end_parser.add_argument("-H", "--header", action="append", type=str,
            default=[], dest="headers",
            help="add additional headers to the request", )

        # parse the registered parameters, and generate optional arguments
        for param in endpoint.params:
            end_parser.add_argument("--%s" % param.name,
                help=param.doc,
                default=param.default,
                required=param.required)

        # parse the registered headers, and generate optional arguments
        for header in endpoint.headers:
            end_parser.add_argument("--%s" % header.name,
                help=header.doc,
                default=header.default,
                required=header.required)

        # parse the URL path, and generate positional arguments

        for i, (typename, varname) in enumerate(url_decode(endpoint.path)):
            idx = index_name[i] if i <= len(index_name) else "%dth" % i
            doc = "%s path component (type: %s)" % (idx, typename)
            end_parser.add_argument(varname,
                help=doc)

        if len(endpoint.methods) > 1:
            end_parser.add_argument("--method", default=endpoints.methods[0],
                type=str, help="specify http method to use for the request")

        # if the endpoint requires a body, add a final positional argument
        # used for uploading a document or stdin
        _type, _mimetype = endpoint.body
        if _type is not None:
            end_parser.add_argument("data",
                help="file to upload (- for stdin)")

            end_parser.add_argument("--no-stream", action="store_false",
                dest="stream",
                help="disable streaming uploads")

            end_parser.add_argument("--content-type", default=_mimetype,
                type=str, dest="content_type",
                help="the body content type (%s)" % _mimetype)

    return parser

def cli_main(endpoints, args):

    parser = generate_argparse(endpoints)
    cli_args = parser.parse_args(args)
    method, url, options = cli_args.func(cli_args)

    # create a client, connect to the server
    username, domain, role = split_auth(cli_args.username)
    password = cli_args.password

    client = AuthenticatedRestClient(cli_args.host,
        username, password, domain, role)

    logging.basicConfig(format='%(asctime)-15s %(message)s',
        level=logging.DEBUG if cli_args.verbose else logging.INFO)

    response = Response(getattr(client, method.lower())(url, **options))

    if cli_args.verbose:
        sys.stderr.write("url: %s\n" % response.url)
        sys.stderr.write("status: %d\n" % response.status_code)
        sys.stderr.write("Request Headers:\n")
        for name, value in response.request.headers.items():
            sys.stderr.write("  %s: %s\n" % (name, value))

        sys.stderr.write("Response Headers:\n")
        for name, value in response.headers.items():
            sys.stderr.write("  %s: %s\n" % (name, value))

    if response.status_code >= 400:
        sys.stderr.write("%s\n" % response.text)
        sys.exit(response.status_code)

    for chunk in response.stream():
        sys.stdout.buffer.write(chunk)

def connect_impl(host, username, password, endpoints):
    """ return a new REST client which implements the given endpoints"""
    username, domain, role = split_auth(username)
    client = AuthenticatedRestClient(host,
             username, password, domain, role)
    return FlaskAppClient(client, endpoints)


