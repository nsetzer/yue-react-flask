"""

GET, POST, HEAD, PUT, DELETE, TRACE, OPTIONS and CONNECT

HEAD : get but return headers only



JQ2020-11-06 12:27:10,265 - WARNING  - root - creating new storage path: s3://yueapp/app/userdata/eaa16329-3c66-4b8f-add4-0ce0587192d6/2020/11/06/ESnIhuJnRLaiyGhTgG4SJQ
2020-11-06 12:28:28,440 - INFO     - root - received all bytes for upload: 393607716
2020-11-06 12:28:29,003 - ERROR    - root - Unhandled Exception:  (current user: nsetzer):
Traceback (most recent call last):
  File "/opt/yueserver/yueserver/framework2/openapi.py", line 225, in wrapper
    return_value = f(resource, req)
  File "/opt/yueserver/yueserver/resource2/files.py", line 465, in upload
    encryption=request.query.crypt)
  File "/opt/yueserver/yueserver/service/filesys_service.py", line 399, in saveFile
    size = self._internalSave(user['id'], storage_path, stream, 4096)
  File "/opt/yueserver/yueserver/service/filesys_service.py", line 492, in _internalSave
    raise e
  File "/opt/yueserver/yueserver/service/filesys_service.py", line 466, in _internalSave
    self.fs.upload(inputStream, storage_path)
  File "/opt/yueserver/yueserver/dao/filesys/filesys.py", line 475, in upload
    return fs.upload(reader, path)
  File "/opt/yueserver/yueserver/dao/filesys/s3fs.py", line 332, in upload
    return bucket.upload_fileobj(reader, key, Callback=callback, Config=config)
  File "/usr/local/lib/python3.6/dist-packages/boto3/s3/inject.py", line 581, in bucket_upload_fileobj
    Callback=Callback, Config=Config)
  File "/usr/local/lib/python3.6/dist-packages/boto3/s3/inject.py", line 539, in upload_fileobj
    return future.result()
  File "/usr/local/lib/python3.6/dist-packages/s3transfer/futures.py", line 73, in result
    return self._coordinator.result()
  File "/usr/local/lib/python3.6/dist-packages/s3transfer/futures.py", line 233, in result
    raise self._exception
  File "/usr/local/lib/python3.6/dist-packages/s3transfer/tasks.py", line 126, in __call__
    return self._execute_main(kwargs)
  File "/usr/local/lib/python3.6/dist-packages/s3transfer/tasks.py", line 150, in _execute_main
    return_value = self._main(**kwargs)
  File "/usr/local/lib/python3.6/dist-packages/s3transfer/tasks.py", line 364, in _main
    **extra_args)
  File "/usr/local/lib/python3.6/dist-packages/botocore/client.py", line 320, in _api_call
    return self._make_api_call(operation_name, kwargs)
  File "/usr/local/lib/python3.6/dist-packages/botocore/client.py", line 623, in _make_api_call
    raise error_class(parsed_response, operation_name)
botocore.exceptions.ClientError: An error occurred (EntityTooSmall) when calling the CompleteMultipartUpload operation: Unknown
2020-11-06 12:28:29,011 - WARNING  - root - yueserver.resource2.files.FileSysResource.upload ran for 79039.377ms
2020-11-06 12:28:29,011 - INFO     - root - 00007FDFD23D0700 73.69.60.181:49870 HTTP/1.1 500  79058 POST     /api/fs/default/path/public/music/333.7z?mtime=1589539761&version=1&permission=511&crypt=system [-1]
2020-11-06 12:28:29,012 - ERROR    - root - received header: b'\x98\xd6\x0f\x18|jP\xe7LT\x97\xe8{\xd0\x08t5'
2020-11-06 12:28:29,012 - ERROR    - root - 00007FDFD23D0700 73.69.60.181:49870 n/a n/a      n/a header too large



2020-11-08 21:22:20,661 INFO     root :server.send_response:208: 00007F7DE3FFF700 209.107.190.170:38122 HTTP/1.1 200      0 GET      /favicon.ico [804]
2020-11-08 22:08:10,039 INFO     root :server.send_response:208: 00007F7DE3FFF700 74.120.14.35:45896 HTTP/1.1 200   1018 GET      / [804]
2020-11-08 22:08:10,117 INFO     root :server.send_response:208: 00007F7DE3FFF700 74.120.14.35:39802 HTTP/1.1 200     19 GET      / [804]
2020-11-08 23:14:41,469 INFO     root :server.send_response:208: 00007F7DE3FFF700 162.243.128.166:34180 HTTP/1.1 200     66 GET      /owa/auth/logon.aspx [804]
2020-11-09 00:41:17,122 INFO     root :server.send_response:208: 00007F7DE3FFF700 74.82.47.3:55106 HTTP/1.1 200    641 GET      / [804]

"""
import os
import sys
import io
import socket
import threading
import socketserver
import select
import gzip
import logging
from logging.handlers import RotatingFileHandler

import argparse
from datetime import datetime

from collections import defaultdict

from urllib.parse import urlparse, unquote
from http.client import responses

from yueserver.framework2.openapi import RegisteredEndpoint, OpenApi, curldoc
##--
from yueserver.framework2.server_core import readline, Namespace, \
    SocketFile, CaseInsensitiveDict, UploadChunkedFile, UploadMultiPartFile, \
    Response, Router

from yueserver.framework2.server import Site
from yueserver.framework2.openapi import Resource, \
    get, put, post, delete, \
    header, param, body, timed, returns, \
    String, BinaryStreamOpenApiBody, JsonOpenApiBody, OpenApiParameter

from yueserver.framework2.security import requires_no_auth, requires_auth, \
    register_handler, register_security, ExceptionHandler

from .config import Config

from .dao.db import db_connect, db_init_main
from .dao.filesys.filesys import FileSystem
from .dao.filesys.s3fs import BotoFileSystemImpl

from .service.audio_service import AudioService
from .service.transcode_service import TranscodeService
from .service.user_service import UserService
from .service.filesys_service import FileSysService
from .service.radio_service import RadioService

from .resource2.util import register_handlers
from .resource2.http import HttpResource
from .resource2.app import AppResource
from .resource2.user import UserResource
from .resource2.files import FileSysResource
from .resource2.library import LibraryResource
from .resource2.queue import QueueResource
##--

def parseArgs(argv, default_profile=None):
    """ parse the command line arguments used for launching an app

    builds an arg parser with the common options needed to create an app.
    """

    #encoding = "cp850"
    #if sys.stdout.encoding != encoding:
    #  sys.stdout = codecs.getwriter(encoding)(sys.stdout.buffer, 'strict')
    #if sys.stderr.encoding != encoding:
    #  sys.stderr = codecs.getwriter(encoding)(sys.stderr.buffer, 'strict')


    if default_profile is None:
        default_profile = "windev" if sys.platform == "win32" else "development"

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--config_dir', dest='config', default="./config",
                        help='enable verbose logging')
    parser.add_argument('-p', '--profile', dest='profile',
                        default=default_profile,
                        help='default profile to use (%s)' % default_profile)
    # workers and bind are for gunicorn support
    # todo: the default bind should be none
    # then use the config to set the default bind,
    #parser.add_argument('--bind', type=str, default="0.0.0.0:4200",
    #                    help="bind server to host:port")
    #parser.add_argument('-w', '--workers', type=int,
    #                    default=1,
    #                    help='number of workers')
    #parser.add_argument('appname', default='wsgi:app', nargs='?'
    #    help="the name of the app for running using wsgi (file:varname)")

    args, _ = parser.parse_known_args(argv[1:])


    #app.logger.handlers = gunicorn_logger.handlers
    #app.logger.setLevel(gunicorn_logger.level)

    return args

class Application(object):
    """docstring for Application"""
    def __init__(self, cfg):
        super(Application, self).__init__()

        self.cfg = cfg
        self.db = db_connect(self.cfg.database.url)
        self._endpoints = []

        # check that the database is configured.
        # the number of tables may not match if there are additional
        # test tables, but in general should be the same
        nbTablesExpected = len(self.db.metadata.tables.keys())
        nbTablesActual = len(self.db.engine.table_names())
        if not self.cfg.null and nbTablesExpected != nbTablesActual:
            logging.warning("database contains %d tables. expected %d." % (
                nbTablesActual, nbTablesExpected))

        if cfg.aws.endpoint is not None:

            logging.getLogger("botocore").setLevel(logging.WARNING)
            logging.getLogger("s3transfer").setLevel(logging.WARNING)

            aws = cfg.aws
            logging.info("configure s3 %s %s",
                aws.endpoint,
                aws.region)
            s3fs = BotoFileSystemImpl(
                aws.endpoint,
                aws.region,
                aws.access_key,
                aws.secret_key)
            FileSystem.register(BotoFileSystemImpl.scheme, s3fs)

        user_service = UserService(self.cfg, self.db, self.db.tables)
        filesys_service = FileSysService(self.cfg, self.db, self.db.tables)
        transcode_service = TranscodeService(self.cfg, self.db, self.db.tables)
        audio_service = AudioService(self.cfg, self.db, self.db.tables)

        self.http_router = Router()
        self.http_router.registerEndpoints(HttpResource().endpoints())

        self.tls_router = Router()

        app_resource = AppResource()
        app_resource.config = self.cfg
        app_resource.db = self.db

        user_resource = UserResource()
        user_resource.user_service = user_service

        filesys_resource = FileSysResource()
        filesys_resource.user_service = user_service
        filesys_resource.filesys_service = filesys_service

        library_resource = LibraryResource()
        library_resource.user_service = user_service
        library_resource.filesys_service = filesys_service
        library_resource.transcode_service = transcode_service
        library_resource.audio_service = audio_service

        queue_resource = QueueResource()
        queue_resource.user_service = user_service
        queue_resource.audio_service = audio_service

        self.registerEndpoints(user_resource.endpoints())
        self.registerEndpoints(filesys_resource.endpoints())
        self.registerEndpoints(library_resource.endpoints())
        self.registerEndpoints(queue_resource.endpoints())
        self.registerEndpoints(app_resource.endpoints())

        #self.endpoints()
        #sys.exit(1)
        user_resource.app_endpoints = self._endpoints

    def registerEndpoints(self, endpoints):
        self.tls_router.registerEndpoints(endpoints)

        endpts = []
        for resource, method, pattern, callback in endpoints:

            path = pattern
            name = callback.__func__.__qualname__
            doc = callback.__doc__

            params = []
            if hasattr(callback, '_params'):
                params = callback._params

            headers = []
            if hasattr(callback, '_headers'):
                headers = callback._headers

            body = None
            if hasattr(callback, '_body'):
                body = callback._body[0]

            returns = None
            if hasattr(callback, '_returns'):
                returns = callback._returns

            auth = None
            if hasattr(callback, '_auth'):
                auth = callback._auth

            scope = None
            if hasattr(callback, '_scope'):
                scope = callback._scope

            endpt = RegisteredEndpoint(path, name, doc, [method], params, headers, body, returns, auth, scope)
            endpts.append(endpt)

        self._endpoints.extend(endpts)

    def endpoints(self):


        #for line in curldoc(self._endpoints, "0.0.0.0"):
        #    print(line)

        #api = OpenApi(self._endpoints)
        #api.license("MIT", "https://mit-license.org/")
        #api.contact(None, "nsetzer@noreply.github.com")
        #api.version("0.0.0.0")
        #api.title("YueApp")
        #api.description("YueApp API Doc")
        #api.servers([{"url": "https://yueapp.duckdns.org"}])
        #with open("openapi.json", "w") as wf:
        #    wf.write(str(api))

        # for method, routes in self.tls_router.route_table.items():

            # for (regex, tokens, resource, callback) in routes:



        return self._endpoints

        #    RegisteredEndpoint(path, name, callback.__doc__,
        #        options['methods'], params, headers, body[0], returns, auth, scope)

    def run(self):

        self.site = Site("0.0.0.0")

        use_ssl = True
        if not os.path.exists(self.cfg.ssl.private_key):
            logging.info("no private key set")
            use_ssl = False

        elif not os.path.exists(self.cfg.ssl.certificate):
            logging.info("no certificate chain set")
            use_ssl = False

        if not use_ssl:
            self.site.listenTCP(self.tls_router, 4200)
        else:
            self.site.listenTCP(self.http_router, 4100)
            self.site.listenTLS(self.tls_router, 4200, self.cfg.ssl.certificate, self.cfg.ssl.private_key)

        self.site.start()

        self.site.join()

def main():
    #logging.basicConfig(level=logging.INFO)

    FORMAT = '%(asctime)s %(levelname)-8s %(name)s :%(module)s.%(funcName)s:%(lineno)d: %(message)s'
    logging.basicConfig(level=logging.INFO, format=FORMAT)

    args = parseArgs(sys.argv)

    app_cfg_path = os.path.join(args.config, args.profile, "application.yml")
    cfg = Config(app_cfg_path)

    formatter = logging.Formatter(FORMAT)
    # always add a rotating log handler
    root_logger = logging.getLogger(None)
    root_logger.setLevel(cfg.logging.level)
    log_path = os.path.join(cfg.logging.directory, cfg.logging.filename)
    handler = RotatingFileHandler(log_path,
        maxBytes=cfg.logging.max_size,
        backupCount=cfg.logging.num_backups)
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    logging.debug("root logger support: DEBUG")
    logging.info("root logger support: INFO")
    logging.warning("root logger support: WARNING")
    logging.error("root logger support: ERROR")

    register_handlers()

    app = Application(cfg)

    app.run()

if __name__ == "__main__":
    main()