
import os, sys
import logging

from ..framework import gui
from ..framework.backend import GuiAppResource, AppClient
from ..framework.web_resource import WebResource, \
    get, post, put, delete, websocket, param, body, compressed, httpError, \
    int_range, int_min, send_generator, null_validator, boolean

from ..dao.storage import StorageNotFoundException, CryptMode

from .gui.pages import AppPage, Palette
from .gui.exception import AuthenticationError, LibraryException

from .gui.context import YueAppState

import datetime

from flask import jsonify, g, request

from yueserver.resource.util import files_generator, files_generator_v2
from yueserver.dao.library import Song, LibraryException
from yueserver.dao.util import string_quote, server_health

from ..dao.image import ImageScale

def image_scale_type(name):

    if name.lower() in ('null', 'none'):
        return None

    index = ImageScale.fromName(name)
    if index == 0:
        raise Exception("invalid: %s" % name)
    return index

class DemoAppClient(AppClient):
    def __init__(self, guiService, userService, audioService, fileService):
        res_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'res')

        css_head = """<style>

            .flex-grid-thirds {
              display: flex;
              justify-content: space-between;
            }

            .flex-grid-thirds .col-left {
              width: 25%;
              height: 100%;
            }

            .flex-grid-thirds .col-main {
              width: 50%;
            }

            .flex-grid-thirds .col-right {
              width: 25%;
              height: 100%;
            }

            @media screen and (max-width: 1080px) {
                .flex-grid-thirds {
              display: flex;
              justify-content: space-between;
            }

            .flex-grid-thirds .col-left {
              width: 20%;
              height: 100%;
            }

            .flex-grid-thirds .col-main {
              width: 60%;
            }

            .flex-grid-thirds .col-right {
              width: 20%;
              height: 100%;
            }

            }

            @media screen and (max-width: 720px) {
                .flex-grid-thirds {
                    display: block;
                }

                .flex-grid-thirds .col-left {
                    display: none;
                }
                .flex-grid-thirds .col-main {
                    width: 100%;
                }
                .flex-grid-thirds .col-right {
                    display: none;
                }

            }

            .progressbar {
                position: relative;
                width: 100%;
                height: 100%;
                background: ${P_LIGHT};
                border: solid;
                margin-top: 5%;
            }


            .progressbar-buffer {
                z-index: 10;
                position: absolute;
                width: 80%;
                left: 10%;
                top: 25%;
                height: 50%;
                background: ${P_MID_DARK};
            }

            .progressbar-progress {
                z-index: 20;
                position: absolute;
                width: 64%;
                height: 100%;
                background: ${P_MID_LIGHT}E0;
            }

            .progressbar-tick25 {
                z-index: 30;
                position: absolute;
                left: 25%;
                width: 1%;
                height: 100%;
                background: black;
            }

            .progressbar-tick50 {
                z-index: 30;
                position: absolute;
                left: 50%;
                width: 1%;
                height: 100%;
                background: black;
            }

            .progressbar-tick75 {
                z-index: 30;
                position: absolute;
                left: 75%;
                width: 1%;
                height: 100%;
                background: black;
            }

            .progressbar-indicator {
                z-index: 40;
                position: absolute;
                left: 64%;
                width: 2%;
                top: -20%;
                height: 120%;
                background: white;
                border: solid;
            }

            .nav-button {
                background: ${P_MID};
            }

            .nav-button-primary {
                background: ${P_LIGHT};
            }

            /* select order matters here */

            .nav-button:hover {
                background: ${P_MID_LIGHT};
            }

            .nav-button:active {
                background: ${P_MID_DARK};
            }

            .nav-button-icon {

            }

            </style>
        """
        for name, color in Palette.__dict__.items():
            if name == "WHITE" or name == "BLACK" or \
               name.startswith("P_") or \
               name.startswith("S_"):
                css_head = css_head.replace("${%s}" % name, color)

        html_body_start = """

        """

        js_body_end = """
            <script>

            var widget_text = null;
            var widget_audio = null;
            var is_wired = 0;

            function wireAudioPlayer(wid1) {

                if (is_wired==1) {
                    return;
                }
                var audio = document.getElementById("audio_player");
                widget_audio = wid1

                audio.volume = .3;

                audio.ontimeupdate = onPositionChanged
                audio.ondurationchange = onPositionChanged
                audio.onprogress = onPositionChanged


                audio.onabort = function() {
                    console.log("audio player abort");
                    var btn = document.getElementById("playbutton_image");
                    btn.src = '/res/app/media_error.svg';
                    sendCallbackParam(widget_audio, 'onaudiostate', {state: 'abort'});
                }
                audio.onstalled = function() {
                    console.log("audio player stalled");
                    var btn = document.getElementById("playbutton_image");
                    btn.src = '/res/app/media_error.svg';
                    sendCallbackParam(widget_audio, 'onaudiostate', {state: 'stalled'});
                }
                audio.onsuspend = function() {
                    console.log("audio player suspend");
                    sendCallbackParam(widget_audio, 'onaudiostate', {state: 'suspend'});
                }
                audio.onwaiting = function() {
                    console.log("audio player waiting");
                    sendCallbackParam(widget_audio, 'onaudiostate', {state: 'waiting'});
                }
                audio.onerror = function() {
                    console.log("audio player error");
                    console.log(audio.error);
                    var btn = document.getElementById("playbutton_image");
                    btn.src = '/res/app/media_error.svg';
                    sendCallbackParam(widget_audio, 'onaudiostate', {state: 'error'});
                }
                audio.onplay = function() {
                    var btn = document.getElementById("playbutton_image");
                    btn.src = '/res/app/media_pause.svg';
                    sendCallbackParam(widget_audio, 'onaudiostate', {state: 'play'});
                }
                audio.onpause = function() {
                    var btn = document.getElementById("playbutton_image");
                    btn.src = '/res/app/media_play.svg';
                    sendCallbackParam(widget_audio, 'onaudiostate', {state: 'pause'});
                }
                audio.onended = function(event) {
                    sendCallback(widget_audio, 'onended');
                    event.stopPropagation();
                    event.preventDefault();
                }

                var x = document.getElementsByClassName("progressbar");
                x[0].onclick = onSetPosition;

                is_wired = 1;
            }

            function onPositionChanged() {
                var audio = document.getElementById("audio_player");
                var i = audio.buffered.length - 1;
                var s = (i>=0)?audio.buffered.start(i).toFixed(0):0;
                var e = (i>=0)?audio.buffered.end(i).toFixed(0):0;
                var t = audio.currentTime.toFixed(0);
                var d = audio.duration.toFixed(0);

                var x = document.getElementsByClassName("progressbar-buffer");
                x[0].style.left = '' + ((s / d) * 100).toFixed(0) + '%'
                x[0].style.width = '' + (((e - s) / d) * 100).toFixed(0) + "%"

                //var x = document.getElementsByClassName("progressbar-indicator");
                //x[0].style.left = '' + ((t / d) * 100).toFixed(0) + '%'

                var x = document.getElementsByClassName("progressbar-progress");
                x[0].style.width = '' + ((t / d) * 100).toFixed(0) + '%'
            }

            function onSetPosition(event) {
                var audio = document.getElementById("audio_player");
                var x = document.getElementsByClassName("progressbar");
                var rect = x[0].getBoundingClientRect();
                var p = event.clientX - rect.left;
                var w = rect.right - rect.left;
                audio.currentTime = audio.duration * p / w;
            }

            function setPositionEnd() {
                var audio = document.getElementById("audio_player");
                console.log(audio.currentTime, audio.duration);
                audio.currentTime = audio.duration - 5.0;
                console.log(audio.currentTime, audio.duration);
            }

            function elementScrolled(elem, wid) {
                // elem: the scrolling element
                // wid: widget id to send callback to
                if(elem.offsetHeight + elem.scrollTop == elem.scrollHeight)
                {
                    sendCallback(wid, 'onscrollend');
                }
            }

            </script>
        """
        super(DemoAppClient, self).__init__(
            css_head=css_head,
            html_body_start=html_body_start,
            js_body_end=js_body_end,
            static_file_path='./res/')

        self.guiService = guiService

        self.state = YueAppState(userService, audioService, fileService)

        self.state.login.connect(gui.Slot(self.onLogin))
        self.state.logout.connect(gui.Slot(self.onLogout))
        self.state.execute.connect(gui.Slot(self.onExecute))

        self.state.healthcheck = self.healthcheck

        self.root = AppPage(self.state)

    def get_route(self):
        return AppState(*self.root.get_state())

    def set_route(self, state):

        location = state.getUrlParts()
        params = state.getParams()
        cookies = state.getCookies()
        self.root.set_route(location, params, cookies)

    def onLogin(self, token):
        dt = datetime.datetime.utcnow() + datetime.timedelta(days=14)
        expires = dt.strftime("%a, %d %b %Y %H:%M:%S GMT")
        cookie = "yue_token=%s; expires=%s; path=/" % (token, expires)
        self.execute_javascript("document.cookie = '%s';" % cookie)

    def onLogout(self):
        # set the cookie to an expired value to clear it from the browser
        # TODO delete the main page
        cookie = "yue_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/"
        self.execute_javascript("document.cookie = '%s';" % cookie)

        # this is a shortcut for routing to the home page
        self.root.set_route([], {}, {})

    def onExecute(self, text):
        self.execute_javascript(text)

    def upload_file(self, filepath, stream):
        """
        filepath: the contract for gui file uploads is that the filepath
            is "${root}/${path}"
        """
        root, path = filepath.split('/', 1)

        # use system encryption by default

        # TODO: how can I enable server encryption for uploads?
        stream = self.state.fileService.encryptStream(self.state.auth_user,
                None, stream, "r", CryptMode.system)

        # TODO: how to handle duplicates?
        #    + append index
        #    + overwrite (default)
        self.state.fileService.saveFile(self.state.auth_user,
            root, path, stream, encryption=CryptMode.system)

    def healthcheck(self):
        return self.guiService.healthcheck(self.identifier)

class AudioGuiResource(GuiAppResource):
    def __init__(self, cfg, userService, audioService, fileService, transcodeService):
        self.userService = userService
        self.audioService = audioService
        self.fileService = fileService
        self.transcodeService = transcodeService

        self.cfg = cfg
        factory = lambda: DemoAppClient(self.service, userService,
            audioService, fileService)
        super(AudioGuiResource, self).__init__(factory, "Yue", self.cfg.static_dir)

    @get("/api/gui/audio/<song_id>")
    def get_audio(self, song_id):
        sessionId = self.service.sessionIdFromHeaders(request.headers)
        client = self.service._get_instance(sessionId)

        user = client.state.get_user()
        song = self.audioService.findSongById(user, song_id)
        path = self.audioService.getPathFromSong(user, song)

        # note: flasks implementation of send_file does not support seeking
        #       for mp3 files in firefox.

        # TODO: is the transcoe logic required here?

        size = song[Song.file_size] or None
        _, name = self.audioService.fs.split(path)
        go = files_generator(self.audioService.fs, path)
        return send_generator(go, name, file_size=size)

    @get("/api/gui/files/<root>/path/<path:path>")
    @param("dl", type_=boolean, default=True)
    @param("preview", type_=image_scale_type, default=None,
        doc="return a preview picture of the resource")
    def get_file(self, root, path):
        """

        """

        sessionId = self.service.sessionIdFromHeaders(request.headers)
        client = self.service._get_instance(sessionId)
        user = client.state.get_user()

        info = client.state.fileInfo(root, path)

        password = None # TODO: retreive from client per file encryption type

        #---
        if g.args.preview is not None:
            _, name = self.fileService.fs.split(info.file_path)
            url = self.fileService.previewFile(user,
                root, path, g.args.preview, password)
            stream = self.fileService.fs.open(url, "rb")
            if info.encryption in (CryptMode.server, CryptMode.system):
                if not password and info.encryption == CryptMode.server:
                    return httpError(400, "Invalid Password")
                stream = self.fileService.decryptStream(user,
                        password, stream, "r", info.encryption)
            go = files_generator_v2(stream)
            headers = {}
            return send_generator(go, '%s.%s.png' % (name, g.args.preview),
                file_size=None, headers=headers, attachment=g.args.dl)

        else:


            stream = self.fileService.loadFileFromInfo(user, info)
            _, name = self.fileService.fs.split(info.file_path)

            go = files_generator_v2(stream)
            headers = {
                "X-YUE-VERSION": info.version,
                "X-YUE-PERMISSION": info.permission,
                "X-YUE-MTIME": info.mtime,
            }
            return send_generator(go, name, file_size=info.size,
                headers=headers, attachment=g.args.dl)

    @get("/public/<fileid>")
    @param("dl", type_=boolean, default=False)
    def get_public_file(self, fileid):
        """
        this is a stub endpoint for an eventual public file sharing page

        if 'dl' is false:
            use getHtml to return a page and route to
            a public html preview of the content
            or a 404 page if the file does not exist

        if 'dl' is true
            return the file with headers sent to download the file
        """

        return httpError(404, "not implemented")

    @websocket("gui_song_ended", "/api/ws")
    def gui_song_ended(self, sid, msg):
        sessionId = self.service.websocket_session[sid]
        client = self.service._get_instance(sessionId)

    @websocket("gui_refresh_song", "/api/ws")
    def gui_refresh_song(self, sid, msg):
        sessionId = self.service.websocket_session[sid]
        client = self.service._get_instance(sessionId)
        client.state.currentSongChanged.emit()

    @get("/health")
    def health(self):
        """ return status information about the application
        """

        # showing stats on an un-authenticated endpoint seems risky
        # TODO: show db health,
        #health = self.db.health()
        #del health['stats']

        result = {
            "status": "OK",
            "database": {},
            "server": server_health()
        }

        return jsonify(result=result)

    @get("/.well-known/<path:path>")
    def webroot(self, path):
        """ return files from a well known directory

        support for Lets Encrypt certificates
        """
        base = os.path.join(os.getcwd(), ".well-known")
        return send_from_directory(base, path)
