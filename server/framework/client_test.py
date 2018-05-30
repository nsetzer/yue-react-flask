
import os
import sys
import unittest
import tempfile
import json
import time

from io import StringIO

from .client import (split_auth, AuthenticatedRestClient,
    RegisteredEndpoint, Parameter, FlaskAppClient, generate_argparse,
    ClientException, ParameterException)

test_endpoints = [
    RegisteredEndpoint("/api/get_json", "TestResource.get_json",
        "test documentation", ['GET'],
        [Parameter("align", str, "left", False, "")], (None, None)),
    RegisteredEndpoint("/api/put_json", "TestResource.put_json",
        "test documentation", ['PUT'], [], ('json', 'application/json')),
    RegisteredEndpoint("/api/post_json", "TestResource.post_json",
        "test documentation", ['POST'], [], ('json', 'application/json')),

    RegisteredEndpoint("/api/delete", "TestResource.delete",
        "test documentation", ['DELETE'], [], (None, None)),

    # same as get_json, with a required query parameter
    RegisteredEndpoint("/api/get_json_2", "TestResource.get_json_2",
        "test documentation", ['GET'],
        [Parameter("align", str, "left", True, "")], (None, None)),

    RegisteredEndpoint("/api/user/<user>", "TestResource.get_user",
        "test documentation", ['GET'], [], (None, None)),
    RegisteredEndpoint("/api/path/<path:ResourePath>", "TestResource.get_path",
        "test documentation", ['GET'], [], (None, None)),

    RegisteredEndpoint("/api/post_file", "TestResource.post_file",
        "test documentation", ['POST'], [], ('json', 'application/json')),

]

class CaptureOutput(object):
    """docstring for CaptureOutput"""
    def __init__(self):
        self._stdout = None
        self._stderr = None

        self.s_stdout = StringIO()
        self.s_stderr = StringIO()

    def __enter__(self):
        self._stdout = sys.stdout
        self._stderr = sys.stderr

        sys.stdout = self.s_stdout
        sys.stderr = self.s_stderr

        return self

    def __exit__(self, type, value, traceback):
        sys.stdout = self._stdout
        sys.stderr = self._stderr

    def stdout(self):
        self.s_stdout.flush()
        return self.s_stdout.getvalue()

    def stderr(self):
        self.s_stderr.flush()
        return self.s_stderr.getvalue()

class TestResponse(object):
    """docstring for TestResponse"""
    def __init__(self, url, options, status_code, body=None):
        super(TestResponse, self).__init__()

        self.request_url = url
        self.request_options = options

        self._body = body
        self.status_code = status_code

        self.history = []

    def json(self):
        return json.loads(self._body)

    def iter_content(self):
        return [self._body]

class TestSession(object):
    """docstring for TestSession"""
    def __init__(self):
        super(TestSession, self).__init__()

        self.get = self._request_impl
        self.put = self._request_impl
        self.post = self._request_impl
        self.delete = self._request_impl

        self.status_code = 200
        self.response_body = json.dumps({'result': None})

    def _request_impl(self, url, **kwargs):
        return TestResponse(url, kwargs, self.status_code, self.response_body)

class ClientTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_split_auth(self):

        u, d, r = split_auth("username")
        self.assertEqual(u, "username")
        self.assertEqual(d, "")
        self.assertEqual(r, "")

        u, d, r = split_auth("username@domain")
        self.assertEqual(u, "username")
        self.assertEqual(d, "domain")
        self.assertEqual(r, "")

        u, d, r = split_auth("username@domain/role")
        self.assertEqual(u, "username")
        self.assertEqual(d, "domain")
        self.assertEqual(r, "role")

    def test_client_get(self):

        client = AuthenticatedRestClient(
            "localhost", "admin", "admin", "test", "test")
        client.setSession(TestSession())

        response = client.get("/api/get_json")

        self.assertEqual(response.request_url, "localhost/api/get_json")
        self.assertTrue('headers' in response.request_options)
        token = response.request_options['headers']['Authorization']
        self.assertEqual(token, 'Basic YWRtaW46YWRtaW4=')

    def test_client_put(self):

        client = AuthenticatedRestClient(
            "localhost", "admin", "admin", "test", "test")
        client.setSession(TestSession())

        response = client.put("/api/put_json", data=b"payload")

        self.assertEqual(response.request_url, "localhost/api/put_json")
        self.assertEqual(response.request_options['data'], b"payload")

    def test_client_post(self):

        client = AuthenticatedRestClient(
            "localhost", "admin", "admin", "test", "test")
        client.setSession(TestSession())

        response = client.post("/api/post_json", data=b"payload")
        self.assertEqual(response.request_url, "localhost/api/post_json")
        self.assertEqual(response.request_options['data'], b"payload")

        response = client.post("/api/post_json", data=b"", json=True)
        self.assertEqual(response.request_url, "localhost/api/post_json")
        headers = response.request_options['headers']
        self.assertEqual(headers['Content-Type'], "application/json")

    def test_client_delete(self):

        client = AuthenticatedRestClient(
            "localhost", "admin", "admin", "test", "test")
        client.setSession(TestSession())

        response = client.delete("/api/delete")

        self.assertEqual(response.request_url, "localhost/api/delete")

class ParserTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        cls.parser = generate_argparse(test_endpoints)

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_get(self):

        # check that the parser works with a simple example
        args = self.parser.parse_args([
            "--host=localhost",
            "--username=admin",
            "--password=admin",
            "test.get_json"])

        self.assertEqual(args.host, "localhost")
        method, url, options = args.func(args)
        self.assertEqual(method, "get")
        self.assertEqual(url, "/api/get_json")

    def test_put(self):

        args = self.parser.parse_args([
            "--host=localhost",
            "--username=admin",
            "--password=admin",
            "test.put_json",
            "-"])

        method, url, options = args.func(args)
        self.assertEqual(method, "put")
        self.assertEqual(url, "/api/put_json")
        self.assertEqual(options['data'], sys.stdin.buffer)

    def test_post(self):

        args = self.parser.parse_args([
            "--host=localhost",
            "--username=admin",
            "--password=admin",
            "test.post_json",
            "-"])

        method, url, options = args.func(args)
        self.assertEqual(method, "post")
        self.assertEqual(url, "/api/post_json")
        self.assertEqual(options['data'], sys.stdin.buffer)

    def test_post_file(self):

        args = self.parser.parse_args([
            "--host=localhost",
            "--username=admin",
            "--password=admin",
            "test.post_json",
            "./test/r160.mp3"])

        method, url, options = args.func(args)
        self.assertEqual(method, "post")
        self.assertEqual(url, "/api/post_json")
        # self.assertEqual(options['data'], sys.stdin)
        file_length = len(options['data'].read())
        with open("./test/r160.mp3", "rb") as rb:
            actual_length = len(rb.read())
        self.assertTrue(file_length, actual_length)

    def test_delete(self):

        args = self.parser.parse_args([
            "--host=localhost",
            "--username=admin",
            "--password=admin",
            "test.delete"])

        method, url, options = args.func(args)
        self.assertEqual(method, "delete")
        self.assertEqual(url, "/api/delete")

    def test_url_substitution(self):

        # check that the parser works with a simple example
        args = self.parser.parse_args([
            "--host=localhost",
            "--username=admin",
            "--password=admin",
            "test.get_user",
            "admin"])

        method, url, options = args.func(args)
        self.assertEqual(method, "get")
        self.assertEqual(url, "/api/user/admin")

    def test_url_substitution_typed(self):

        # check that the parser works with a simple example
        args = self.parser.parse_args([
            "--host=localhost",
            "--username=admin",
            "--password=admin",
            "test.get_path",
            "test"])

        method, url, options = args.func(args)
        self.assertEqual(method, "get")
        self.assertEqual(url, "/api/path/test")

    def test_generate_help(self):

        # check the arg parse help format...
        with CaptureOutput() as cap:
            with self.assertRaises(SystemExit):
                self.parser.parse_args(['-h'])

            self.assertTrue("test.get_json" in cap.stdout())
            self.assertTrue("positional arguments" in cap.stdout())

class FlaskClientTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        rest_client = AuthenticatedRestClient(
            "localhost", "admin", "admin", "test", "test")
        cls.session = TestSession()
        rest_client.setSession(cls.session)

        cls.client = FlaskAppClient(rest_client, test_endpoints)

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_endpoints(self):

        endpoints = set(self.client.endpoints())

        self.assertEqual(len(endpoints), len(test_endpoints))
        self.assertTrue('test_get_json' in endpoints)
        self.assertTrue('test_delete' in endpoints)

    def test_get_json(self):

        response = self.client.test_get_json()
        self.assertEqual(response.request_url, "localhost/api/get_json")
        self.assertEqual(response.json()['result'], None)

        self.session.status_code = 400
        body = self.session.response_body
        self.session.response_body = json.dumps({'error': 'invalid'})
        response = self.client.test_get_json()
        with self.assertRaises(ClientException):
            response.json()
        self.session.response_body = body
        self.session.status_code = 200

        response = self.client.test_get_json(align="right")
        self.assertEqual(response.request_url, "localhost/api/get_json")
        params = response.request_options['params']
        self.assertEqual(params['align'], "right")

    def test_method_with_unknown_parameter(self):
        # an illegal key name should throw an error when given
        with self.assertRaises(ParameterException):
            response = self.client.test_get_json(param_dne="dne")

    def test_post_json(self):
        payload = json.dumps({'content': None})
        response = self.client.test_post_json(payload)
        self.assertEqual(response.request_url, "localhost/api/post_json")
        headers = response.request_options['headers']
        self.assertEqual(headers['Content-Type'], 'application/json')

def main():
    suite = unittest.TestSuite()

    load = unittest.defaultTestLoader.loadTestsFromTestCase
    suite.addTests(load(ClientTestCase))
    suite.addTests(load(ParserTestCase))
    suite.addTests(load(FlaskClientTestCase))

    unittest.TextTestRunner().run(suite)

if __name__ == '__main__':
    main()