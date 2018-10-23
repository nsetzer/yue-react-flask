
import os, sys
import logging

from ..framework import gui
from ..framework.backend import AppResource, AppClient
from ..framework.web_resource import WebResource, \
    get, post, put, delete, websocket, param, body, compressed, httpError, \
    int_range, int_min, send_generator, null_validator

from .gui.pages import AppPage
from .gui.exception import AuthenticationError, LibraryException

from .gui.context import YueAppState

import datetime


class DemoAppClient(AppClient):
    def __init__(self, userService, audioService, fileService):
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
                background: rgb(200,200,200);
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
                background: orange;
            }

            .progressbar-progress {
                z-index: 20;
                position: absolute;
                width: 64%;
                height: 100%;
                background: rgba(255,0,0,.7);
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

            /*

             base:

             silver -> black
             #c0c0c0 #aeaeae #9d9d9d #8b8b8b #7a7a7a #686868
             #575757 #454545 #343434 #222222 #111111 #000000

             silver -> white
             #c0c0c0 #c5c5c5 #cbcbcb #d1d1d1 #d6d6d6 #dcdcdc
             #e2e2e2 #e8e8e8 #ededed #f3f3f3 #f9f9f9 #ffffff

             primary:

             blue -> black
             #4682b4 #3f76a3 #396a93 #325e82 #2c5272 #264662
             #1f3b51 #192f41 #132331 #0c1720 #060b10 #000000

             blue -> white
             #4682b4 #568dba #6798c1 #78a4c8 #89afcf #9abad6
             #aac6dc #bbd1e3 #ccdcea #dde8f1 #eef3f8 #ffffff

             secondary:

             violet -> black
             #9400d3 #8600bf #7900ac #6b0099 #5e0086 #500073
             #43005f #35004c #280039 #1a0026 #0d0013 #000000

             violet -> white
             #9400d3 #9d17d7 #a72edb #b145df #ba5ce3 #c473e7
             #ce8beb #d8a2ef #e1b9f3 #ebd0f7 #f5e7fb #ffffff

            */

            .nav-button {
                background-image: linear-gradient(#78a4c8, #dde8f1 10%, #78a4c8);
            }

            .nav-button-primary {
                background-image: linear-gradient(#78a4c8, #9400d3 10%, #78a4c8);
            }

            /* select order matters here */

            .nav-button:hover {
                background-image: linear-gradient(#78a4c8, #c473e7 10%, #78a4c8);
            }

            .nav-button:active {
                background-image: linear-gradient(#78a4c8, #500073 10%, #78a4c8);
            }

            .nav-button-icon {

            }

            </style>
        """

        html_body_start = """
            <audio id="audio_player"></audio>
        """

        js_body_end = """
        <script>
        var audio = document.getElementById("audio_player");
        var widget_text = null;
        var widget_audio = null;

        function wireAudioPlayer(wid1) {
            widget_audio = wid1

            audio.volume = .3;

            audio.ontimeupdate = onPositionChanged
            audio.ondurationchange = onPositionChanged
            audio.onprogress = onPositionChanged


            audio.onabort = function() {
                console.log("audio player abort");
                sendCallbackParam(widget_audio, 'onaudiostate', {state: 'abort'});
            }
            audio.onstalled = function() {
                console.log("audio player stalled");
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
                console.log("audio player error"); console.log(audio.error);
                sendCallbackParam(widget_audio, 'onaudiostate', {state: 'error'});
            }
            audio.onplay = function() {
                sendCallbackParam(widget_audio, 'onaudiostate', {state: 'play'});
            }
            audio.onpause = function() {
                sendCallbackParam(widget_audio, 'onaudiostate', {state: 'pause'});
            }
            audio.onended = function(event) {
                sendCallback(widget_audio, 'onended');
                event.stopPropagation();
                event.preventDefault();
            }

            var x = document.getElementsByClassName("progressbar");
            x[0].onclick = onSetPosition;
        }

        function onPositionChanged() {
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
            var x = document.getElementsByClassName("progressbar");
            var rect = x[0].getBoundingClientRect();
            var p = event.clientX - rect.left;
            var w = rect.right - rect.left;
            audio.currentTime = audio.duration * p / w;
        }

        function setPositionEnd() {
            console.log(audio.currentTime, audio.duration);
            audio.currentTime = audio.duration - 5.0;
            console.log(audio.currentTime, audio.duration);
        }

        function elementScrolled(elem) {
            if(elem.offsetHeight + elem.scrollTop == elem.scrollHeight)
            {
                console.log("End of Scroll Region");
            }
        }

        </script>
        """
        super(DemoAppClient, self).__init__(
            css_head=css_head,
            html_body_start=html_body_start,
            js_body_end=js_body_end,
            static_file_path='./res/')

        self.state = YueAppState(userService, audioService, fileService)

        self.state.login.connect(gui.Slot(self.onLogin))
        self.state.logout.connect(gui.Slot(self.onLogout))
        self.state.execute.connect(gui.Slot(self.onExecute))

        self.root = AppPage(self.state)

    def get_state(self):
        return AppState(*self.root.get_state())

    def set_state(self, state):

        location = state.getUrlParts()
        params = state.getParams()
        cookies = state.getCookies()
        self.root.set_state(location, params, cookies)

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
        self.root.set_state([], {}, {})

    def onExecute(self, text):
        self.execute_javascript(text)

class GraphicsResource(AppResource):
    def __init__(self, cfg, userService, audioService, fileService, transcodeService):
        self.userService = userService
        self.audioService = audioService
        self.fileService = fileService
        self.transcodeService = transcodeService

        self.cfg = cfg
        factory = lambda: DemoAppClient(userService,
            audioService, fileService)
        super(GraphicsResource, self).__init__(factory, "Yue", self.cfg.static_dir)

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

    @websocket("gui_song_ended", "/api/ws")
    def gui_song_ended(self, sid, msg):
        sessionId = self.service.websocket_session[sid]
        client = self.service._get_instance(sessionId)

        print("gui song ended", msg)

    @get("/health")
    def health(self):
        """ return status information about the application
        """

        # showing stats on an un-authenticated endpoint seems risky
        health = self.db.health()
        del health['stats']

        result = {
            "status": "OK",
            "database": health,
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