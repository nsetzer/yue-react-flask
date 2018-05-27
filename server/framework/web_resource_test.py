import os
import unittest
import json
import time
import random

from ..config import Config
from .web_resource import WebResource, \
    get, post, put, delete, param, body, compressed, httpError, \
    int_range, int_min, send_file as send_file_v2, send_generator, \
    local_file_generator
from .application import FlaskApp

from flask import g, send_file

class TestResource(WebResource):
    def __init__(self):
        super(TestResource, self).__init__("/api/test")

    @get("file1")
    def send_file_1(self):
        return send_file("./test/r160.mp3")

    @get("file2")
    def send_file_2(self):
        return send_file_v2("./test/r160.mp3")

    @get("file3")
    def send_file_3(self):
        path = "./test/r160.mp3"
        name = os.path.split(path)[1]
        size = os.stat(path).st_size
        return send_generator(local_file_generator(path), name, file_size=size)


class WebResourceTestCase(unittest.TestCase):

    def _check_headers_equal(self, r1, r2):

        # check that a certain subset of headers are equal
        for h in ['Content-Length', 'Content-Type']:
            self.assertEqual(r1.headers[h], r2.headers[h])

        if r1.headers.has_key('Range'):
            self.assertEqual(r1.headers['Range'], r2.headers['Range'])



    def test_send_file_1(self):

        testApp = FlaskApp(Config.null())
        testApp.add_resource(TestResource())

        with testApp.test_client() as app:
            response1 = app.get("/api/test/file1")
            #print("v1: %s\n" % response1.status_code,response1.headers)

            response2 = app.get("/api/test/file2")
            #print("v2: %s\n" % response2.status_code,response2.headers)

            self._check_headers_equal(response1, response2)

            response3 = app.get("/api/test/file3")
            #print("v3: %s\n" % response3.status_code,response3.headers)
            self._check_headers_equal(response1, response3)

    def test_send_file_2(self):

        testApp = FlaskApp(Config.null())
        testApp.add_resource(TestResource())

        with testApp.test_client() as app:
            headers = {"Range": "bytes 0-1024/1024"}
            response1 = app.get("/api/test/file1", headers=headers)
            #print("v1: %s\n" % response1.status_code,response1.headers)

            response2 = app.get("/api/test/file2", headers=headers)
            #print("v2: %s\n" % response2.status_code,response2.headers)
            self._check_headers_equal(response1, response2)

            # this test proves that, by not setting direct_passthrough
            # range requests are still supported, because file wrapper
            # and that send_file_v2 is not required.
            response3 = app.get("/api/test/file3", headers=headers)
            #print("v2: %s\n" % response2.status_code,response2.headers)
            self._check_headers_equal(response1, response3)

def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(WebResourceTestCase)
    unittest.TextTestRunner().run(suite)

if __name__ == '__main__':
    main()
