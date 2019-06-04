

import sys

from yueserver.app import YueApp, generate_client
from yueserver.config import Config

import json
import http

class ObjectEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Api):
            return obj.json()
        return obj

class Api(object):
    def __init__(self, **attrs):
        super(Api, self).__init__()
        self.attrs = attrs

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
        return json.dumps(self, cls=ObjectEncoder, **kwargs)

class ApiParameter(Api):
    def __init__(self, in_, **attrs):
        super(ApiParameter, self).__init__()
        self.attrs = attrs
        self.attrs['in'] = in_

    def json(self):
        return self.attrs

class ApiResponse(Api):
    def __init__(self):
        super(ApiResponse, self).__init__()

class ApiDescription(Api):
    def __init__(self):
        super(ApiDescription, self).__init__()

        self.tags = None
        self.summary = None
        self.description = None
        self.operationId = None
        self.parameters = None
        self.responses = None
        self.security = []
        self.requestBody = None

    def json(self):

        obj = {
            "tags": self.tags,
            "summary": self.summary,
            "description": self.description,
            "operationId": self.operationId,
            "parameters": [p.json() for p in self.parameters],
            "responses": self.responses,
            "security": self.security
        }
        if self.requestBody:
            obj['requestBody'] = self.requestBody

        return obj

class ApiObjectProperty(Api):
    def __init__(self, type, format):
        super(ApiObjectProperty, self).__init__()
        self.type = type
        self.format = format
        self.description = None
        self.enum = None

class ApiObjectDefinition(Api):

    pass

class ApiSecurityDefinition(Api):
    def __init__(self, type_, in_, **kwargs):
        super(ApiSecurityDefinition, self).__init__(**kwargs)
        self.type = type_
        self.attrs['in'] = in_

    def json(self):
        obj = {
            "type": self.type
        }
        obj.update(self.attrs)
        return obj

class ApiSecurityDefinitions(Api):
    """docstring for ApiSecurityDefinitions"""

    def json(self):
        return {k: v.json() for (k, v) in self.attrs.items()}

class OpenApi(Api):
    def __init__(self, app):
        super(OpenApi, self).__init__()

        self._generate(app)

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

        if 'url':
            self['info']['contact']['url'] = url
        elif 'url' in self['info']['contact']:
            del self['info']['contact']['url']

        if 'email':
            self['info']['contact']['email'] = email
        elif 'email' in self['info']['contact']:
            del self['info']['contact']['email']

        return self

    def license(self, name=None, url=None):

        if 'url':
            self['info']['license']['url'] = url
        elif 'info' in self['info']['license']:
            del self['info']['license']['url']

        if 'name':
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
        _auth = [[], [_auth0, _auth1]]

        for endpoint in app._registered_endpoints_v2:
            for method in endpoint.methods:

                desc = ApiDescription()
                path = endpoint.path

                if not path.startswith("/api"):
                    continue

                tag = endpoint.long_name.split('.')[0].replace("Resource", "")

                desc.tags = [tag]
                desc.summary = endpoint.long_name
                desc.description = endpoint.doc or ""
                desc.parameters = []
                # http error code => {description, schema}

                if isinstance(endpoint.returns, list):
                    desc.responses = {}
                    for code in endpoint.returns:
                        desc.responses[str(code)] = {"description": http.client.responses[code]}
                else:
                    desc.responses = {"200": {"description": "OK"}}


                desc.security = _auth[endpoint.auth]
                desc.operationId = endpoint.long_name

                path, desc.parameters = self._fmt_path(path)

                sys.stderr.write("%-8s %s %s\n" % (method, 'FT'[endpoint.auth], path))

                for param in endpoint.params:
                    _type = param.type
                    if hasattr(_type, 'schema'):
                        p = ApiParameter("query",
                            name=param.name,
                            required=_type.getRequired(),
                            description=_type.getDescription())
                        p['schema'] = _type.schema()
                    else:
                        # old style validators
                        p = ApiParameter("query",
                            name=param.name,
                            required=param.required,
                            description=param.doc)
                        p['schema'] = {'type': 'string'}
                    desc.parameters.append(p)

                for param in endpoint.headers:
                    _type = param.type
                    if hasattr(_type, 'schema'):
                        p = ApiParameter("header",
                            name=param.name,
                            required=_type.getRequired(),
                            description=_type.getDescription())
                        p['schema'] = _type.schema()
                    else:
                        p = ApiParameter("header",
                            name=param.name,
                            required=param.required,
                            description=param.doc)
                        p['schema'] = {'type': 'string'}  # TODO TYPES
                    desc.parameters.append(p)

                if method in ('POST', 'PUT'):
                    model = endpoint.body
                    if model and hasattr(model, 'mimetype'):

                        obj = openapi['components']['schemas'][model.name()] = {
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

                        desc.requestBody = {
                            "description": "TODO",
                            "required": True,
                            "content": content
                        }

                if path not in openapi['paths']:
                    openapi['paths'][path] = {}
                openapi['paths'][path][method.lower()] = desc

    def _fmt_path(self, path):

        parameters = []
        s = path.find('<')
        e = path.find('>')
        while s >= 0 and s < e:
            name = path[s + 1:e].split(":")[-1]
            path = path[:s] + ("{%s}" % name) + path[e + 1:]

            p = ApiParameter("path", name=name, required=True)
            p['schema'] = {'type': 'string'}
            parameters.append(p)

            s = path.find('<')
            e = path.find('>')

        return path, parameters
