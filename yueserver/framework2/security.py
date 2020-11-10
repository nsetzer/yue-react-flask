
"""
Helper functions for implementing Web Resources
"""
import logging

class HttpException(Exception):
    def __init__(self, message, code=400):
        super(HttpException, self).__init__(message)
        self.status = code

class ExceptionHandler(object):

    def handle(self, resource, request, ex):
        raise NotImplementedError

_handlers = []

def register_handler(hdlr):
    _handlers.append(hdlr)

__g_features = set()
def __add_feature(features):
    """record features used by this application

    Every decorator adds the feature used to this set.
    this allows listing of all features used by the application
    """
    global __g_features
    if features is not None:
        for f in features:
            __g_features.add(f)

def get_features():
    return frozenset(__g_features)

_security = []

def register_security(hdlr):

    _security.append(hdlr)

def requires_no_auth(f):
    f._auth = False
    f._handlers = _handlers
    return f

def requires_auth(features=None):

    if features is None:
        features = []
    elif isinstance(features, str):
        features = [features]
    __add_feature(features)

    def impl(f):
        f._auth = True
        f._scope = features
        f._security = _security
        f._handlers = _handlers

        return f
    return impl


