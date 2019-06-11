

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

        for endpoint in sorted(app._registered_endpoints_v2, key=lambda e: e.path):
            for method in sorted(endpoint.methods):

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

        # reformat the description
        # trim whitespace at the start of the lines
        d = endpoint.doc or ""
        count = 0
        for c in d:
            if c == '\n':
                count = 0
            elif c == ' ':
                count += 1
            else:
                break
        if count > 1:
            d = d.replace('\n' + ' ' * count, "\n")
        d = d.strip()
        desc['description'] = d

        desc['parameters'] = []

        if isinstance(endpoint.returns, list):
            desc['responses'] = {}
            for code in endpoint.returns:
                desc['responses'][str(code)] = {
                    "description": http.client.responses[code]
                }

        if isinstance(endpoint.returns, dict):
            desc['responses'] = {}
            for code, content in endpoint.returns.items():
                obj = desc['responses'][str(code)] = {
                    "description": http.client.responses[code]
                }

                if not isinstance(content, list):
                    content = [content]

                for model in content:
                    if model is None:
                        continue

                    if 'content' not in obj:
                        obj['content'] = {}

                    reg_name = self._reg_model(model)

                    mimetype = model.mimetype()

                    if isinstance(mimetype, str):
                        mimetype = [mimetype]

                    for m in mimetype:
                        obj['content'][m] = {
                            'schema': {'$ref': reg_name},
                        }
        else:
            desc['responses'] = {"200": {"description": "OK"}}

        _auth0 = {'basicAuth': endpoint.scope}
        _auth1 = {'tokenAuth': endpoint.scope}
        _auth = [[], [_auth0, _auth1]]

        desc['security'] = _auth[endpoint.auth]
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
            items = endpoint.body
            if not isinstance(items, list):
                items = [items]
            for model in items:
                if model and hasattr(model, 'mimetype'):
                    self._reg_body(desc, model)
                else:
                    sys.stderr.write("%s: oldstyle body\n" % endpoint.long_name)

        return path, desc

    def _reg_body(self, desc, model):

            reg_name = self._reg_model(model)

            mimetype = model.mimetype()

            if isinstance(mimetype, str):
                mimetype = [mimetype]

            content = {
                "schema": {
                    "$ref": reg_name
                }
            }

            if mimetype and 'requestBody' not in desc:
                desc['requestBody'] = {
                    "description": "TODO",
                    "required": True,
                    "content": {}
                }

            for m in mimetype:
                desc['requestBody']['content'][m] = content

    def _reg_model(self, model):

        obj = self['components']['schemas'][model.name()] = {
            "type": model.type()
        }

        if obj['type'] == 'object':
            obj["properties"] = model.model()
            _required = []
            for key, value in obj["properties"].items():
                if 'required' in value:
                    if value['required']:
                        _required.append(key)
                    del value['required']
            if _required:
                obj['required'] = _required
        elif obj['type'] == 'array':
            obj['items'] = model.schema()
        elif obj['type'] == 'stream':
            obj['type'] = "string"
            obj['format'] = "binary"

        return '#/components/schemas/' + model.name()

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
            sys.stderr.write("oldstyle parameter: %s\n" % param.name)
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
            parts = path[s + 1:e].split(":")
            name = parts[-1]
            path = path[:s] + ("{%s}" % name) + path[e + 1:]

            type_name = "path" if len(parts) > 1 else "string"
            p = {
                "in": "path",
                "name": name,
                "required": True,
                "description": "type: " + type_name,
                "schema": {'type': 'string'}
            }

            parameters.append(p)

            s = path.find('<')
            e = path.find('>')

        return path, parameters


def curldoc(app, host):

    for endpoint in sorted(app._registered_endpoints_v2, key=lambda e: e.path):
        for method in sorted(endpoint.methods):

            print("\n\n%s" % endpoint.long_name)
            cmd = []

            cmd.append("-X")
            cmd.append(method)

            params = []
            for param in endpoint.params:
                params.append("%s={%s}" % (param.name, param.name))

            for param in endpoint.headers:
                pass

            mimeschema = {}
            if method in ('POST', 'PUT'):

                cmd.append("-H")
                cmd.append("Content-Type='{Content-Type}'")
                items = endpoint.body

                if not isinstance(items, list):
                    items = [items]

                binary = False

                for model in items:
                    if model and hasattr(model, 'mimetype'):

                        name = model.name()
                        mimetype = model.mimetype()
                        if isinstance(mimetype, str):
                            mimetype = [mimetype]

                        type = model.type()
                        schema = {"type": type}
                        if type == 'object':
                            schema = model.model()

                        if type == 'array':
                            schema = [model.schema()]

                        if type == 'stream':
                            schema['type'] = "string"
                            schema['format'] = "binary"
                            binary = True

                        for m in mimetype:
                            mimeschema[m] = schema

                if binary:
                    cmd.append("--data-binary")
                else:
                    cmd.append("-d")

                cmd.append("@'upload-file'")

            url = "%s%s" % (host, endpoint.path)
            if params:
                url += '?' + '&'.join(params)

            cmd.append("'%s'" % url)

            print("curl %s" % (" ".join(cmd)))

            for mimetype, schema in sorted(mimeschema.items()):
                print("%s:" % mimetype)
                s = json.dumps(schema, cls=ObjectEncoder, indent=2)
                s = "    " + s.replace("\n", "\n    ")
                print(s)



