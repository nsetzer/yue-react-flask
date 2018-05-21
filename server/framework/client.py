
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

from collections import namedtuple

"""

"""

RegisteredEndpoint = namedtuple('RegisteredEndpoint',
    ['path', 'long_name', 'doc', 'methods', 'params', 'body'])

def split_auth(authas):
    """ parse a string user@domain/role into basic parts

    returns a 3-tuple: user, domain, role
    """
    domain = ""
    role = ""

    if "@" in authas:
        user, extra = authas.split("@")
        if "/" in extra:
            domain, role = extra.split("/")
        else:
            domain = extra
    else:
        user = authas

    return user, domain, role

def url_encode(url, f):

    i = url.find('<')
    while i >= 0:
        j = url.find('>', i)
        varname = url[i + 1:j]
        if ':' in varname:
            varname = varname.split(":")[1]

        s = quote(f(varname))
        url = url[:i] + s + url[j + 1:]

        i = url.find('<', i)

    return url

def url_decode(url):
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

        self.host = host

        self.verify_ssl = False

        self._session = requests

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

        kwargs['headers']["X-Yue-Domain"] = self.domain
        if self.role:
            kwargs['headers']["X-Yue-Role"]   = self.role

        auth = "Basic %s" % (base64.b64encode(b"%s:%s" % (
            self.username.encode("utf-8"),
            self.password.encode("utf-8")))).decode("utf-8")
        kwargs['headers']["Authorization"] = auth

        url = "%s%s" % (self.host, url)

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
        return "%s" % (self.host)

    def __repr__(self):
        return "<%s(%s)>" % (self.__class__.__name__, self.host)

def _request_buider(endpoint, *args, **kwargs):
    """
    args: the positional arguments that compose the URL
           for PUT and POST methods, the final positional
           argument should be a file like object implementing read(),
           the body of the request.

    special kwarg options:
        stream: set True for a streaming download of the response body
        method: specifiy the exact method to use
        json:   the request content body is a json document

    returns:
        method: the method name to process the request,
                get, put, post, delete
        url:    the request URL
        options: an options dictionary formatted for the requests library

    """

    positional = list(args)

    options = {}

    if 'method' in kwargs:
        # TODO: may want to assert that the chosen method
        # is a valid method in the set of defined methods
        # on this endpoint
        method = kwargs['method'].lower()
        del kwargs['method']
    else:
        method = endpoint.methods[0].lower()

    _type, _json = endpoint.body
    if _type is not None or method in ["put", "post"]:
        options['data'] = positional.pop()

    if json:
        options['json'] = True

    if 'stream' in kwargs:
        options['stream'] = kwargs['stream']
        del kwargs['stream']

    param_names = {name for name, _, _, _ in endpoint.params}
    for key in kwargs.keys():
        if key not in param_names:
            raise ParameterException("Unknown keyword argument: %s" % key)

    if len(kwargs) > 0:
        options['params'] = kwargs

    # todo: validate correct number of arguments given
    url = url_encode(endpoint.path, lambda v: positional.pop(0))

    return method, url, options

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

        method, url, options = _request_buider(endpoint, *args, **kwargs)

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

    todo: write a function which generates a python client package
    serialize the _registered_endpoints and refactor this method to
    generate a class instance.
    """

    parser = argparse.ArgumentParser(description='yue client')

    parser.add_argument('--username', required=True,
                    help='username')
    parser.add_argument('--password', required=False,
                    help='password')
    parser.add_argument('--hostname', dest='hostname',
                    default="https://localhost:4200",
                    help='the database connection string')

    subparsers = parser.add_subparsers()

    def unpack_args(endpoint, args):
        # deprecated, replace with _request_buider

        method = endpoint.methods[0]
        # use the arguments to construct the url for the request
        url = url_encode(endpoint.path, lambda v: getattr(args, v))

        # unclear what to do about null params
        params = []
        for name, _type, _default, _required in endpoint.params:
            params.append((name, getattr(args, name)))

        body = None
        _type, _json = endpoint.body
        if _type is not None or method in ["PUT", "POST"]:
            body = getattr(args, "data")

        # TODO: one of the options should be 'requires_auth'
        options = {}

        if params:
            options['params'] = {k: v for k, v in params}

        if body is not None:
            if body == "-":
                options['data'] = sys.stdin
            else:
                options['data'] = open(body, "rb")

        return [method, url, options]

    for endpoint in registered_endpoints:
        # need a way to hide/rename a _registered_endpoints
        # when it is registered

        name = endpoint.long_name.lower().replace("resource", "")

        # create the subparser
        doc = "%s" % (endpoint.path)
        end_parser = subparsers.add_parser(name, help=doc)
        end_parser.set_defaults(
            func=lambda args, endpoint=endpoint: unpack_args(endpoint, args))

        # parse the registered parameters, and generate optional arguments
        for name, _type, _default, _required in endpoint.params:
            end_parser.add_argument("--%s" % name,
                help="todo",
                default=_default,
                required=_required)

        # parse the URL path, and generate positional arguments
        for typename, varname in url_decode(endpoint.path):
            end_parser.add_argument(varname,
                help="todo")

        # todo: add optional methods, if more than 1, default to first

        # if the endpoint requires a body, add a final positional argument
        # used for uploading a document or stdin
        _type, _json = endpoint.body
        if _type is not None:
            end_parser.add_argument("data",
                help="file to upload (- for stdin)")

    return parser

