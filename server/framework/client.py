
import json
import requests
import base64
import requests.exceptions as exceptions
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

import logging

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

    def set_session(self, session):
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

    def put(self, url, payload, **kwargs):
        return self._makeRequest(self._session.put, url, data=payload, **kwargs)

    def post(self, url, payload, **kwargs):
        """ Send a post request to the configured server

        url: the api endpoint (sans host and port)
        payload: the post body content

        Streaming uploads can be done by passing the payload as an iterator.
            For example, the output of a function which yields bytes.
            the iterator should yield bytes

        """
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

        kwargs['headers']["X-Cogito-Domain"] = self.domain
        if self.role:
            kwargs['headers']["X-Cogito-Role"]   = self.role

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
