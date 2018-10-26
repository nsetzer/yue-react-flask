
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
from threading import Thread

from urllib.parse import urlparse

from . import gui
from .web_resource import WebResource, \
    websocket, get, post, put, delete, compressed, httpError

from flask import jsonify, g, request, send_from_directory, make_response
from urllib.parse import unquote

from fnmatch import fnmatch

"""
    - allow client to reconnect socket automatically
    - sessions Ids should be valid across server restarts
      - if a user requests a session id and it does not exist create it
    - allow page routing
        client should have set state / get state which returns
            - a path
            - query parameters
    - update events which re-render do not work as expected
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


        var do_repaint = 0;

        function byteLength(str) {
            // returns the byte length of an utf8 string
            var s = str.length;
            for (var i=str.length-1; i>=0; i--) {
                var code = str.charCodeAt(i);
                if (code > 0x7f && code <= 0x7ff) s++;
                else if (code > 0x7ff && code <= 0xffff) s+=2;
                if (code >= 0xDC00 && code <= 0xDFFF) i--; //trail surrogate
            }
            return s;
        }

        function openSocket(){

            try{

                socket = io.connect('http://' + document.domain + ':' + location.port + namespace);

                socket.on('connect', websocketOnOpen);
                socket.on('reconnect', websocketOnReconnect);
                socket.on('disconnect', websocketOnClose);
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

            if (do_repaint == 1) {
                var state = {
                    location: '' + document.location,
                    cookie: document.cookie
                }
                socket.emit('gui_repaint', JSON.stringify(state));
                do_repaint = 0;
            }
        };

        function websocketOnReconnect(attemptNumber) {
            do_repaint = 1;
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

            if (focusedElement == "") {
                console.log("error: focusedElement is empty. no active element")
            }
            var elemToFocus = document.getElementById(focusedElement);
            if( elemToFocus != null ){
                document.getElementById(focusedElement).focus();
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
    SLEEP_INTERVAL = 60

    def __init__(self, service):
        super(AppSessionManager, self).__init__()
        self.alive = True
        self.service = service

    def run(self):

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

            time.sleep(self.SLEEP_INTERVAL)

class AppClient(object):
    """docstring for AppClient"""
    def __init__(self, **kwargs):
        super(AppClient, self).__init__()

        self.update_lock = threading.RLock()

        self.location = "/"

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
        with self.update_lock:

            state = AppRoute(*self.root.get_route())
            location = state.getLocation()
            if location != self.location:
                self.setLocation(location)

            changed_widget_dict = {}
            _s = self.root._force_repaint
            self.root.repr(changed_widget_dict)

            for widget in changed_widget_dict.keys():
                html = changed_widget_dict[widget]
                _id = str(widget.identifier)
                msg = json.dumps({"id": _id, "repr": html})
                self.socket_send("gui_update", msg)
        self._need_update_flag = False

    def set_root_widget(self, widget):
        self.root = widget
        self.root.disable_refresh()
        self.root.attributes['data-parent-widget'] = str(id(self))
        self.root._parent = self
        self.root.enable_refresh()

        msg = {"id": self.root.identifier, "repr": self.root.repr()}
        self.socket_send("gui_update", json.dumps(msg))

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
        self.websockets.add(socketId)
        self._update_time = None
        # TODO: >?
        #print("on connect set location: %s" % self.location)
        #self.execute_javascript("history.pushState(null, '', '%s');" % self.location)

    def disconnect_socket(self, socketId):
        self.websockets.remove(socketId)
        if len(self.websockets) == 0:
            self._update_time = time.time()

    def socket_timeout(self):
        if len(self.websockets) == 0 and self._update_time is not None:
            return time.time() - self._update_time
        return 0

    def socket_send(self, event, payload):
        if len(self.websockets) == 0:
            logging.warning("no sockets connected to send message")
        for socketId in self.websockets:
            self._socket_send(event, socketId, payload)

    def get_route(self):
        return AppRoute()

    def set_route(self, state):
        pass

class AppService(object):
    """docstring for RemiSersessionIdFromHeadersvice"""

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
        self.thread.start()

    #def _get_list_from_app_args(self, name):
    #    try:
    #        v = self.kwargs[name]
    #        if isinstance(v, (tuple, list)):
    #            vals = v
    #        else:
    #            vals = [v]
    #    except KeyError:
    #        vals = []
    #    return vals

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
        for tok in headers.get('cookie',"").split(";"):
            if 'yue_session=' in tok:
                try:
                    sessionId = tok.replace('yue_session=', '').strip()
                except:
                    pass

        if not sessionId:
            sessionId = uuid.uuid4()

        return sessionId

    def _get_instance(self, sessionId):

        # with self.update_lock:
        if sessionId in self.clients:
            return self.clients[sessionId]

        client = self.newAppInstance()

        # The root node requires a fixed ID for repaint to work
        client.root.set_identifier("application_root")

        client.health_check = self.health_check

        client.update_interval = self.update_interval

        # refreshing the script every instance() call, because of different net_interface_ip connections
        # can happens for the same 'k'
        client.js_body_end += js_body_end

        # add built in js, extend with user js
        # client.js_body_end += ('\n' + '\n'.join(self._get_list_from_app_args('js_body_end')))
        # use the default css, but append a version based on its hash, to stop browser caching

        # todo default sytle sheet
        # with open(self._get_static_file('style.css'), 'rb') as f:
        #    md5 = hashlib.md5(f.read()).hexdigest()
        #    client.css_head = "<link href='/res/style.css?%s' rel='stylesheet' />\n" % md5

        # add built in css, extend with user css
        #client.css_head += ('\n' + '\n'.join(self._get_list_from_app_args('css_head')))

        # add user supplied extra html,css,js
        #client.html_head = '\n'.join(self._get_list_from_app_args('html_head'))
        #client.html_body_start = '\n'.join(self._get_list_from_app_args('html_body_start'))
        #client.html_body_end = '\n'.join(self._get_list_from_app_args('html_body_end'))
        #client.js_body_start = '\n'.join(self._get_list_from_app_args('js_body_start'))
        #client.js_head = '\n'.join(self._get_list_from_app_args('js_head'))

        client.title = self.title

        if not hasattr(client, 'websockets'):
            client.websockets = []

        if not hasattr(client, '_need_update_flag'):
            client._need_update_flag = False
            client._stop_update_flag = False
            if client.update_interval > 0:
                client._update_thread = threading.Thread(target=self._idle_loop)
                client._update_thread.setDaemon(True)
                client._update_thread.start()

        self.clients[sessionId] = client
        self._diag("session %s: session created" % sessionId)

        return client

    def getHtml(self, sessionId, path="/", params=None, headers=None):

        client = self._get_instance(sessionId)

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
        f.write("<meta content='text/html;charset=utf-8'")
        f.write(" http-equiv='Content-Type'>\n")
        f.write("<meta content='utf-8' http-equiv='encoding'>")
        f.write("<meta name=\"viewport\"")
        f.write(" content=\"width=device-width, initial-scale=1.0\">\n")
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
            raise Exception("socket session not found for %s" % socketId)

        sessionId = self.websocket_session[socketId]
        if sessionId not in self.clients:
            raise Exception("client not found for %s" % sessionId)

        self.clients[sessionId].disconnect_socket(socketId)
        del self.websocket_session[socketId]

        self._diag("session %s: socket disconnected" % sessionId)

    def repaint(self, socketId, state):

        if socketId not in self.websocket_session:
            raise Exception("socket session not found for %s" % socketId)

        sessionId = self.websocket_session[socketId]
        if sessionId not in self.clients:
            raise Exception("client not found for %s" % sessionId)

        self.clients[sessionId].root._force_repaint = True
        self.clients[sessionId].set_route(state)
        self.clients[sessionId].do_gui_update()

    def set_client_state(self, sessionId, state):
        client = self._get_instance(sessionId)
        client.set_route(state)
        client.do_gui_update()

    def _diag(self, msg):
        logging.info("%s [%d clients, %d sockets]" % (
            msg, len(self.clients), len(self.websocket_session)))

    def health_check(self, sessionId):

        client = self.clients.get(sessionId, None)
        obj = {
            "global": {
                "nclients": len(self.clients),
                "nsockets": len(self.websocket_session)
            },
        }

        if client:
            obj['session'] = {
                "nsockets": len(client.websockets)
            }
        return obj

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
        sessionId = self.service.sessionIdFromHeaders(request.headers)
        html = self.service.getHtml(sessionId, path, request.args, request.headers)
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
        return self._index_path(path)

    @get("/res/<path:path>")
    def static(self, path):
        """ retrieve static files
        """
        return send_from_directory(self.static_dir, path)

    # todo run this example in "threading mode"
    # https://github.com/miguelgrinberg/python-socketio/blob/master/examples/wsgi/app.py

    @websocket("connect", "/api/ws")
    def connect(self, sid, msg):
        headers = {"cookie": msg.get('HTTP_COOKIE', "")}
        sessionId = self.service.sessionIdFromHeaders(headers)
        self.service.connect_socket(sessionId, sid)

    @websocket("disconnect", "/api/ws")
    def disconnect(self, sid):
        self.service.disconnect_socket(sid)

    @websocket("gui_repaint", "/api/ws")
    def gui_repaint(self, sid, msg):

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

        # TODO: this can maybe be done a better way
        self.service.repaint(sid, state)

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

        obj = json.loads(msg)
        widgetId = obj['id']
        method = obj['method']
        params = obj['params']

        sessionId = self.service.websocket_session[sid]

        self.service.rpc(sessionId, widgetId, method, params)
