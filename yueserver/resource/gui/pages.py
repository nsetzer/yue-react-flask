
import os, sys
import logging

"""
settings:
    button to delete  current playlist
    test page layout when no playlist exists
"""
from ...framework import gui
from ...framework.backend import InvalidRoute

from ...dao.util import string_quote

from .exception import AuthenticationError, LibraryException

NAV_HEIGHT = "6em"
NAVBAR_HEIGHT = "2em"

class Palette(object):

    P_LIGHT     = "#1455A3"  # "#0D5199"
    P_MID_LIGHT = "#124E92"  # "#104479"
    P_MID       = "#0D3981"  # "#0C3662"
    P_MID_DARK  = "#052460"  # "#052445"
    P_DARK      = "#031539"  # "#031528"

    S_LIGHT     = "#aaaaaa"
    S_MID_LIGHT = "#888888"
    S_MID       = "#666666"
    S_MID_DARK  = "#444444"
    S_DARK      = "#222222"

    WHITE = "#FFFFFF"
    BLACK = "#000000"

class SongWidget(gui.Widget):
    def __init__(self, song, index=None, *args, **kwargs):
        super(SongWidget, self).__init__(*args, **kwargs)
        self.type = 'li'

        self.song = song
        self.index = index

        self.height = "32px"
        self.hbox = gui.Widget(height="100%", width="100%", parent=self)
        self.hbox.style.update({
            'display':'flex',
            'justify-content':'space-around',
            'align-items':'center',
            'flex-direction':'row',
            'border-style': "solid",
            'border-radius': "3px"
        })

        self.img_icon = gui.Image('/res/app/disc.svg', parent=self.hbox)
        self.img_icon.style.update({
            "height": "32px",
            "width": "32px",
            "margin-left": "3%",
            "margin-right": "3%",
        })
        del self.img_icon.style['margin']

        self.vbox_text = gui.VBox(height="100%", width="100%", parent=self.hbox)
        self.vbox_text.style.update({"align-self": "flex-start"})

        self.lbl_title = gui.Label(song['title'], height="45%", width="100%", parent=self.vbox_text)
        self.lbl_title.style.update({
            "margin-bottom": "2px",
            "margin-top": "2px",
            "bottom": '0',
            "left": '0'
        })
        del self.lbl_title.style['margin']

        self.lbl_artist = gui.Label(song['artist'], height="45%", width="100%", parent=self.vbox_text)
        self.lbl_artist.style.update({
            "margin-top": "2px",
            "margin-bottom": "2px",
            "top": '0',
            "left": '0'
        })
        del self.lbl_artist.style['margin']

        self.btn_menu = gui.Button("...", parent=self.hbox)
        self.btn_menu.onclick.connect(self.onMenuButtonClickedOpened)
        self.btn_menu.style.update({
            "height": "32px",
            "width": "32px",
            "margin-left": "3%",
            "margin-left": "3%",
            "margin-right": "3%",
        })
        del self.btn_menu.style['margin']


        self.openMenu = gui.Signal(object, object)
        self.delete = gui.Signal(object)
        self.playNext = gui.Signal(object)

    def menu_dialog_clicked(self, widget):
        self.lbl_artist.set_text("clicked")

    def onPlayNextSelected(self, widget):
        self.playNext.emit(self)

    def onDeleteSelected(self, widget):
        self.delete.emit(self)

    def onMenuButtonClickedOpened(self, widget):
        self.openMenu.emit(self.index, self.song)

    def getSong(self):
        return self.song

class TitleTextWidget(gui.Widget):
    def __init__(self, icon_url, text, *args, **kwargs):
        super(TitleTextWidget, self).__init__()

        # calc(100% - 20px)
        self.hbox = gui.Widget(height="100%", width="100%", parent=self)
        self.hbox.style.update({
            'display': 'flex',
            'justify-content': 'space-around',
            'align-items': 'center',
            'flex-direction': 'row',
            'border-style': "solid",
            'border-radius': "3px"
        })

        self.img_icon = gui.Image(icon_url)
        self.img_icon.style.update({
            "height": "32px",
            "width": "32px",
            "margin-left": "3%",
            "margin-right": "3%",
        })
        del self.img_icon.style['margin']

        self.lbl_path = gui.Label(text, width="100%", height="100%")

        self.open = gui.Signal()

        self.hbox.append(self.img_icon, "img_icon")
        self.hbox.append(self.lbl_path, "lbl_title")

        btn = gui.Button("open")
        btn.onclick.connect(self._onOpenClicked)
        self.hbox.append(btn, "btn_open")
        btn.style.update({
            "width": "40px",
            "margin-left": "3%",
            "margin-right": "3%",
        })
        del btn.style['margin']

    def _onOpenClicked(self, widget):

        self.open.emit()

class IconBarWidget(gui.Widget):
    def __init__(self, *args, **kwargs):
        super(IconBarWidget, self).__init__()

        self.hbox = gui.Widget(height="100%", width="100%", parent=self)

        self.actions = []

    def addAction(self, icon_url, callback):

        btn = gui.Button()
        btn.onclick.connect(lambda w: callback())
        img = gui.Image(icon_url, parent=btn)
        img.style.update({"width": "100%", "height": "100%"})
        self.addWidget(btn)

    def addWidget(self, widget):

        widget.style.update({
            "width": "2.5em",
            "height": "2.5em",
            "margin-left": ".5em",
            "margin-right": ".5em",
            "margin-top": ".5em",
            "margin-bottom": ".5em",
        })
        del widget.style['margin']

        self.hbox.append(widget)
        self.actions.append(widget)

class FileInfoWidget(gui.Widget):
    """docstring for FileInfoWidget"""
    def __init__(self, file_info, *args, **kwargs):
        super(FileInfoWidget, self).__init__()

        self.file_info = file_info

        self.hbox = gui.Widget(height="100%", width="calc(100% - 20px)", parent=self)
        self.hbox.style.update({
            'display': 'flex',
            'justify-content': 'space-around',
            'align-items': 'center',
            'flex-direction': 'row',
            'border-style': "solid",
            'border-radius': "3px"
        })

        if file_info['isDir']:
            if file_info['name'] == '..':
                url = '/res/app/return.svg'
            else:
                url = '/res/app/folder.svg'
        else:
            url = '/res/app/file.svg'
        self.img_icon = gui.Image(url)
        self.img_icon.style.update({
            "height": "32px",
            "width": "32px",
            "margin-left": "3%",
            "margin-left": "3%",
            "margin-right": "3%",
        })
        del self.img_icon.style['margin']

        self.lbl_path = gui.Label(file_info['name'], width="100%", height="100%")

        self.openDirectory = gui.Signal(object)
        self.openPreview = gui.Signal(object)

        self.hbox.append(self.img_icon, "img_icon")
        self.hbox.append(self.lbl_path, "lbl_title")

        if self.file_info['isDir']:
            btn = gui.Button("open", parent=self.hbox)
            btn.onclick.connect(self._onOpenClicked)
            btn.style.update({
                "width": "40px",
                "margin-left": "3%",
                "margin-right": "3%",
            })
            del btn.style['margin']

        else:
            btn = gui.Button("pre", parent=self.hbox)
            btn.onclick.connect(self._onOpenPreviewClicked)
            btn.style.update({
                "width": "40px",
                "margin-left": "3%",
                "margin-right": "3%",
            })
            del btn.style['margin']

    def _onOpenClicked(self, widget):
        if self.file_info['isDir']:
            self.openDirectory.emit(self.file_info)

    def _onOpenPreviewClicked(self, widget):
        if not self.file_info['isDir']:
            self.openPreview.emit(self.file_info)

class AppViewWrapper(gui.Widget):
    """docstring for AppView"""
    def __init__(self, view, *args, **kwargs):
        super(AppViewWrapper, self).__init__(*args, **kwargs)

        self.style.update({
            "position": "absolute",
            "left": "0",
            "top": "0",
            "width": "100%",
            "overflow-y": "scroll",
        })

        self.append(view)

class AppView(gui.Widget):
    """docstring for AppView"""
    def __init__(self, child, *args, **kwargs):
        super(AppView, self).__init__(*args, **kwargs)

        self.style.update({
            "width": "100%",
            "flex": "1 1 auto",
        })

        self.append(child)

class ScrollBox(gui.Widget):
    """http://jsfiddle.net/sA5fD/8/"""
    def __init__(self, child, *args, **kwargs):
        super(ScrollBox, self).__init__(*args, **kwargs)

        self.content = gui.Widget()
        self.content_scroll = gui.Widget()

        self.style.update({
            "width": "100%",
            "height": "100%",
        })
        self.content.style.update({
            "position": "relative",
            "height": "100%"
        })
        self.content_scroll.style.update({
            "position": "absolute",
            "top": "0",
            "right": "0",
            "bottom": "0",
            "left": "0",
            "overflow-y": "auto",
            "overflow-x": "hidden",
        })

        self.content_scroll.attributes.update({"onscroll": "elementScrolled(this)"})

        if child is not None:
            self.content_scroll.append(child)
        self.content.append(self.content_scroll)
        super(ScrollBox, self).append(self.content)

    def append(self, widget):
        self.content_scroll.append(widget)

class ProgressBar(gui.Widget):
    """docstring for ProgressBar"""
    def __init__(self, *args, **kwargs):
        super(ProgressBar, self).__init__(*args, **kwargs)

        self.style.update({"width": "60%", "height": "16px"})

        bar = gui.Widget(_class='progressbar', parent=self)
        gui.Widget(_class='progressbar-buffer', parent=bar)
        gui.Widget(_class='progressbar-progress', parent=bar)
        gui.Widget(_class='progressbar-tick25', parent=bar)
        gui.Widget(_class='progressbar-tick50', parent=bar)
        gui.Widget(_class='progressbar-tick75', parent=bar)
        # gui.Widget(_class='progressbar-indicator', parent=bar)

class NavBar2(gui.Widget):
    """docstring for NavBar"""
    def __init__(self, *args, **kwargs):
        super(NavBar2, self).__init__(*args, **kwargs)

        self.hbox_nav = gui.HBox()
        self.hbox_nav.style.update({
            "width": "100%",
            "height": NAVBAR_HEIGHT,
            "border-bottom": "3px solid",
            "background": Palette.S_MID_LIGHT
        })

        self.container = gui.Widget(height=("calc(100%% - %s)" % NAVBAR_HEIGHT), width="100%")
        #self.container.style.update({"margin-bottom": NAVBAR_HEIGHT})
        self.append(self.hbox_nav)
        self.append(self.container)
        self.scrollbox = ScrollBox(None)
        self.container.append(self.scrollbox)

        self.nav_children = []
        self.nav_buttons = []

        self.indexChanged = gui.Signal(int)

    def addTabIcon(self, name, url, widget):

        self.nav_children.append((name, widget))

        button = gui.Widget(width="100%", height="32px", parent=self.hbox_nav)
        button.attributes.update({"class": "nav-button"})
        button.style.update({
            "border-style": "solid",
            "border-width": "3px",
            "border-radius": "15px 15px 0px 0px",
        })
        self.nav_buttons.append(button)

        icon = gui.Image(url, parent=button)
        icon.attributes.update({"class": "nav-button-icon"})
        icon.style.update({"height": "32px", "width": "32px", "margin": "auto", "display": "block"})
        button.onclick.connect(lambda x: self.onNavClicked(widget))
        self.scrollbox.append(widget)
        widget.style.update({"display": "block"})
        widget._style_display = "block"

        # by default hide all extra tabs
        if len(self.nav_children) > 1:
            widget.set_visible(False)
        else:
            widget.set_visible(True)

    def items(self):
        return self.nav_children

    def current(self):
        for i, (name, child) in enumerate(self.nav_children):
            if child.is_visible():
                return (name, child)
        raise Exception("no child is visible")

    def onNavClicked(self, widget):

        if widget.is_visible():
            return

        index = None
        for i, (name, child) in enumerate(self.nav_children):
            child.set_visible(False)
            self.nav_buttons[i].attributes.update({"class": "nav-button"})

            if widget is child:
                index = i

        widget.set_visible(True)
        self.nav_buttons[index].attributes.update({"class": "nav-button-primary"})

        self.indexChanged.emit(index)

    def setIndex(self, index):
        for i, (name, child) in enumerate(self.nav_children):
            child.set_visible(False)
            self.nav_buttons[i].attributes.update({"class": "nav-button"})
        self.nav_children[index][1].set_visible(True)
        self.nav_buttons[index].attributes.update({"class": "nav-button-primary"})

    def index(self):
        for i, (name, child) in enumerate(self.nav_children):
            if child.is_visible():
                return i
        return None

class AudioDisplay(gui.Widget):

    def __init__(self, context, *args, **kwargs):
        super(AudioDisplay, self).__init__(_id="audio_display",
            *args, **kwargs)

        self.context = context  # application context

        self.current_state = "unkown"  # state of the audio playback

        self.style.update({
            "position": "absolute",
            "top": "0",
            "height": NAV_HEIGHT,
            "overflow": "hidden"})
        # ---------------------------------------------------------------------

        # <audio id="audio_player"></audio>
        self.audio_player = gui.Widget(_type="audio",
            _id="audio_player", parent=self)
        del self.audio_player.style['margin']

        self.hbox_main = gui.Widget(parent=self)
        self.hbox_main.attributes.update({"class": "flex-grid-thirds"})
        self.hbox_main.style.update({"height": "100%", "width": "100%"})
        self.hbox_main.style.update({"background": Palette.S_MID_LIGHT})

        border_left = gui.Widget(parent=self.hbox_main)
        border_left.attributes.update({"class": "col-left", "z-index": "-2"})
        border_left.style.update({"background": Palette.S_DARK})

        vbox = gui.VBox(parent=self.hbox_main)
        vbox.attributes.update({"class": "col-main", "z-index": "-2"})
        vbox.style.update({"background": Palette.S_MID_LIGHT})

        border_left = gui.Widget(parent=self.hbox_main)
        border_left.attributes.update({"class": "col-left", "z-index": "-2"})
        border_left.style.update({"background": Palette.S_DARK})

        # ---------------------------------------------------------------------

        self.hbox_player = gui.HBox(parent=vbox)
        self.hbox_player.style.update({
            "display": "flex",
            "margin": "0px",
            "overflow": "visible",
            "position": "static",
            "width": "100%",
            "justify-content":
            "space-around",
            "height": "48px",
            "order": "-1",
            "align-items": "center",
            "top": "20px",
            "flex-direction": "row",
            "background": "transparent"
        })

        self.btnPlayPause = gui.Button(
            _id="playbutton",
            image='/res/app/media_play.svg',
            parent=self.hbox_player)
        self.btnPlayPause.onclick.connect(self.onPlayPauseClicked)
        self.btnPlayPause.style.update({
            "order": "-1",
            "width": "3em",
            "height": "3em",
            "border-radius": "1.5em"
        })

        self.btnNextSong = gui.Button(image='/res/app/media_next.svg',
            parent=self.hbox_player)
        self.btnNextSong.onclick.connect(self.onNextSongClicked)
        self.btnNextSong.style.update({
            "order": "-1",
            "width": "32px",
            "height": "32px"
        })

        self.btnAudioStatus = gui.Button(image='/res/app/media_next.svg',
            parent=self.hbox_player)
        self.btnAudioStatus.onclick.connect(self.onAudioStatusClicked)
        self.btnAudioStatus.style.update({"order":"-1",
            "background-image": "url('/res/flag.png')",
            "width": "32px",
            "height": "32px"
        })

        self.progressbar = ProgressBar(parent=self.hbox_player)

        # ---------------------------------------------------------------------

        self.lbl_title = gui.Label('TITLE', parent=vbox)
        self.lbl_title.style.update({
            "width": "100%",
            "text-align": "center",
            "background": "transparent"
        })

        # ---------------------------------------------------------------------

        self._onPlaylistChanged = gui.Slot(self.onPlaylistChanged)
        self.context.playlistChanged.connect(self._onPlaylistChanged)
        self._onCurrentSongChanged = gui.Slot(self.onCurrentSongChanged)
        self.context.currentSongChanged.connect(self._onCurrentSongChanged)

        # this Event Connector allows for the audio player to directly
        # call the onended handler from javascript
        self.onended = gui.ClassEventConnector(self, 'onended',
            lambda *args, **kwargs: tuple())
        self.onended.connect(self.onAudioEnded)

        self.onaudiostate = gui.ClassEventConnector(self, 'onaudiostate',
            lambda *args, **kwargs: tuple([kwargs.get('state', None)]))
        self.onaudiostate.connect(self.onAudioState)

        self.updateCurrentSong()

    def onAudioStatusClicked(self, widget):
        text = """
            setPositionEnd()
        """
        self.context.execute.emit(text)

    def onPlayPauseClicked(self, widget):

        text = """
            wireAudioPlayer('audio_display');
            var audio = document.getElementById("audio_player");
            if (audio.paused) {
                if (audio.src) {
                    audio.play();
                } else {
                    socket.emit('gui_refresh_song', {})
                }
                audio.autoplay = true;
            } else {
                audio.autoplay = false;
                audio.pause();
            }
        """
        self.context.execute.emit(text)

    def onNextSongClicked(self, widget):

        self.context.nextSong()
        self.updateCurrentSong()

    def updateCurrentSong(self):

        try:
            song = self.context.getCurrentSong()
            path = "/api/gui/audio/%s" % song['id']
            self.lbl_title.set_text(song['title'] + " - " + song['artist'])

            text = """

                wireAudioPlayer('audio_display');

                var audio = document.getElementById("audio_player");

                if (audio != null) {
                    audio.src = '%s';
                    audio.load();
                } else {
                    console.error("unable to find audio element");
                }

            """ % (path)
            self.context.execute.emit(text)
        except LibraryException as e:
            self.lbl_title.set_text("No Playlist Created")

    def onPlaylistChanged(self):
        # TODO: if playing, and the current song has not changed do nothing
        self.updateCurrentSong()

    def onCurrentSongChanged(self):
        self.updateCurrentSong()

    def onAudioEnded(self, widget):

        self.context.nextSong()
        self.updateCurrentSong()

    def onAudioState(self, widget, state):
        self.current_state = state

class PopMenu(gui.Widget):
    """docstring for PopMenu"""
    def __init__(self, *args, **kwargs):
        super(PopMenu, self).__init__(*args, **kwargs)

        self.style.update({
            "display": "none",
            "position": "fixed",
            "width": "30%",
            "top": "50%",
            "left": "50%",
            "transform": "translate(-50%, -50%)",
            "background": "blue",
            "z-index": "500",
            "border": "solid"
        })

        # experiment with focs menu, failed?
        #self.attributes['tabindex'] = "0"
        #self.attributes['onclick'] = self.focus_js()

        self.onblur.connect(self.onBlur)
        self.onkeyup.connect(self.onKeyUp)

        self.opened = gui.Signal()

        self.vbox = gui.VBox(parent=self)
        self.vbox.style['background'] = "transparent"

        self.btn0 = gui.Button("exit", width="2em", height="2em", parent=self.vbox)
        self.btn0.onclick.connect(lambda w: self.reject())
        #del self.btn0.style['margin']
        self.btn0.style['margin'] = "1em"
        self.btn0.style['align-self'] = 'flex-end'

        self.buttons = []
        self.callbacks = []

    def addAction(self, text, callback):

        btn = gui.Button(text, width="100%", parent=self.vbox)
        index = len(self.buttons)
        btn.onclick.connect(lambda w: self.accept(index))
        del btn.style['margin']
        btn.style['margin-bottom'] = ".5em"

        self.buttons.append(btn)
        self.callbacks.append(callback)

    def onKeyUp(self, widget, key, ctrl, shift, alt):
        if key == "Escape":
            self.reject()

    def onBlur(self, widget):

        self.reject()

    def reject(self):
        self.style['display'] = 'none'

    def accept(self, index):
        self.style['display'] = 'none'
        self.callbacks[index]()

    def focus_js(self):
        return "document.getElementById('%s').focus();" % self.identifier

    def show(self):
        self.style['display'] = 'block'

class PopPreview(gui.Widget):
    """docstring for PopPreview"""
    def __init__(self, *args, **kwargs):
        super(PopPreview, self).__init__(*args, **kwargs)

        self.style.update({
            "display": "none",
            "position": "fixed",
            "width": "50%",
            "top": "50%",
            "left": "50%",
            "height": "80%",
            "transform": "translate(-50%, -50%)",
            "background": "blue",
            "z-index": "500",
            "border": "solid"
        })

        self.vbox = gui.VBox(parent=self)
        self.vbox.style['height'] = "80%"

        self.btn0 = gui.Button("exit", width="2em", height="2em", parent=self.vbox)
        self.btn0.onclick.connect(lambda w: self.reject())
        #del self.btn0.style['margin']
        self.btn0.style['margin'] = "1em"
        self.btn0.style['align-self'] = 'flex-end'

        self.scrollbox = ScrollBox(None, parent=self.vbox)
        self.wpre = gui.Widget(_type="pre", parent=self.scrollbox)
        self.code = gui.Widget(_type="code", parent=self.wpre)

    def setTextContent(self, text, content_ext):
        self.code.add_child("content", text)

    def reject(self):
        self.style['display'] = 'none'

    def accept(self, index):
        self.style['display'] = 'none'

    def show(self):
        self.style['display'] = 'block'

# ---------------------

class NowPlayingPage(gui.Page):
    """docstring for NowPlayingPage"""
    def __init__(self, context, *args, **kwargs):
        super(NowPlayingPage, self).__init__(*args, **kwargs)

        self.context = context
        self._onOpenMenu = gui.Slot(self.onOpenMenu)
        self.lst = gui.WidgetList()

        self.menu = PopMenu(parent=self)
        self.menu.addAction("Play Next", self.onMenuPlayNext)
        self.menu.addAction("Remove", self.onMenuRemove)
        self.menu_active_row = None

        self.onPlaylistChanged()

        self.append(self.lst)

        self.context.currentSongChanged.connect(gui.Slot(self.onPlaylistChanged))
        self.context.playlistChanged.connect(gui.Slot(self.onPlaylistChanged))

    def onOpenMenu(self, index, song):
        self.menu.show()
        self.menu_active_row = (index, song)

    def onMenuPlayNext(self):
        index, _ = self.menu_active_row
        self.context.playlistPlayNext(index)
        self.menu_active_row = None

    def onMenuRemove(self):
        index, _ = self.menu_active_row
        self.context.playlistDeleteSong(index)
        self.menu_active_row = None

    def onPlaylistChanged(self):

        self.lst.empty()

        try:
            playlist = self.context.getPlaylist()
        except LibraryException as e:
            playlist = []

        for index, song in enumerate(playlist):
            item = SongWidget(song, index=index)
            item.openMenu.connect(self._onOpenMenu)
            self.lst.append(item)

class LibraryPage(gui.Page):
    """docstring for NowPlayingPage"""
    def __init__(self, context, *args, **kwargs):
        super(LibraryPage, self).__init__(*args, **kwargs)

        self.context = context
        self.domain_info = self.context.getDomainInfo()
        self.page_state = 0
        self.page_artist_index = -1
        self.page_albums = []
        self.page_albums_index = -1
        self.page_genre_index = -1
        self.page_query = ""

        self.menu_song = PopMenu(parent=self)
        self.menu_song.addAction("Play Next", self.onSongMenuPlayNext)
        self.menu_song_active_row = None

        # 0: [artist, genres]
        # 1: [artists]
        # 2: [albums]
        # 3: [genres]
        # 4: [songs]

        self.lst = gui.WidgetList(parent=self)

        self._onOpenSongMenu = gui.Slot(self.onOpenSongMenu)

        self.showPage(0)

    def showPage(self, index):

        self.page_state = index

        self.lst.empty()
        if index == 0:
            # top level menu

            item = TitleTextWidget('/res/app/microphone.svg', "Artists")
            item.open.connect(gui.Slot(lambda: self.onOpenElement(1)))
            self.lst.append(item)

            item = TitleTextWidget('/res/app/disc.svg', "Genres")
            item.open.connect(gui.Slot(lambda: self.onOpenElement(3)))
            self.lst.append(item)

            item = TitleTextWidget('/res/app/music_note.svg', "Random Play All")
            item.open.connect(gui.Slot(lambda: self.onRandomPlay("")))
            self.lst.append(item)

        elif index == 1:  # show artists
            item = TitleTextWidget('/res/app/return.svg', "..")
            item.open.connect(gui.Slot(lambda: self.onOpenElement(0)))
            self.lst.append(item)

            for i, artist in enumerate(self.domain_info['artists']):
                item = TitleTextWidget('/res/app/microphone.svg', artist['name'])
                slot = gui.Slot(lambda i=i: self.onOpenAlbums(i))
                item.open.connect(slot)
                self.lst.append(item)

        elif index == 2:  # show artist albums

            item = TitleTextWidget('/res/app/return.svg', "..")
            item.open.connect(gui.Slot(lambda: self.onOpenElement(1)))
            self.lst.append(item)

            artist = self.domain_info['artists'][self.page_artist_index]['name']
            query = "artist==%s" % string_quote(artist)
            item = TitleTextWidget('/res/app/return.svg', "Random Play All")
            item.open.connect(gui.Slot(lambda: self.onRandomPlay(query)))
            self.lst.append(item)

            albums = self.domain_info['artists'][self.page_artist_index]['albums']
            self.page_albums = list(sorted(albums.items()))
            for i, (album, count) in enumerate(self.page_albums):
                item = TitleTextWidget('/res/app/album.svg', album)
                slot = gui.Slot(lambda i=i: self.onOpenAlbumSongs(i))
                item.open.connect(slot)
                self.lst.append(item)

        elif index == 3:  # Genres
            item = TitleTextWidget('/res/app/return.svg', "..")
            item.open.connect(gui.Slot(lambda: self.onOpenElement(0)))
            self.lst.append(item)

            for i, genre in enumerate(self.domain_info['genres']):
                item = TitleTextWidget('/res/app/genre.svg', genre['name'])
                item.open.connect(gui.Slot(lambda i=i: self.onOpenGenre(i)))
                self.lst.append(item)

        elif index == 4:  # Songs
            item = TitleTextWidget('/res/app/return.svg', "..")
            item.open.connect(gui.Slot(lambda: self.onOpenElement(2)))
            self.lst.append(item)

            item = TitleTextWidget('/res/app/return.svg', "Random Play All")
            item.open.connect(gui.Slot(lambda: self.onRandomPlay(self.page_query)))
            self.lst.append(item)

            for song in self.context.search(self.page_query):
                item = SongWidget(song, index=index)
                item.openMenu.connect(self._onOpenSongMenu)
                self.lst.append(item)

        elif index == 5:
            item = TitleTextWidget('/res/file.png', "..")
            item.open.connect(gui.Slot(lambda: self.onOpenElement(3)))
            self.lst.append(item)

            item = TitleTextWidget('/res/file.png', "Random Play All")
            item.open.connect(gui.Slot(lambda: self.onRandomPlay(self.page_query)))
            self.lst.append(item)

            for song in self.context.search(self.page_query):
                item = SongWidget(song, index=index)
                item.openMenu.connect(self._onOpenSongMenu)
                self.lst.append(item)

    def onRandomPlay(self, query):
        self.context.createPlaylist(query)

    def onOpenElement(self, index):
        self.showPage(index)

    def onOpenAlbums(self, index):
        self.page_artist_index = index
        self.showPage(2)

    def onOpenAlbumSongs(self, index):
        self.page_albums_index = index
        art = string_quote(self.domain_info['artists'][self.page_artist_index]['name'])
        alb = string_quote(self.page_albums[self.page_albums_index][0])
        self.page_query = "artist==%s && album==%s" % (art, alb)
        self.showPage(4)

    def onOpenGenre(self, index):
        self.page_genre_index = index
        genre = self.domain_info['genres'][index]['name']
        # TODO: this requires domain knowledge of genre format...
        self.page_query = "genre=%s" % string_quote(";" + genre + ";").lower()
        self.showPage(5)

    def onOpenSongMenu(self, index, song):
        self.menu_song.show()
        self.menu_song_active_row = (index, song)

    def onSongMenuPlayNext(self):
        _, song = self.menu_song_active_row
        self.context.playlistInsertSong(1, song)

    def onOpenQuery(self, text):
        pass

    def get_route(self):

        return [], {}, {}

    def set_route(self, location, params, cookies):

        pass

class SearchLibraryPage(gui.Page):
    """docstring for SearchLibrary"""
    def __init__(self, context, *args, **kwargs):
        super(SearchLibraryPage, self).__init__(*args, **kwargs)
        self.context = context

    def get_route(self):

        return [], {}, {}

    def set_route(self, location, params, cookies):

        pass

    def onOpen(self):
        super(SearchLibraryPage, self).onOpen()
        # TODO: get health check for admins

class FileSystemPage(gui.Page):
    """docstring for FileSystemPage"""

    def __init__(self, context, *args, **kwargs):
        super(FileSystemPage, self).__init__(*args, **kwargs)

        self.location = gui.Signal(str, str)

        self.root = ""
        self.path = ""
        self.context = context

        # directories don't actually exist.
        # support a user 'creating' a directory by storing
        #   (root, path) => name
        self.session_directories = {}

        self.lst = gui.WidgetList()
        self.append(self.lst)

        self._onOpenDirectory = gui.Slot(self.onOpenDirectory)
        self._onOpenPreview = gui.Slot(self.onOpenPreview)
        self._onOpenParent = gui.Slot(self.onOpenParent)
        self._onOpenRoot = gui.Slot(self.onOpenRoot)

        self.menu = PopPreview(parent=self)

        self.listdir()  # TODO: this is a bug, on show: listdir

    def get_route(self):

        if self.root:
            path = ["path", self.root]
            if self.path:
                path.extend(self.path.split("/"))
        else:
            path = []

        return path, {}, {}

    def set_route(self, location, params, cookies):

        if len(location) == 0:
            self.root = ""
            self.path = ""
        if len(location) >= 2:
            self.root = location[1]
            self.path = "/".join(location[2:])

        try:
            self.listdir()
        except Exception as e:
            raise InvalidRoute(str(e))

    def setLocation(self, root, path):
        self.root = root
        self.path = path
        self.listdir()

    def listdir(self):
        self.lst.empty()

        if self.root == "":

            for name in self.context.listroots():
                file_info = {'name': name, 'isDir': True, "size": 0}
                item = FileInfoWidget(file_info)
                item.openDirectory.connect(self._onOpenRoot)
                self.lst.append(item)
        else:

            wdt = IconBarWidget()
            wdt.addAction("/res/app/return.svg", self.onOpenParent)

            if self.path:
                urlbase = "%s/%s/" % (self.root, self.path)
            else:
                urlbase = "%s/" % (self.root)

            btn = gui.UploadFileButton(urlbase, image="/res/app/file.svg")
            btn.style.update({"width": "2em", "height": "2em"})
            btn.onsuccess.connect(self.onFileUploadSuccess)
            btn.onfailure.connect(self.onFileUploadFailure)
            wdt.addWidget(btn)
            self.lst.append(wdt)

            session_dirs = self.session_directories.get(
                (self.root, self.path), set())

            items = self.context.listdir(self.root, self.path)

            for file_info in items:

                if file_info['name'] in session_dirs:
                    session_dirs.remove(file_info['name'])

                item = FileInfoWidget(file_info)
                item.openDirectory.connect(self._onOpenDirectory)
                item.openPreview.connect(self._onOpenPreview)
                self.lst.append(item)

            for name in session_dirs:
                file_info = {'name': name, 'isDir': True}
                item = FileInfoWidget(file_info)
                item.openDirectory.connect(self._onOpenDirectory)
                item.openPreview.connect(self._onOpenPreview)
                self.lst.insert(1, item)

            # if the list is now empty (a file exists creating)
            # the directory, remove the entry entirely
            if not session_dirs and \
               (self.root, self.path) in self.session_directories:
                del self.session_directories[(self.root, self.path)]

    def onOpenDirectory(self, file_info):
        self.path = os.path.join(self.path, file_info['name'])
        self.listdir()
        self.location.emit(self.root, self.path)

    def onOpenPreview(self, file_info):
        path = os.path.join(self.path, file_info['name'])
        self.menu.setTextContent(
            self.context.renderContent(self.root, path), ".txt")
        self.menu.show()

    def onOpenParent(self):

        if self.path:
            self.path = os.path.split(self.path)[0]
        else:
            self.root = ""

        self.listdir()
        self.location.emit(self.root, self.path)

    def onOpenRoot(self, file_info):
        self.root = file_info['name']
        self.path = ""
        self.listdir()
        self.location.emit(self.root, self.path)

    def onFileUploadSuccess(self, widget, filepath):
        print("success", filepath)

    def onFileUploadFailure(self, widget, filepath):

        print("failed", filepath)

class SettingsPage(gui.Page):
    def __init__(self, context, *args, **kwargs):
        super(SettingsPage, self).__init__(*args, **kwargs)

        self.context = context

        self.vbox = gui.VBox(height="100%", width="100%", parent=self)
        self.btn_logout = gui.Button("logout", parent=self.vbox)
        self.btn_logout.onclick.connect(self.onLogout)

    def onLogout(self, widget):
        self.context.clear_authentication()

class HomePage(gui.Page):
    """
    Signals:
        login()
    """
    def __init__(self, *args, **kwargs):
        super(HomePage, self).__init__(*args, **kwargs)

        self.vbox = gui.VBox(height="100%", width="100%", parent=self)
        self.vbox.style.update({
            "background": Palette.S_DARK,
        })

        self.panel = gui.Widget(parent=self.vbox)
        self.panel.style.update({
            "width": "100%",
            "background": Palette.S_MID_LIGHT,
            "padding-top": "3em",
            "padding-bottom": "3em",
        })
        del self.panel.style['margin']

        self.label_title = gui.Label("Welcome", parent=self.panel)
        self.label_title.style.update({
            "text-align": "center",
            "font-size": "1.5em"
        })
        del self.label_title.style['margin']

        self.btn_submit = gui.Button("login", parent=self.panel)
        self.btn_submit.style.update({
            "margin-top": "20px",
            "margin-left": "33%",
            "margin-right": "33%",
            "width": "34%"
        })
        del self.btn_submit.style['margin']

        self.btn_submit.onclick.connect(self.onSubmitClicked)
        self.login = gui.Signal()

    def set_route(self, location, params, cookies):
        pass

    def get_route(self):
        return [], {}, {}

    def onSubmitClicked(self, widget):

        self.login.emit()

class NotFoundPage(gui.Page):
    """
    Signals:
        submit()
    """
    def __init__(self, *args, **kwargs):
        super(NotFoundPage, self).__init__(*args, **kwargs)

        self.submit = gui.Signal()

        self.vbox = gui.VBox(height="100%", width="100%", parent=self)
        self.vbox.style.update({
            "background": Palette.S_DARK,
        })

        self.panel = gui.Widget(parent=self.vbox)
        self.panel.style.update({
            "width": "100%",
            "background": Palette.S_MID_LIGHT,
            "padding-top": "3em",
            "padding-bottom": "3em",
        })
        del self.panel.style['margin']

        self.label_title = gui.Label("404", parent=self.panel)
        self.label_title.style.update({
            "text-align": "center",
            "font-size": "1.5em"
        })
        del self.label_title.style['margin']

        self.btn_submit = gui.Button("return", parent=self.panel)
        self.btn_submit.style.update({
            "margin-top": "20px",
            "margin-left": "33%",
            "margin-right": "33%",
            "width": "34%"
        })
        del self.btn_submit.style['margin']

        self.btn_submit.onclick.connect(self.onSubmitClicked)

        self.route = ([], {}, {})

    def set_route(self, location, params, cookies):
        """
        persist the route that got us to a page that was not found
        """
        self.route = (location, params, cookies)

    def get_route(self):
        return route

    def onSubmitClicked(self, widget):

        self.submit.emit()

class LoginPage(gui.Page):
    """
    Signals:
        login (username, password)
        cancel()

    """

    MSG_LOGIN_ERROR = "Invalid username or password"

    JS_FOCUS = "document.getElementById('%s').focus();"

    def __init__(self, *args, **kwargs):
        super(LoginPage, self).__init__(*args, **kwargs)

        # ---------------------------------------------------------------------
        # define signals emitted by this page

        self.login = gui.Signal(str, str)
        self.cancel = gui.Signal()

        # ---------------------------------------------------------------------
        # Create the widgets that make up the form
        # so that we can resolve reference loops

        self.vbox = gui.VBox(height="100%", width="100%", parent=self)
        self.panel = gui.Widget(parent=self.vbox)
        self.focusguard1 = gui.Widget(parent=self.panel, _class="focusguard")
        self.label_email = gui.Label("Email:", parent=self.panel)
        self.input_email = gui.Input("email", parent=self.panel)
        self.label_password = gui.Label("Password:", parent=self.panel)
        self.input_password = gui.Input("password", parent=self.panel)
        self.label_error = gui.Label(self.MSG_LOGIN_ERROR, parent=self.panel)
        self.hbox_submit = gui.Widget(parent=self.panel)
        self.btn_cancel = gui.Button("cancel", parent=self.hbox_submit)
        self.btn_submit = gui.Button("login", parent=self.hbox_submit)
        self.focusguard2 = gui.Widget(parent=self.panel, _class="focusguard")

        # ---------------------------------------------------------------------
        # set attributes for all of the widgets

        self.vbox.style.update({
            "background": Palette.S_DARK,
        })

        self.panel.style.update({
            "width": "100%",
            "background": Palette.S_MID_LIGHT,
            "padding-top": "3em",
            "padding-bottom": "3em",
        })
        del self.panel.style['margin']

        # A focus guard which focuses on the LAST element in the
        # focus group when it receives keyboard focus
        self.focusguard1.attributes['tabindex'] = "1"
        js = self.JS_FOCUS % self.btn_submit.identifier
        self.focusguard1.attributes['onfocus'] = js
        self.focusguard1.style.update({"width": "0", "height": "0"})

        self.label_email.style.update({
            "width": "80%",
            "margin-left": "10%",
            "margin-right": "10%",
            "margin-bottom": "0",
            "margin-top": "1em",
        })
        del self.label_email.style['margin']

        self.input_email.attributes['tabindex'] = "2"
        self.input_email.style.update({
            "width": "80%",
            "margin-left":
            "10%",
            "margin-right": "10%"
        })
        del self.input_email.style['margin']

        self.label_password.style.update({
            "width": "80%",
            "margin-left": "10%",
            "margin-right": "10%",
            "margin-bottom": "0",
            "margin-top": "1em",
        })
        del self.label_password.style['margin']

        self.input_password.attributes['tabindex'] = "3"
        self.input_password.style.update({
            "width": "80%",
            "margin-left": "10%",
            "margin-right": "10%"
        })
        del self.input_password.style['margin']

        self.label_error.style.update({"display": 'none'})
        self.label_error.style.update({
            "width": "80%",
            "margin-left": "10%",
            "margin-right": "10%"
        })
        del self.label_error.style['margin']

        self.hbox_submit.style.update({
            "width": "80%",
            "margin-left": "10%",
            "margin-right": "10%",
            "background":
            "transparent"
        })
        self.hbox_submit.style.update({
            "display": "flex",
            "justify-content":
            "flex-end"
        })
        del self.hbox_submit.style['margin']

        self.btn_cancel.attributes['tabindex'] = "4"
        self.btn_cancel.style.update({
            "margin-right": "10%",
            "margin-top": "20px",
            "width": "25%"
        })
        del self.btn_cancel.style['margin']

        self.btn_submit.attributes['tabindex'] = "5"
        self.btn_submit.style.update({
            "margin-top": "20px",
            "width": "25%"
        })
        del self.btn_submit.style['margin']

        # A focus guard which focuses on the FIRST element in the
        # focus group when it receives keyboard focus
        self.focusguard2.attributes['tabindex'] = "6"
        js = self.JS_FOCUS % self.input_email.identifier
        self.focusguard2.attributes['onfocus'] = js
        self.focusguard2.style.update({"width": "0", "height": "0"})

        # ---------------------------------------------------------------------
        # connect signals / slots

        self.input_email.onkeyup.connect(self.onKeyUp)
        self.input_password.onkeyup.connect(self.onKeyUp)
        self.btn_submit.onclick.connect(self.onSubmitClicked)
        self.btn_cancel.onclick.connect(self.onCancelClicked)

    def set_route(self, location, params, cookies):

        self.label_error.style.update({"display": 'none'})

    def get_route(self):
        return [], {}, {}

    def onKeyUp(self, widget, key, ctrl, shift, alt):

        if key == "Enter":
            self.login.emit(self.input_email.get_value(),
                self.input_password.get_value())

    def onCancelClicked(self, widget):
        self.cancel.emit()

    def onSubmitClicked(self, widget):

        self.login.emit(self.input_email.get_value(),
            self.input_password.get_value())

    def set_error(self, error):
        if error:
            self.label_error.style.update({"display": 'block'})
        else:
            self.label_error.style.update({"display": 'none'})

class MainPage(gui.Page):

    def __init__(self, context, *args, **kwargs):
        super(MainPage, self).__init__(*args, **kwargs)

        self.context = context

        self.vbox = gui.VBox(height="100%", width="100%", parent=self)

        self.display = AudioDisplay(self.context, width="100%", parent=self.vbox)

        self.navbar = NavBar2(height="100%", width="100%", parent=self.vbox)
        self.navbar.style.update({"margin-top": NAV_HEIGHT, "z-index": "5"})
        del self.navbar.style['margin']

        self.tabNowPlaying = NowPlayingPage(self.context,
            height="100%", width="100%")

        self.tabLibrary = LibraryPage(self.context,
            height="100%", width="100%")

        self.tabSearchLibrary = SearchLibraryPage(self.context,
            height="100%", width="100%")

        # TODO: conditionally create this tab
        # print("creating tab", self.context.auth_info)
        # 'filesystem_read' in auth_info['roles'][0]['features']
        self.tabFileSystem = FileSystemPage(self.context,
            height="100%", width="100%")

        self.tabSettings = SettingsPage(self.context,
            height="100%", width="100%")

        self.navbar.addTabIcon("queue", "/res/app/playlist.svg", self.tabNowPlaying)
        self.navbar.addTabIcon("library", "/res/app/album.svg", self.tabLibrary)
        self.navbar.addTabIcon("search", "/res/app/search.svg", self.tabSearchLibrary)
        self.navbar.addTabIcon("files", "/res/app/documents.svg", self.tabFileSystem)
        self.navbar.addTabIcon("settings", "/res/app/settings.svg", self.tabSettings)

    def set_route(self, location, params, cookies):
        if len(location) == 0:
            self.navbar.setIndex(0)
            self.tabNowPlaying.set_route([], params, cookies)
        else:
            for i, (name, page) in enumerate(self.navbar.items()):
                if name == location[0]:
                    self.navbar.setIndex(i)
                    page.set_route(location[1:], params, cookies)
                    return

            raise InvalidRoute(location)

    def get_route(self):

        name, page = self.navbar.current()

        path = [name]
        params = {}
        cookies = {}

        _path, _params, _cookies = page.get_route()
        path += _path
        params.update(_params)
        cookies.update(_cookies)

        return path, params, cookies

class AppPage(gui.Page):

    def __init__(self, context, *args, **kwargs):
        super(AppPage, self).__init__(*args, **kwargs)

        self.style.update({"height": "100%", "width": "100%"})

        self.context = context

        # custom css, flex box grid layouts
        # https://www.w3schools.com/css/css_attribute_selectors.asp
        # attribute selectors

        self.hbox_main = gui.Widget(parent=self)
        self.hbox_main.attributes.update({"class": "flex-grid-thirds"})
        self.hbox_main.style.update({"height": "100%", "width": "100%"})

        border_left = gui.Widget(parent=self.hbox_main)
        border_left.attributes.update({"class": "col-left", "z-index": "-2"})
        border_left.style.update({"background": Palette.S_DARK})

        self.page_main = None
        self.page_notfound = None
        self.page_login = None

        self.page_home = HomePage()
        self.page_home.attributes.update({"class": "col-main"})
        self.page_home.style.update({"height": "100%", "display": "flex"})
        self._openLoginPage = gui.Slot(self.openLoginPage)
        self.page_home.login.connect(self._openLoginPage)
        self.hbox_main.insert(1, self.page_home)

        border_right = gui.Widget(parent=self.hbox_main)
        border_right.attributes.update({"class": "col-right"})
        border_right.style.update({"background": Palette.S_DARK})

        self.pages = [self.page_home]

    def set_route(self, location, params, cookies):

        if self.page_main is not None and not self.context.is_authenticated():
            # on any route change, if the user is no longer logged in
            # remove the main page, if it exists
            # the user has logged out and it may contain user secrets
            self.hbox_main.remove_child(self.page_main)
            self.page_main = None

        try:
            for page in self.pages:
                page.set_visible(False)

            # location: empty,    -> fn
            # location: N or more -> fn
            # location: exactly N -> fn
            # location: is auth   -> fn

            # add_auth_route(path, fn_true, fn_false)
            # add_exact_route(path, fn)
            # add_route(path, fn)

            # path -> "/"
            # path -> ['m']
            # path -> ['login']

            self.context.set_authentication(cookies.get("yue_token", None))

            if len(location) == 0:
                self.page_home.set_visible(True)
                self.page_home.set_route([], params, cookies)
            elif location[0] == 'm':
                if self.context.is_authenticated():
                    page = self.getMainPage()
                else:
                    logging.warning("not auth")
                    page = self.getLoginPage()
                page.set_visible(True)
                page.set_route(location[1:], params, cookies)
            elif location[0] == "login" and len(location) == 1:
                page = self.getLoginPage()
                page.set_visible(True)
                page.set_route(location[1:], params, cookies)
            else:
                page = self.getNotFoundPage()
                page.set_visible(True)
                page.set_route(location, params, cookies)

        except InvalidRoute as e:
            for page in self.pages:
                page.set_visible(False)
            page = self.getNotFoundPage()
            page.set_visible(True)
            page.set_route([], {}, {})

        return

    def get_route(self):

        path = []
        params = {}
        cookies = {}

        if self.page_home.is_visible():
            pass

        elif self.page_notfound and self.page_notfound.is_visible():
            _path, _params, _cookies = self.page_notfound.get_route()
            path += _path
            params.update(_params)
            cookies.update(_cookies)

        elif self.page_main is not None and self.page_main.is_visible():
            path.append("m")
            _path, _params, _cookies = self.page_main.get_route()
            path += _path
            params.update(_params)
            cookies.update(_cookies)

        elif self.page_login is not None and self.page_login.is_visible():
            path.append("login")
            _path, _params, _cookies = self.page_login.get_route()
            path += _path
            params.update(_params)
            cookies.update(_cookies)

        return path, params, cookies

    def getNotFoundPage(self):

        if self.page_notfound is None:
            self.page_notfound = NotFoundPage()
            self.page_notfound.attributes.update({"class": "col-main"})
            self.page_notfound.style.update({"height": "100%", "display": "flex"})
            self._onNotFoundSubmit = gui.Slot(self.onNotFoundSubmit)
            self.page_notfound.submit.connect(self._onNotFoundSubmit)
            self.hbox_main.insert(1, self.page_notfound)
            self.pages.append(self.page_notfound)

        return self.page_notfound

    def getLoginPage(self):

        if self.page_login is None:
            self.page_login = LoginPage()
            self.page_login.attributes.update({"class": "col-main"})
            self.page_login.style.update({"height": "100%", "display": "flex"})
            self._onLogin = gui.Slot(self.onLogin)
            self.page_login.login.connect(self._onLogin)
            self._onCancelLogin = gui.Slot(self.onCancelLogin)
            self.page_login.cancel.connect(self._onCancelLogin)
            self.hbox_main.insert(1, self.page_login)
            self.pages.append(self.page_login)

        return self.page_login

    def getMainPage(self):

        if self.page_main is None:
            self.page_main = MainPage(self.context)
            self.page_main.attributes.update({"class": "col-main"})
            self.page_main.style.update({"height": "100%", "display": "flex"})
            self.hbox_main.insert(1, self.page_main)
            self.pages.append(self.page_main)
        return self.page_main

    def onLogin(self, username, password):

        try:
            self.context.authenticate(username, password)

            self.getLoginPage().set_error(False)
            for page in self.pages:
                page.set_visible(False)
            self.getMainPage().set_visible(True)

            # remove the login page to prevent continuous
            # pop ups in firefox prompting to store the password
            self.hbox_main.remove_child(self.page_login)
            self.page_login = None

        except Exception as e:
            logging.exception(e)
            self.getLoginPage().set_error(True)

    def onNotFoundSubmit(self):

        for page in self.pages:
            page.set_visible(False)

        if self.context.is_authenticated():
            self.getMainPage().set_visible(True)
        else:
            self.page_home.set_visible(True)

    def onCancelLogin(self):

        for page in self.pages:
            page.set_visible(False)
        self.page_home.set_visible(True)

    def openLoginPage(self):
        for page in self.pages:
            page.set_visible(False)
        self.getLoginPage().set_visible(True)
