

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

class ApiDocument(Api):
    def __init__(self, **kwargs):
        super(ApiDocument, self).__init__(**kwargs)

    def json(self):
        return self.attrs

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
        return {k: v.json() for (k,v) in self.attrs.items()}

def main():

    app = YueApp(Config.null())

    openapi = ApiDocument()

    openapi['openapi'] = '3.0.0'
    openapi['info'] = {
        'description': "todo",
        'version': "0.0.0",
        'title': "openapi Api",
        'termsOfService': "http://openapi.io/terms/",
        'contact': {"email": "nicksetzer@gmail.com"},
        'license': {"name": "MIT"}
    }

    openapi['servers'] = [
        {"url": "https://yueapp.duckdns.org"},
        {"url": "http://localhost:4200"}
    ]

    openapi['paths'] = {}

    openapi['components'] = {}
    openapi['components']['schemas'] = {}
    openapi['components']['securitySchemes'] = {
        "basicAuth": {"type": "http", "scheme": "basic"}
    }

    for endpoint in app._registered_endpoints:
        for method in endpoint.methods:

            desc = ApiDescription()
            path = endpoint.path

            if not path.startswith("/api"):
                continue

            tag = endpoint.long_name.split('.')[0].replace("Resource", "")

            desc.tags =[tag]
            desc.summary = ""
            desc.description = ""
            desc.parameters = []
            # http error code => {description, schema}

            if isinstance(endpoint.returns, list):
                desc.responses = {}
                for code in endpoint.returns:
                    desc.responses[str(code)] = {"description": http.client.responses[code]}
            else:
                desc.responses = {"200": {"description": "OK"}}

            desc.security = [[], [{'basicAuth': []}]][endpoint.auth]
            desc.operationId=endpoint.long_name

            s = path.find('<')
            e = path.find('>')
            while s >= 0 and s < e:
                name = path[s+1:e].split(":")[-1]
                path = path[:s] + ("{%s}" % name) + path[e+1:]

                p = ApiParameter("path", name=name, required=True)
                p['schema'] = {'type': 'string'} # TODO TYPES
                desc.parameters.append(p)

                s = path.find('<')
                e = path.find('>')

            sys.stderr.write("%-8s %s %s\n" % (method, 'FT'[endpoint.auth], path))

            for param in endpoint.params:
                # TODO: param.default
                p = ApiParameter("query",
                    name=param.name,
                    required=param.required,
                    description=param.doc)
                p['schema'] = {'type': 'string'} # TODO TYPES
                desc.parameters.append(p)

            for param in  endpoint.headers:
                # TODO: param.default
                p = ApiParameter("header",
                    name=param.name,
                    required=param.required,
                    description=param.doc)
                p['schema'] = {'type': 'string'} # TODO TYPES
                desc.parameters.append(p)

            if method in ('POST', 'PUT'):
                model = app._registered_models.get((endpoint.path, method), None)
                if model and hasattr(model, 'model'):

                    openapi['components']['schemas'][model.name()] = {
                        "type": model.type(),
                        "properties": model.model(),
                    }

                    desc.requestBody = {
                        "description": "TODO",
                        "required": True,
                        "content": {
                            model.mimetype(): {
                                "schema": {
                                    "$ref": "#/components/schemas/" + model.name()
                                }
                            }
                        }

                    }

            if path not in openapi['paths']:
                openapi['paths'][path] = {}
            openapi['paths'][path][method.lower()] = desc

    print(openapi.jsons(indent=2))

if __name__ == '__main__':
    main()
