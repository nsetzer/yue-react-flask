

import sys

from yueserver.app import YueApp, generate_client
from yueserver.config import Config

import json
import http

class ObjectEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        raise TypeError(type(obj))

class OpenApi(object):
    def __init__(self, app):
        super(OpenApi, self).__init__()
        self.attrs = {}

        self._generate(app)

    def set(self, attr, value):
        self.attrs[attr] = value

    def __setitem__(self, key, value):
        self.attrs[key] = value

    def get(self, key):
        return self.attrs[key]

    def __getitem__(self, key):
        return self.attrs[key]

    def json(self):
        return self.attrs

    def jsons(self, **kwargs):
        return json.dumps(self.attrs, cls=ObjectEncoder, **kwargs)

    def description(self, value):
        self['info']['description'] = value
        return self

    def title(self, value):
        self['info']['title'] = value
        return self

    def version(self, value):
        self['info']['version'] = value
        return self

    def contact(self, url=None, email=None):

        if url is not None:
            self['info']['contact']['url'] = url
        elif 'url' in self['info']['contact']:
            del self['info']['contact']['url']

        if email is not None:
            self['info']['contact']['email'] = email
        elif 'email' in self['info']['contact']:
            del self['info']['contact']['email']

        return self

    def license(self, name=None, url=None):

        if url is not None:
            self['info']['license']['url'] = url
        elif 'info' in self['info']['license']:
            del self['info']['license']['url']

        if name is not None:
            self['info']['license']['name'] = name
        elif 'name' in self['info']['license']:
            del self['info']['license']['name']

        return self

    def servers(self, value):
        self['servers'] = value
        return self

    def __str__(self):
        return self.jsons()

    def _generate(self, app):

        openapi = self

        openapi['openapi'] = '3.0.0'

        openapi['paths'] = {}

        openapi['servers'] = {}

        openapi['components'] = {}
        openapi['components']['schemas'] = {}

        openapi['info'] = {}
        self['info']['contact'] = {}
        self['info']['license'] = {}

        # todo: generate security using registered security settings
        # found inside the app
        openapi['components']['securitySchemes'] = {
            "basicAuth": {"type": "http", "scheme": "basic"},
            "tokenAuth": {"type": "apiKey", 'in': 'header', 'name': 'Authorization'},
        }
        _auth0 = {'basicAuth': []}
        _auth1 = {'tokenAuth': []}
        self._auth = [[], [_auth0, _auth1]]

        for endpoint in app._registered_endpoints_v2:
            for method in endpoint.methods:

                if not endpoint.path.startswith("/api"):
                    continue

                path, desc = self. _fmt_endpoint(method, endpoint)

                if path not in openapi['paths']:
                    openapi['paths'][path] = {}

                openapi['paths'][path][method.lower()] = desc

    def _fmt_endpoint(self, method, endpoint):

        desc = {}
        path = endpoint.path

        tag = endpoint.long_name.split('.')[0].replace("Resource", "")

        desc['tags'] = [tag]
        desc['summary'] = endpoint.long_name
        desc['description'] = endpoint.doc or ""
        desc['parameters'] = []

        if isinstance(endpoint.returns, list):
            desc['responses'] = {}
            for code in endpoint.returns:
                desc['responses'][str(code)] = {
                    "description": http.client.responses[code]
                }
        else:
            desc['responses'] = {"200": {"description": "OK"}}

        desc['security'] = self._auth[endpoint.auth]
        desc['operationId'] = endpoint.long_name

        path, desc['parameters'] = self._fmt_path(path)

        sys.stderr.write("%-8s %s %s\n" % (method, 'FT'[endpoint.auth], path))

        for param in endpoint.params:
            p = self._fmt_parameter("query", param)
            desc['parameters'].append(p)

        for param in endpoint.headers:
            p = self._fmt_parameter("header", param)
            desc['parameters'].append(p)

        if method in ('POST', 'PUT'):
            model = endpoint.body
            if model and hasattr(model, 'mimetype'):

                obj = self['components']['schemas'][model.name()] = {
                    "type": model.type()
                }

                if obj['type'] == 'object':
                    obj["properties"] = model.model()
                    obj['required'] = []
                    for key, value in obj["properties"].items():
                        if 'required' in value:
                            if value['required']:
                                obj['required'].append(key)
                            del value['required']
                elif obj['type'] == 'array':
                    obj['items'] = model.schema()
                elif obj['type'] == 'stream':
                    obj['type'] = "string"
                    obj['format'] = "binary"

                content = {}
                mimetype = model.mimetype()
                if isinstance(mimetype, str):
                    mimetype = [mimetype]

                for m in mimetype:
                    content[m] = {
                        "schema": {
                            "$ref": "#/components/schemas/" + model.name()
                        }
                    }

                desc['requestBody'] = {
                    "description": "TODO",
                    "required": True,
                    "content": content
                }

        return path, desc

    def _fmt_parameter(self, kind, param):
        _type = param.type
        if hasattr(_type, 'schema'):
            return {
                "in": kind,
                "name": param.name,
                "required": _type.getRequired(),
                "description": _type.getDescription(),
                "schema": _type.schema()
            }
        else:
            return {
                "in": kind,
                "name": param.name,
                "required": param.required,
                "description": param.doc,
                "schema": {'type': 'string'}
            }

    def _fmt_path(self, path):

        parameters = []
        s = path.find('<')
        e = path.find('>')
        while s >= 0 and s < e:
            name = path[s + 1:e].split(":")[-1]
            path = path[:s] + ("{%s}" % name) + path[e + 1:]

            p = {
                "in": "path",
                "name": name,
                "required": True,
                "description": "",
                "schema": {'type': 'string'}
            }

            parameters.append(p)

            s = path.find('<')
            e = path.find('>')

        return path, parameters
