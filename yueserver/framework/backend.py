
import struct
import socket
import base64
import hashlib
import sys
import threading
import signal
import time
import os
import re
import weakref
import io
import logging
import uuid
import json
import time
import posixpath
import traceback
from threading import Thread, Condition, Lock

from urllib.parse import urlparse

from . import gui
from .web_resource import WebResource, \
    websocket, get, post, put, delete, compressed, httpError

from flask import jsonify, g, request, send_from_directory, make_response
from urllib.parse import unquote

from fnmatch import fnmatch

import yueserver

"""
    - auto detect need to page refresh: window.location.reload()
"""

#  <script type="text/javascript" src="//cdnjs.cloudflare.com/ajax/libs/socket.io/2.0.4/socket.io.slim.js"></script>
js_body_end = """
        <link rel="stylesheet" type="text/css" href="/res/style.css">
        <script type="text/javascript" src="/res/socketio.slim.2.0.4.js"></script>
        <script>
        // from http://stackoverflow.com/questions/5515869/string-length-in-bytes-in-javascript
        // using UTF8 strings I noticed that the javascript .length of a string returned less
        // characters than they actually were
        var pendingSendMessages = [];
        var socket = null;
        var comTimeout = null;
        var failedConnections = 0;
        var intervalID = null;

        var namespace = '/api/ws'
        var url = document.location.protocol + '//' + document.domain + ':' + location.port + namespace

        function openSocket(){

            try{

                socket = io.connect(url);

                socket.on('connect', websocketOnOpen);
                socket.on('reconnect', websocketOnReconnect);
                socket.on('disconnect', websocketOnClose);
                socket.on('gui_reload', websocketOnReload);
                socket.on('gui_show', websocketOnShow);
                socket.on('gui_update', websocketOnUpdate);
                socket.on('gui_exec', websocketOnExec);

            } catch(ex) {
                socket=false;
                console.log(ex)
                alert('websocket not supported or server unreachable: ' + url);
            }
        }

        function websocketOnOpen(evt) {
            console.log('websocket: open');
            socket.send('connect', '');

            try {
                document.getElementById("loading").style.display = 'none';
            } catch(err) {
                console.log('Error hiding loading overlay ' + err.message);
            }
        };

        function websocketOnReconnect(attemptNumber) {

            console.log("successfully reconnected. attempt: " + attemptNumber);
        };

        function websocketOnClose(evt){
            console.log('websocket: close');
            try {
                document.getElementById("loading").style.display = '';
            } catch(err) {
                console.log('Error hiding loading overlay ' + err.message);
            }
        };

        function websocketOnShow (msg) {
            msg = JSON.parse(msg)
            var idElem = msg['id']
            var content = msg['repr']

            document.body.innerHTML = '<div id="loading" style="display: none;"><div id="loading-animation"></div></div>';
            document.body.innerHTML += msg['repr'];
        }

        function websocketOnUpdate (msg) {
            msg = JSON.parse(msg)
            var idElem = msg['id']
            var content = msg['repr']

            var focusedElement=-1;
            if (document.activeElement)
            {
                focusedElement = document.activeElement.id;
            }

            var elem = document.getElementById(idElem);
            if (elem == null) {
                console.warn("unable to get " + idElem)
            }

            try{
                elem.insertAdjacentHTML('afterend', content);
                elem.parentElement.removeChild(elem);
            } catch(e) {
                /*Microsoft EDGE doesn't support insertAdjacentHTML for SVGElement*/
                var ns = document.createElementNS("http://www.w3.org/2000/svg",'tmp');
                ns.innerHTML = content;
                elem.parentElement.replaceChild(ns.firstChild, elem);
            }

            if (focusedElement !== "") {
                var elemToFocus = document.getElementById(focusedElement);
                if( elemToFocus != null ){
                    document.getElementById(focusedElement).focus();
                }
            }
        }

        function websocketOnExec (msg) {
            try {
                console.log(msg);
                eval(msg);
            } catch(e) {
                console.debug(msg);
                console.debug(e.message);
            };
        }

        function websocketOnReload (msg) {
            // web socket connected, but the session does not exist anymore
            window.location.reload()
        }

        var sendCallbackParam = function (widgetID,functionName,params /*a dictionary of name:value*/){
            var state = {
                id: widgetID,
                method: functionName,
                params: (params==null)?{}:params
            };
            socket.emit("gui_widget_rpc", JSON.stringify(state));
        };

        var sendCallback = function (widgetID,functionName){
            // call method with no parameters
            sendCallbackParam(widgetID,functionName,null);
        };

        function uploadFileV2(elem, widgetID, urlbase) {
            console.log(urlbase);
            console.log(elem.files.length)

            var myStringArray = ["Hello","World"];
            var arrayLength = elem.files.length;
            for (var i = 0; i < elem.files.length; i++) {
                var file = elem.files[i];

                console.log(file);

                var filepath = urlbase + file.name;
                var url = '/gui/upload';

                var xhr = new XMLHttpRequest();
                xhr.open('POST', url, true);
                xhr.setRequestHeader('filename', file.name);
                xhr.setRequestHeader('filepath', filepath);
                xhr.onreadystatechange = function() {
                    if (xhr.readyState == 4 && xhr.status == 200) {
                        var params={};
                        params['filename'] = file.name;
                        params['filepath'] = filepath;
                        sendCallbackParam(widgetID, 'onsuccess', params);
                        console.log('upload success: ' + file.name);
                    }else if(xhr.status == 400){
                        var params={};
                        params['filename'] = file.name;
                        params['filepath'] = filepath;
                        sendCallbackParam(widgetID, 'onfailure', params);
                        console.log('upload failed: ' + file.name);
                    }
                };

                var fd = new FormData();
                fd.append('upload', file);
                xhr.send(fd);
            }
        }

        function uploadFile(widgetID, eventSuccess, eventFail, eventData, file){
            var url = '/';
            var xhr = new XMLHttpRequest();
            var fd = new FormData();
            xhr.open('POST', url, true);
            xhr.setRequestHeader('filename', file.name);
            xhr.setRequestHeader('listener', widgetID);
            xhr.setRequestHeader('listener_function', eventData);
            xhr.onreadystatechange = function() {
                if (xhr.readyState == 4 && xhr.status == 200) {
                    /* Every thing ok, file uploaded */
                    var params={};params['filename']=file.name;
                    sendCallbackParam(widgetID, eventSuccess,params);
                    console.log('upload success: ' + file.name);
                }else if(xhr.status == 400){
                    var params={};params['filename']=file.name;
                    sendCallbackParam(widgetID,eventFail,params);
                    console.log('upload failed: ' + file.name);
                }
            };
            fd.append('upload_file', file);
            xhr.send(fd);
        };

        function downloadFile(widgetID, fileId, password) {
            var postData = new FormData();

            // https://stackoverflow.com/questions/22724070/
            var xhr = new XMLHttpRequest();
            xhr.open('GET', '/api/fs/public/' + fileId);
            console.log(password)
            console.log(!password)
            console.log(password.length > 0)
            console.log(!password && password.length > 0)
            if (password.length > 0) {
                console.log("setting header");
                xhr.setRequestHeader('X-YUE-PASSWORD', password);
            }
            xhr.responseType = 'blob';
            xhr.onload = function (this_, event_) {
                var blob = this_.target.response;


                console.log(blob)
                console.log(this_.target.status)

                if (!blob || this_.target.status != 200) {
                    var params={};
                    params['status'] = this_.target.status;
                    sendCallbackParam(widgetID, 'onfailure', params);
                } else {
                    var contentDispo = xhr.getResponseHeader('Content-Disposition');
                    // https://stackoverflow.com/a/23054920/
                    var fileName = contentDispo.match(/filename[^;=\\n]*=((['"]).*?\\2|[^;\\n]*)/)[1];
                    saveBlob(blob, fileName);
                    sendCallbackParam(widgetID, 'onsuccess', null);
                }
            }
            xhr.send(postData);
        }

        function saveBlob(blob, fileName) {
            var a = document.createElement('a');
            a.href = window.URL.createObjectURL(blob);
            a.download = fileName;
            a.dispatchEvent(new MouseEvent('click'));
        }

        function saveOrOpenBlob(blob, fileName) {
            window.requestFileSystem = window.requestFileSystem || window.webkitRequestFileSystem;
            window.requestFileSystem(window.TEMPORARY, 1024 * 1024, function (fs) {
                fs.root.getFile(fileName, { create: true }, function (fileEntry) {
                    fileEntry.createWriter(function (fileWriter) {
                        fileWriter.addEventListener("writeend", function () {
                            window.location = fileEntry.toURL();
                        }, false);
                        fileWriter.write(blob, "_blank");
                    }, function () { });
                }, function () { });
            }, function () { });
        }

        window.onpopstate = function (event) {
            var state = {
                location: '' + document.location,
                cookie: document.cookie
            }
            socket.emit('gui_set_location', JSON.stringify(state));
        }

        openSocket();

        </script>"""

def get_method_by_name(root_node, name):
    """
    get an RPC method by name from a widget.
    """
    val = None
    # limit the scope of what can be accesed, only
    # event connectors prefixed with "on" can be accessed remotely
    if name.startswith("on"):
        if hasattr(root_node, name):
            attr = getattr(root_node, name)
            if isinstance(attr, gui.ClassEventConnector):
                val = attr
    if val is None:
        logging.warning("%s has no method %s" % (root_node, name))
    return val

class InvalidRoute(Exception):
    """thrown if the user requests an invalid route"""
    pass

class AppServiceException(Exception):
    """docstring for AppServiceException"""
    def __init__(self, status, message):
        super(AppServiceException, self).__init__(message)
        self.status = status

class AppRoute(object):
    def __init__(self, url, params=None, cookies=None):
        """
        url: the document url, e.g. "/r/worldnews"
        params: optional parameter dict built from the request query parameters
        cookies: optional dictionary containing HTTP cookies
        """
        super(AppRoute, self).__init__()

        if not isinstance(url, str):
            url = "/".join(url)

        if not url.startswith("/"):
            url = "/" + url

        self.url = url
        self.params = params or {}
        self.cookies = cookies or {}

    def update(self, url, params=None, cookies=None):

        self.url = posixpath.join(self.url, url)

        if params is not None:
            self.params.update(params)

        if cookies is not None:
            self.cookies.update(cookies)

    def getUrlParts(self):
        return [s for s in self.url.split("/") if s]

    def getUrl(self):
        return self.url

    def setUrl(self, url):
        self.url = url

    def getParams(self):
        return self.params

    def setParams(self, params):
        self.params = params or {}

    def getCookies(self):
        return self.cookies

    def setCookies(self, cookies):
        self.cookies = cookies or {}

    def getLocation(self):
        s = ["%s=%s" % x for x in sorted(self.params.items())]
        if s:
            return "%s?%s" % (self.url, ''.join(s))
        return "%s" % self.url

    def __str__(self):
        return "<AppRoute(%s)>" % (self.getLocation())

    def __repr__(self):
        return self.__str__()

    def match(self, path):
        return fnmatch(self.url, path)

    def get_cookie(self, cookie_name):
        return self.cookies.get(cookie_name, "")

class AppSessionManager(Thread):

    """
    sessions cannot be deleted when the last websocket disconnects
    in case of the user accidentally closing a tab, network issues etc.
    instead check for sessions with no sockets that have not been updated
    for some time and remove them
    """

    MAX_SESSION_AGE = 600
    SLEEP_INTERVAL = 60  # seconds

    def __init__(self, service):
        super(AppSessionManager, self).__init__()
        self.alive = True
        self.service = service

        self.lock_kill = Lock()
        self.condvar_kill = Condition(self.lock_kill)

        #traceback.print_stack()
        return

    def run(self):

        print(">>> Creating Session Manager Thread")

        with self.lock_kill:
            while self.alive:

                # TODO: use a mutex to wake this thread up when there are sessions
                # let it sleep indefinitly as long as there are no sessions

                # get a list of candidate sessions to remove
                sessionIds = set()

                for sessionId, client in self.service.clients.items():
                    if client.socket_timeout() > self.MAX_SESSION_AGE:
                        sessionIds.add(sessionId)

                for sessionId in sessionIds:
                    del self.service.clients[sessionId]
                    self.service._diag("removing session %s" % sessionId)

                self.condvar_kill.wait(self.SLEEP_INTERVAL)
        logging.info("Gui Session Managger thread exited.")

    def kill(self):

        with self.lock_kill:
            self.alive = False
            self.condvar_kill.notify_all()


class AppClient(object):
    """docstring for AppClient"""
    def __init__(self, **kwargs):
        super(AppClient, self).__init__()

        self.update_lock = threading.RLock()

        # TODO: synchronous bug, if initialized to "/"
        # then the first time we route to "/" will not
        # be signaled
        # on getHtml, set THIS location based on the route used
        self.location = "not-set"

        self.css_head = kwargs.get("css_head", "")
        self.html_head = kwargs.get("html_head", "")
        self.js_head = kwargs.get("js_head", "")
        self.js_body_start = kwargs.get("js_body_start", "")
        self.html_body_start = kwargs.get("html_body_start", "")
        self.html_body_end = kwargs.get("html_body_end", "")
        self.js_body_end = kwargs.get("js_body_end", "")

        self.websockets = set()
        self._update_time = None  # set to the time the last session is removed

        self.title = ""

        self._socket_send = None

        self.instance_registry = weakref.WeakValueDictionary()
        self.instance_counter = 0

    def createInstanceId(self):
        self.instance_counter += 1
        return "wd%08d" % self.instance_counter

    def register(self, wid, widget):
        self.instance_registry[wid] = widget

    def main(self, *_):
        """ Subclasses of App class *must* declare a main function
            that will be the entry point of the application.
            Inside the main function you have to declare the GUI structure
            and return the root widget. """
        raise NotImplementedError("Applications must implement 'main()' function.")

    def _idle_loop(self):
        """ This is used to exec the idle function in a safe context and a separate thread
        """
        while not self._stop_update_flag:
            time.sleep(self.update_interval)
            with self.update_lock:
                try:
                    self.idle()
                except:
                    self._log.error("exception in App.idle method", exc_info=True)
                if self._need_update_flag:
                    try:
                        self.do_gui_update()
                    except:
                        self._log.error('''exception during gui update. It is advisable to
                            use App.update_lock using external threads.''', exc_info=True)

    def idle(self):
        """ Idle function called every UPDATE_INTERVAL before the gui update.
            Useful to schedule tasks. """
        pass

    def _need_update(self, emitter=None):
        if self.update_interval == 0:
            # no interval, immediate update
            self.do_gui_update()
        else:
            # will be updated after idle loop
            self._need_update_flag = True

    def do_gui_update(self):
        """ This method gets called also by Timer, a new thread, and so needs to lock the update
        """

        state = AppRoute(*self.root.get_route())
        location = state.getLocation()
        if location != self.location:
            self.setLocation(location)

        changed_widget_dict = {}
        self.root.repr(changed_widget_dict)

        # TODO: if the change for the widget is only append
        # (e.g. adding to a list)
        # then send a different update signal for only the new values
        # var div = document.getElementById('divID');
        # div.innerHTML += 'appended items';
        # add the ability to record the type of child changes
        for widget in changed_widget_dict.keys():
            html = changed_widget_dict[widget]
            _id = str(widget.identifier)
            msg = json.dumps({"id": _id, "repr": html})
            self.socket_send("gui_update", msg)
        self._need_update_flag = False

    #def set_root_widget(self, widget):
    #    self.root = widget
    #    self.root.disable_refresh()
    #    self.root.attributes['data-parent-widget'] = str(id(self))
    #    self.root._parent = self
    #    self.root.enable_refresh()
    #    msg = {"id": self.root.identifier, "repr": self.root.repr()}
    #    self.socket_send("gui_update", json.dumps(msg))

    def execute_javascript(self, code):
        """ run arbitrary code """
        self.socket_send("gui_exec", code)

    def setLocation(self, location):
        self.location = location
        self.execute_javascript("history.pushState(null, '', '%s');" % location)

    def notification_message(self, title, content, icon=""):
        """This function sends "javascript" message to the client, that executes its content.
           In this particular code, a notification message is shown
        """
        code = """
            var options = {
                body: "%(content)s",
                icon: "%(icon)s"
            }
            if (!("Notification" in window)) {
                alert("%(content)s");
            }else if (Notification.permission === "granted") {
                var notification = new Notification("%(title)s", options);
            }else if (Notification.permission !== 'denied') {
                Notification.requestPermission(function (permission) {
                    if (permission === "granted") {
                        var notification = new Notification("%(title)s", options);
                    }
                });
            }
        """ % {'title': title, 'content': content, 'icon': icon}
        self.execute_javascript(code)

    def get_widget_by_id(self, widget_id):

        # cache widgets in a weak reference map by id
        # on cache miss search for the widget starting with the root node
        if widget_id not in self.instance_registry:
            stack = [self.root]
            while stack:
                widget = stack.pop()
                for child in widget.children.values():
                    # TODO: this is a bug waiting to happen
                    # hasattr(child, [children,identifier]) or explicitly
                    # search for gui instances
                    if not isinstance(child, str):
                        stack.append(child)
                        cid = child.identifier
                        self.instance_registry[cid] = child
                        if widget_id == cid:
                            return child
            raise Exception("not found: %s" % widget_id)
        else:
            return self.instance_registry[widget_id]

    def connect_socket(self, socketId):
        with self.update_lock:
            self.websockets.add(socketId)
            self._update_time = None

    def disconnect_socket(self, socketId):
        with self.update_lock:
            self.websockets.remove(socketId)
            if len(self.websockets) == 0:
                self._update_time = time.time()

    def socket_timeout(self):
        with self.update_lock:
            if len(self.websockets) == 0 and self._update_time is not None:
                return time.time() - self._update_time
            return 0

    def socket_send(self, event, payload):
        with self.update_lock:
            if len(self.websockets) == 0:
                logging.warning("no sockets connected to send message")
            for socketId in self.websockets:
                self._socket_send(event, socketId, payload)

    def get_route(self):
        return AppRoute()

    def set_route(self, state):
        pass

    def upload_file(self, filepath, stream):
        raise NotImplementedError("cannot save: %s" % filepath)

class AppService(object):

    def __init__(self, factory, *args, **kwargs):
        super(AppService, self).__init__()

        self.factory = factory

        # a map for session id -> client instance
        self.clients = {}
        # a map for socket session id -> client session id
        self.websocket_session = {}

        self.title = kwargs.get("title", "Application")

        self.update_interval = 0

        # self.kwargs = kwargs

        self.thread = AppSessionManager(self)
        # TODO: background thread is disabled until the arch can be fixed
        # thread should only run if the application is 'run'
        # and not when created.
        #self.thread.start()

        self.client_lock = threading.RLock()

    def newAppInstance(self):

        client = self.factory()
        client._socket_send = self.emit
        return client

    def setSocketHandler(self, method):
        """socket handler is a function for sending events back to the user
        """
        self.socketHandler = method

    def emit(self, event, socketId, message):
        self.socketHandler(event, socketId, message)

    def sessionIdFromHeaders(self, headers):
        sessionId = ""

        # checking previously defined session
        for tok in headers.get('cookie', "").split(";"):
            if 'yue_session=' in tok:
                try:
                    sessionId = tok.replace('yue_session=', '').strip()
                except:
                    pass

        if not sessionId:
            sessionId = uuid.uuid4()

        return sessionId

    def _get_instance(self, sessionId, create=True):

        with self.client_lock:
            if sessionId in self.clients:
                return self.clients[sessionId]

            if not create:
                return None

            client = self.newAppInstance()
            client.identifier = sessionId

            client.update_interval = self.update_interval

            client.js_body_end += js_body_end

            client.title = self.title

            if not hasattr(client, 'websockets'):
                client.websockets = []

            self.clients[sessionId] = client
            self._diag("session %s: session created" % sessionId)

            return client

    def getHtml(self, sessionId, path="/", params=None, headers=None, remote_addr=None):

        client = self._get_instance(sessionId)

        client.remote_addr = remote_addr

        cookies = {}
        for cookie in headers.get("Cookie", "").split(';'):
            if '=' in cookie:
                name, value = cookie.split("=", 1)
                cookies[name.strip()] = value.strip()

        client.set_route(AppRoute(path, params, cookies))

        with client.update_lock:
            # render the HTML
            html = client.root.repr()

        f = io.StringIO()
        f.write("<!DOCTYPE html>\n")
        f.write("<html>\n<head>\n")
        f.write("<link rel=\"shortcut icon\" type=\"image/png\" href=\"/favicon.png\"/>")
        f.write("<link rel=\"shortcut icon\" type=\"image/x-icon\" href=\"/favicon.ico\"/>")
        f.write("<meta content='text/html;charset=utf-8'")
        f.write(" http-equiv='Content-Type'>\n")
        f.write("<meta content='utf-8' http-equiv='encoding'>")
        # disallow pinch to zoom
        f.write("<meta name=\"viewport\"")
        f.write(" content=\"width=device-width, initial-scale=1.0,")
        f.write(" maximum-scale=1.0, user-scalable=no\">\n")
        f.write(client.css_head)
        f.write(client.html_head)
        f.write(client.js_head)
        f.write("\n<title>%s</title>\n" % client.title)
        f.write("\n</head>\n<body>\n")
        f.write(client.js_body_start)
        f.write(client.html_body_start)
        f.write('<div id="loading"><div id="loading-animation">\n</div></div>')
        f.write(html)
        f.write(client.html_body_end)
        f.write(client.js_body_end)
        f.write("</body>\n</html>")

        return f.getvalue()

    def rpc(self, sessionId, widget_id, method_id, params):

        client = self._get_instance(sessionId)

        with client.update_lock:

            try:
                widget = client.get_widget_by_id(widget_id)
                method = get_method_by_name(widget, method_id)
                if method is None:
                    msg = 'attr %s/%s not available' % (widget_id, method_id)
                    raise AppServiceException(400, msg)
                result = method(**params)
                client.do_gui_update()
                return result
                # TODO: send a response...
                # NOTE: for  'callback' (sent via websocket)
                #       any return value is ignored.
                # I may want to change this into a proper feature
                # which can request the return value

            except IOError:
                msg = 'attr %s/%s call error' % (widget_id, method_id)
                raise AppServiceException(404, msg)
            except (TypeError, AttributeError):
                msg = 'attr %s/%s not available' % (widget_id, method_id)
                raise AppServiceException(503, msg)

    def parse_parameters(self, msg):
        """
        Parses the parameters given from POST or websocket reqs
        expecting the parameters as:  "11|par1='asd'|6|par2=1"
        returns a dict like {par1:'asd',par2:1}
        """
        params = {}
        while len(msg) > 1 and msg.count('|') > 0:
            s = msg.split('|')
            l = int(s[0])  # length of param field
            if l > 0:
                msg = msg[len(s[0]) + 1:]
                field_name = msg.split('|')[0].split('=')[0]
                field_value = msg[len(field_name) + 1:l]
                msg = msg[l + 1:]
                params[field_name] = field_value
        return params

    def connect_socket(self, sessionId, socketId):

        client = self._get_instance(sessionId)
        client.connect_socket(socketId)
        self.websocket_session[socketId] = sessionId

        self._diag("session %s: socket connected" % sessionId)

    def disconnect_socket(self, socketId):

        if socketId not in self.websocket_session:
            logging.warning("socket session not found for %s" % socketId)
            return

        sessionId = self.websocket_session[socketId]

        client = self._get_instance(sessionId, create=False)
        if client is None:
            raise Exception("client not found for %s" % sessionId)

        client.disconnect_socket(socketId)
        del self.websocket_session[socketId]

        self._diag("session %s: socket disconnected" % sessionId)

    def set_client_state(self, sessionId, state):
        client = self._get_instance(sessionId)
        client.set_route(state)
        client.do_gui_update()

    def _diag(self, msg):
        logging.info("%s [%d clients, %d sockets]" % (
            msg, len(self.clients), len(self.websocket_session)))

    def healthcheck(self, sessionId):

        clients = {}
        for sid, client in self.clients.items():
            clients[sid] = {
                "remote_addr": client.remote_addr,
                "nsockets": len(client.websockets)
            }

        obj = {
            "global": {
                "nclients": len(self.clients),
                "nsockets": len(self.websocket_session),

            },
            "clients": clients,
            "version": yueserver.__version__,
            "version_branch": yueserver.__branch__,
            "version_git_hash": yueserver.__githash__,
            "version_build_date": yueserver.__date__,
        }

        client = self._get_instance(sessionId, create=False)

        if client:
            obj['session'] = {
                "identifier": sessionId,
                "nsockets": len(client.websockets),
                "remote_addr": client.remote_addr,
            }
        return obj

    def upload_file(self, sessionId, filepath, stream):
        client = self._get_instance(sessionId)
        client.upload_file(filepath, stream)

class GuiAppResource(WebResource):
    """
    The GuiAppResource defines a set of generic endpoints for the web application
    """

    def __init__(self, client_class, title="Application", static_dir="./res"):
        super(GuiAppResource, self).__init__()
        self.service = AppService(client_class, title=title)
        self.service.setSocketHandler(self.emit)

        # test that the client class can build
        client_class().root.repr()

        self.static_dir = static_dir

    def emit(self, event, sid, message):
        self.sio.emit(event, message, room=sid, namespace='/api/ws')

    def _index_path(self, path):

        if 'HTTP_X_REAL_IP' in request.environ:
            # for nginx
            remote_addr = request.environ.get('HTTP_X_REAL_IP')
        elif 'HTTP_X_FORWARDED_FOR' in request.environ:
            # for nginx, and maybe other reverse proxies
            remote_addr = request.environ.get('HTTP_X_FORWARDED_FOR')
        else:
            # for local dev, when not behind a proxy
            remote_addr = request.remote_addr

        logging.info("client ip connected: %s" % remote_addr)

        sessionId = self.service.sessionIdFromHeaders(request.headers)
        html = self.service.getHtml(sessionId, path, request.args,
            request.headers, remote_addr)
        response = make_response(html)
        response.headers["Set-Cookie"] = "yue_session=%s; Path=/" % (sessionId)
        response.headers['Content-Type'] = "text/html"
        response.headers['Cache-Control'] = "no-cache, no-store, must-revalidate"
        response.headers['Pragma'] = "no-cache"
        response.headers['Expires'] = "0"
        logging.info("html Content-Length: %.3f" % (len(html) / 1024.0))
        return response

    @get("/")
    def index_root(self):
        """ return the application bundle when no url path is given
        """
        return self._index_path("")

    @get("/<path:path>")
    def index_path(self, path):
        """ """
        return self._index_path(path)

    @post("/gui/upload")
    def upload_file(self):
        sessionId = self.service.sessionIdFromHeaders(request.headers)
        filepath = request.headers['filepath']
        # this returns None or a flask FileStorage instance
        # a FileStorage object implements read()
        fs = request.files.get("upload")
        self.service.upload_file(sessionId, filepath, fs)
        return "OK", 200

    @get("/favicon.<ext>")
    def favicon(self, ext):
        """ retrieve static files
        """
        if ext not in ("png", "ico"):
            return httpError(403, "Invalid Extension")
        return send_from_directory(self.static_dir, "favicon." + ext)

    @get("/res/<path:path>")
    def static(self, path):
        """ retrieve static files
        """
        # throws werkzeug.exceptions.NotFound
        # if the file does not exist
        return send_from_directory(self.static_dir, path)


    # todo run this example in "threading mode"
    # https://github.com/miguelgrinberg/python-socketio/blob/master/examples/wsgi/app.py

    @websocket("connect", "/api/ws")
    def connect(self, sid, msg):
        headers = {"cookie": msg.get('HTTP_COOKIE', "")}
        sessionId = self.service.sessionIdFromHeaders(headers)
        if sessionId not in self.service.clients:
            logging.warning("socket connected for session %s which no longer exists" % sessionId)
            self.emit("gui_reload", sid, "")
        else:
            self.service.connect_socket(sessionId, sid)

    @websocket("disconnect", "/api/ws")
    def disconnect(self, sid):
        """ """
        self.service.disconnect_socket(sid)

    @websocket("gui_set_location", "/api/ws")
    def gui_set_location(self, sid, msg):

        msg = json.loads(msg)
        cookies = {}
        for cookie in msg.get("cookie", "").split(';'):
            name, value = cookie.split("=", 1)
            cookies[name.strip()] = value.strip()

        info = urlparse(msg.get('location', ""))
        # TODO: 'query', 'params', 'fragment'
        # query    : ?foo=bar
        # params   : ;foo=bar
        # fragment : #foo=bar
        state = AppRoute(info.path, info.query, cookies)

        sessionId = self.service.websocket_session[sid]
        self.service.set_client_state(sessionId, state)

    @websocket("gui_widget_rpc", "/api/ws")
    def gui_widget_rpc(self, sid, msg):

        try:
            obj = json.loads(msg)
            widgetId = obj['id']
            method = obj['method']
            params = obj['params']
        except Exception as e:
            logging.exception("invalid request")
            return

        try:

            sessionId = self.service.websocket_session[sid]

            self.service.rpc(sessionId, widgetId, method, params)
        except Exception as e:
            # TODO: this is a hack
            # interpret an unhandled excpetoin as an invalid gui state
            # force a page reload to fix the problem.
            # try to enumerate why this could occur.
            self.emit("gui_reload", sid, "")
            logging.exception(str(e))

    def _stop(self):
        self.service.thread.kill()