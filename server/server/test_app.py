import os
import unittest
import tempfile
import json
import time

from .app import AppResource, YueApp, TestApp
from ..framework.application import FlaskApp
from ..framework.web_resource import WebResource

from ..service.audio_service import AudioService
from ..service.transcode_service import TranscodeService
from ..service.user_service import UserService

from .config import Config

from ..dao.db import db_connect, db_remove, db_init_main

from .util import get_features

class AppTestCase(unittest.TestCase):

    db_name = "AppTestCase"

    @classmethod
    def setUpClass(cls):

        cls.app = TestApp(cls.__name__);

        cls.app.add_resource(cls.app.resource_app)

    @classmethod
    def tearDownClass(cls):
        cls.app.tearDown()

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_features(self):
        # todo: a test which counts registered features, looking for changes

        cfg_features = self.app.env_cfg['features']
        all_features = get_features()
        for feat in all_features:
            if feat not in cfg_features:
                self.app.log.error("missing: %s" % feat)

        for feat in cfg_features:
            if feat not in all_features:
                self.app.log.error("unused: %s" % feat)

        self.assertEqual(len(cfg_features), len(all_features))

    def test_health(self):
        with self.app.test_client() as app:
            result = app.get("/health")
            self.assertEqual(result.status_code, 200)

    def test_index_001(self):
        """ assert that the default endpoint returns the application bundle"""
        with self.app.test_client() as app:
            result = app.get("/")
            self.assertEqual(result.status_code, 200)
            doc = result.data.decode("utf-8")
            self.assertTrue(doc.startswith("<!DOCTYPE html>"))

    def test_index_002(self):
        """ assert that the default endpoints return the application bundle"""
        with self.app.test_client() as app:
            result = app.get("/undefined")
            self.assertEqual(result.status_code, 200)
            doc = result.data.decode("utf-8")
            self.assertTrue(doc.startswith("<!DOCTYPE html>"))

def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AppTestCase)
    unittest.TextTestRunner().run(suite)

if __name__ == '__main__':
    main()
