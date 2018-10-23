
import os, sys
import logging

from ...framework import gui
from ...framework.backend import InvalidRoute

from ...dao.util import string_quote

from .exception import AuthenticationError, LibraryException

NAV_HEIGHT = "5em"
NAVBAR_HEIGHT = "2em"

class SongWidget(gui.Widget):
    """docstring for SongWidget"""
    def __init__(self, song, index=None, *args, **kwargs):
        super(SongWidget, self).__init__(*args, **kwargs)
        self.type = 'li'

        self.song = song
        self.index = index

        self.height = "32px"
        self.hbox = gui.Widget(height="100%", width="calc(100% - 20px)", parent=self)
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
    """docstring for FileInfoWidget"""
    def __init__(self, icon_url, text, *args, **kwargs):
        super(TitleTextWidget, self).__init__()

        self.hbox = gui.Widget(height="100%", width="calc(100% - 20px)", parent=self)
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
            "background": "#8f8"
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

    def addTabIcon(self, url, widget):

        self.nav_children.append(widget)

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
            widget.style.update({"display": "none"})

    def onNavClicked(self, widget):

        if widget.is_visible():
            return

        index = None
        for i, child in enumerate(self.nav_children):
            child.set_visible(False)
            self.nav_buttons[i].attributes.update({"class": "nav-button"})

            if widget is child:
                index = i

        widget.set_visible(True)
        self.nav_buttons[index].attributes.update({"class": "nav-button-primary"})

        self.indexChanged.emit(index)

    def setIndex(self, index):
        for i, child in enumerate(self.nav_children):
            child.set_visible(False)
            self.nav_buttons[i].attributes.update({"class": "nav-button"})
        self.nav_children[index].set_visible(True)
        self.nav_buttons[index].attributes.update({"class": "nav-button-primary"})

    def index(self):
        for i, child in enumerate(self.nav_children):
            if child.is_visible():
                return i
        return None

class AudioDisplay(gui.Widget):

    def __init__(self, state, *args, **kwargs):
        super(AudioDisplay, self).__init__(*args, **kwargs)

        self.wire_audio = True
        self.state = state  # application context

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

        border_left = gui.Widget(parent=self.hbox_main)
        border_left.attributes.update({"class": "col-left", "z-index": "-2"})
        border_left.style.update({"background": "#222222"})

        vbox = gui.VBox(parent=self.hbox_main)
        vbox.attributes.update({"class": "col-main", "z-index": "-2"})

        border_left = gui.Widget(parent=self.hbox_main)
        border_left.attributes.update({"class": "col-left", "z-index": "-2"})
        border_left.style.update({"background": "#222222"})

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
            "flex-direction": "row"
        })

        self.btnPlayPause = gui.Button('', parent=self.hbox_player)
        self.btnPlayPause.onclick.connect(self.onPlayPauseClicked)
        self.btnPlayPause.style.update({
            "order": "-1",
            "width": "32px",
            "height": "32px",
            "border-radius": "16px"
        })
        gui.Image('/res/app/media_play.svg', parent=self.btnPlayPause)

        self.btnNextSong = gui.Button('', parent=self.hbox_player)
        self.btnNextSong.onclick.connect(self.onNextSongClicked)
        self.btnNextSong.style.update({
            "order": "-1",
            "width": "32px",
            "height": "32px"
        })
        gui.Image('/res/app/media_next.svg', parent=self.btnPlayPause)

        self.btnAudioStatus = gui.Button('', parent=self.hbox_player)
        self.btnAudioStatus.onclick.connect(self.onAudioStatusClicked)
        self.btnAudioStatus.style.update({"order":"-1",
            "background-image": "url('/res/flag.png')",
            "width": "32px",
            "height": "32px"
        })

        self.progressbar = ProgressBar(parent=self.hbox_player)

        # self.audio_player = gui.AudioPlayer('', parent=self.hbox_player)

        # ---------------------------------------------------------------------

        self.lbl_title = gui.Label('TITLE', parent=vbox)
        self.lbl_title.style.update({"width": "100%"})


        # ---------------------------------------------------------------------

        #self.audio_player.onplay.connect(lambda *args: sys.stdout.write("on play\n"))
        #self.audio_player.onpause.connect(lambda *args: sys.stdout.write("on pause\n"))
        #self.audio_player.onended.connect(self.onNextSongClicked)

        self._onPlaylistChanged = gui.Slot(self.onPlaylistChanged)
        self.state.playlistChanged.connect(self._onPlaylistChanged)
        self._onCurrentSongChanged = gui.Slot(self.onCurrentSongChanged)
        self.state.currentSongChanged.connect(self._onCurrentSongChanged)

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
        self.state.execute.emit(text)

    def onPlayPauseClicked(self, widget):

        text = """
            var audio = document.getElementById("audio_player");
            if (audio.paused) {
                audio.autoplay = true;
                audio.play();

            } else {
                audio.autoplay = false;
                audio.pause();
            }
        """
        self.state.execute.emit(text)

    def onNextSongClicked(self, widget):

        self.state.nextSong()
        self.updateCurrentSong()

    def updateCurrentSong(self):

        try:
            song = self.state.getCurrentSong()
            path = "/api/gui/audio/%s" % song['id']
            self.lbl_title.set_text(song['title'] + " - " + song['artist'])

            text = """

                wireAudioPlayer('%s');

                var audio = document.getElementById("audio_player");

                audio.src = '%s';
                audio.load();

            """ % (self.identifier, path)
            self.state.execute.emit(text)
        except LibraryException as e:
            self.lbl_title.set_text("No Playlist Created")

    def onPlaylistChanged(self):
        # TODO: if playing, and the current song has not changed do nothing
        self.updateCurrentSong()

    def onCurrentSongChanged(self):
        self.updateCurrentSong()

    def onAudioEnded(self, widget):

        self.state.nextSong()
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
    def __init__(self, state, *args, **kwargs):
        super(NowPlayingPage, self).__init__(*args, **kwargs)

        self.state = state
        self._onOpenMenu = gui.Slot(self.onOpenMenu)
        self.lst = gui.WidgetList()

        self.menu = PopMenu(parent=self)
        self.menu.addAction("Play Next", self.onMenuPlayNext)
        self.menu.addAction("Remove", self.onMenuRemove)
        self.menu_active_row = None

        self.onPlaylistChanged()

        self.append(self.lst)

        self.state.currentSongChanged.connect(gui.Slot(self.onPlaylistChanged))
        self.state.playlistChanged.connect(gui.Slot(self.onPlaylistChanged))

    def onOpenMenu(self, index, song):
        self.menu.show()
        self.menu_active_row = (index, song)

    def onMenuPlayNext(self):
        index, _ = self.menu_active_row
        self.state.playlistPlayNext(index)
        self.menu_active_row = None

    def onMenuRemove(self):
        index, _ = self.menu_active_row
        self.state.playlistDeleteSong(index)
        self.menu_active_row = None

    def onPlaylistChanged(self):

        self.lst.empty()

        try:
            playlist = self.state.getPlaylist()
        except LibraryException as e:
            playlist = []

        for index, song in enumerate(playlist):
            item = SongWidget(song, index=index)
            item.openMenu.connect(self._onOpenMenu)
            self.lst.append(item)

class LibraryPage(gui.Page):
    """docstring for NowPlayingPage"""
    def __init__(self, state, *args, **kwargs):
        super(LibraryPage, self).__init__(*args, **kwargs)

        self.state = state
        self.domain_info = self.state.getDomainInfo()
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

            for song in self.state.search(self.page_query):
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

            for song in self.state.search(self.page_query):
                item = SongWidget(song, index=index)
                item.openMenu.connect(self._onOpenSongMenu)
                self.lst.append(item)

    def onRandomPlay(self, query):
        print("random play: %s" % query)
        self.state.createPlaylist(query)

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
        self.state.playlistInsertSong(1, song)

    def onOpenQuery(self, text):
        pass

    def get_state(self):

        return [], {}, {}

    def set_state(self, location, params, cookies):

        pass

class SearchLibraryPage(gui.Page):
    """docstring for SearchLibrary"""
    def __init__(self, state, *args, **kwargs):
        super(SearchLibraryPage, self).__init__(*args, **kwargs)
        self.state = state

    def get_state(self):

        return [], {}, {}

    def set_state(self, location, params, cookies):

        pass

    def onOpen(self):
        super(SearchLibraryPage, self).onOpen()
        # TODO: get health check for admins

class FileSystemPage(gui.Page):
    """docstring for FileSystemPage"""

    def __init__(self, state, *args, **kwargs):
        super(FileSystemPage, self).__init__(*args, **kwargs)

        self.location = gui.Signal(str, str)

        self.root = ""
        self.path = ""
        self.state = state

        self.lst = gui.WidgetList()
        self.append(self.lst)

        self._onOpenDirectory = gui.Slot(self.onOpenDirectory)
        self._onOpenPreview = gui.Slot(self.onOpenPreview)
        self._onOpenParent = gui.Slot(self.onOpenParent)
        self._onOpenRoot = gui.Slot(self.onOpenRoot)

        self.menu = PopPreview(parent=self)

        self.listdir()  # TODO: this is a bug, on show: listdir

    def get_state(self):

        if self.root:
            path = ["path", self.root]
            if self.path:
                path.extend(self.path.split("/"))
        else:
            path = []

        return path, {}, {}

    def set_state(self, location, params, cookies):

        if len(location) == 0:
            self.root = ""
            self.path = ""
        if len(location) >= 2:
            self.root = location[1]
            self.path = "/".join(location[2:])

        self.listdir()

    def setLocation(self, root, path):
        self.root = root
        self.path = path
        self.listdir()

    def listdir(self):
        self.lst.empty()

        if self.root == "":

            for name in self.state.listroots():
                file_info = {'name': name, 'isDir': True, "size": 0}
                item = FileInfoWidget(file_info)
                item.openDirectory.connect(self._onOpenRoot)
                self.lst.append(item)
        else:

            file_info = {'name': "..", 'isDir': True, "size": 0}
            item = FileInfoWidget(file_info)
            item.openDirectory.connect(self._onOpenParent)
            self.lst.append(item)

            for file_info in self.state.listdir(self.root, self.path):
                item = FileInfoWidget(file_info)
                item.openDirectory.connect(self._onOpenDirectory)
                item.openPreview.connect(self._onOpenPreview)
                self.lst.append(item)

    def onOpenDirectory(self, file_info):
        self.path = os.path.join(self.path, file_info['name'])
        self.listdir()
        self.location.emit(self.root, self.path)

    def onOpenPreview(self, file_info):
        path = os.path.join(self.path, file_info['name'])
        self.menu.setTextContent(
            self.state.renderContent(self.root, path), ".txt")
        self.menu.show()

    def onOpenParent(self, file_info):

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

class SettingsPage(gui.Page):
    def __init__(self, state, *args, **kwargs):
        super(SettingsPage, self).__init__(*args, **kwargs)

        self.state = state

        self.vbox = gui.VBox(height="100%", width="100%", parent=self)
        self.btn_logout = gui.Button("logout", parent=self.vbox)
        self.btn_logout.onclick.connect(self.onLogout)

    def onLogout(self, widget):
        self.state.clear_authentication()

class HomePage(gui.Page):
    def __init__(self, *args, **kwargs):
        super(HomePage, self).__init__(*args, **kwargs)

        self.vbox = gui.VBox(height="100%", width="100%", parent=self)

        self.panel = gui.Widget(parent=self.vbox)
        self.panel.style.update({
            "height": "25%",
            "width": "100%",
            "min-height": "240px",
            "background": "#aaaaaa",
        })
        del self.panel.style['margin']

        self.label_email = gui.Label("Home:", parent=self.panel)
        self.label_email.style.update({"width": "80%", "margin-left": "10%", "margin-right": "10%"})
        del self.label_email.style['margin']

        self.hbox_submit = gui.Widget(parent=self.panel)
        self.hbox_submit.style.update({"width": "80%", "margin-left": "10%", "margin-right": "10%", "background": "transparent"})
        self.hbox_submit.style.update({"display": "flex", "justify-content": "flex-end"})
        del self.hbox_submit.style['margin']

        self.btn_submit = gui.Button("login", parent=self.hbox_submit)
        self.btn_submit.style.update({"margin-top": "20px", "width": "25%"})
        del self.btn_submit.style['margin']

        self.btn_submit.onclick.connect(self.onSubmitClicked)
        self.login = gui.Signal()

    def set_state(self, location, params, cookies):
        pass

    def get_state(self):
        return [], {}, {}

    def onSubmitClicked(self, widget):

        self.login.emit()

class LoginPage(gui.Page):
    def __init__(self, *args, **kwargs):
        super(LoginPage, self).__init__(*args, **kwargs)

        self.vbox = gui.VBox(height="100%", width="100%", parent=self)

        self.panel = gui.Widget(parent=self.vbox)
        self.panel.style.update({
            "height": "25%",
            "width": "100%",
            "min-height": "240px",
            "background": "#aaaaaa",
        })
        del self.panel.style['margin']

        self.label_email = gui.Label("Email:", parent=self.panel)
        self.label_email.style.update({"width": "80%", "margin-left": "10%", "margin-right": "10%"})
        del self.label_email.style['margin']
        self.input_email = gui.Input("email", parent=self.panel)
        self.input_email.style.update({"width": "80%", "margin-left": "10%", "margin-right": "10%"})
        del self.input_email.style['margin']

        self.label_password = gui.Label("Password:", parent=self.panel)
        self.label_password.style.update({"width": "80%", "margin-left": "10%", "margin-right": "10%"})
        del self.label_password.style['margin']
        self.input_password = gui.Input("password", parent=self.panel)
        self.input_password.style.update({"width": "80%", "margin-left": "10%", "margin-right": "10%"})
        del self.input_password.style['margin']

        self.label_error = gui.Label("Invalid username or password", parent=self.panel)
        self.label_error.style.update({"display": 'none'})
        self.label_error.style.update({"width": "80%", "margin-left": "10%", "margin-right": "10%"})
        del self.label_error.style['margin']

        self.hbox_submit = gui.Widget(parent=self.panel)
        self.hbox_submit.style.update({"width": "80%", "margin-left": "10%", "margin-right": "10%", "background": "transparent"})
        self.hbox_submit.style.update({"display": "flex", "justify-content": "flex-end"})
        del self.hbox_submit.style['margin']

        self.btn_cancel = gui.Button("cancel", parent=self.hbox_submit)
        self.btn_cancel.style.update({"margin-right": "10%", "margin-top": "20px", "width": "25%"})
        del self.btn_cancel.style['margin']

        self.btn_submit = gui.Button("login", parent=self.hbox_submit)
        self.btn_submit.style.update({"margin-top": "20px", "width": "25%"})
        del self.btn_submit.style['margin']

        self.input_password.onkeyup.connect(self.onKeyUp)
        self.input_email.onkeyup.connect(self.onKeyUp)
        self.btn_submit.onclick.connect(self.onSubmitClicked)
        self.login = gui.Signal(str, str)

    def set_state(self, location, params, cookies):

        self.label_error.style.update({"display": 'none'})

    def get_state(self):
        return [], {}, {}

    def onKeyUp(self, widget, key, ctrl, shift, alt):

        if key == "Enter":
            self.login.emit(self.input_email.get_value(),
                self.input_password.get_value())

    def onSubmitClicked(self, widget):

        self.login.emit(self.input_email.get_value(),
            self.input_password.get_value())

    def set_error(self, error):
        if error:
            self.label_error.style.update({"display": 'block'})
        else:
            self.label_error.style.update({"display": 'none'})

class MainPage(gui.Page):

    def __init__(self, state, *args, **kwargs):
        super(MainPage, self).__init__(*args, **kwargs)

        self.state = state

        self.vbox = gui.VBox(height="100%", width="100%", parent=self)

        self.display = AudioDisplay(state, width="100%", parent=self.vbox)

        self.navbar = NavBar2(height="100%", width="100%", parent=self.vbox)
        self.navbar.style.update({"margin-top": NAV_HEIGHT, "z-index": "5"})
        del self.navbar.style['margin']

        self.tabNowPlaying = NowPlayingPage(self.state,
            height="100%", width="100%")

        self.tabLibrary = LibraryPage(self.state,
            height="100%", width="100%")

        print("creating tab", self.state.auth_info)
        # 'filesystem_read' in auth_info['roles'][0]['features']
        self.tabFileSystem = FileSystemPage(self.state,
            height="100%", width="100%")

        self.tabSettings = SettingsPage(self.state,
            height="100%", width="100%")

        self.tabSearchLibrary = SearchLibraryPage(self.state,
            height="100%", width="100%")

        self.navbar.addTabIcon("/res/app/playlist.svg", self.tabNowPlaying)
        self.navbar.addTabIcon("/res/app/album.svg", self.tabLibrary)
        self.navbar.addTabIcon("/res/app/search.svg", self.tabSearchLibrary)
        self.navbar.addTabIcon("/res/app/documents.svg", self.tabFileSystem)
        self.navbar.addTabIcon("/res/app/settings.svg", self.tabSettings)

    def set_state(self, location, params, cookies):
        if len(location) == 0:
            self.navbar.setIndex(0)
            self.tabNowPlaying.set_state([], params, cookies)
        elif location[0] == "queue":
            self.navbar.setIndex(0)
            self.tabNowPlaying.set_state(location[1:], params, cookies)
        elif location[0] == "library":
            self.navbar.setIndex(1)
            self.tabLibrary.set_state(location[1:], params, cookies)
        elif location[0] == "files":
            self.navbar.setIndex(2)
            self.tabFileSystem.set_state(location[1:], params, cookies)
        elif location[0] == "settings":
            self.navbar.setIndex(3)
            self.tabSettings.set_state(location[1:], params, cookies)
        else:
            raise InvalidRoute()

    def get_state(self):

        path = []
        params = {}
        cookies = {}
        index = self.navbar.index()
        if index == 0:
            path.append("queue")
            _path, _params, _cookies = self.tabNowPlaying.get_state()
            path += _path
            params.update(_params)
            cookies.update(_cookies)

        elif index == 1:
            path.append("library")
            _path, _params, _cookies = self.tabLibrary.get_state()
            path += _path
            params.update(_params)
            cookies.update(_cookies)

        elif index == 2:
            path.append("files")
            _path, _params, _cookies = self.tabFileSystem.get_state()
            path += _path
            params.update(_params)
            cookies.update(_cookies)

        elif index == 3:
            path.append("settings")
            _path, _params, _cookies = self.tabSettings.get_state()
            path += _path
            params.update(_params)
            cookies.update(_cookies)

        return path, params, cookies

class AppPage(gui.Page):

    def __init__(self, state, *args, **kwargs):
        super(AppPage, self).__init__(*args, **kwargs)

        self.style.update({"height": "100%", "width": "100%"})

        self.state = state

        # custom css, flex box grid layouts
        # https://www.w3schools.com/css/css_attribute_selectors.asp
        # attribute selectors

        self.hbox_main = gui.Widget(parent=self)
        self.hbox_main.attributes.update({"class": "flex-grid-thirds"})
        self.hbox_main.style.update({"height": "100%", "width": "100%"})

        border_left = gui.Widget(parent=self.hbox_main)
        border_left.attributes.update({"class": "col-left", "z-index": "-2"})
        border_left.style.update({"background": "#222222"})

        self.page_main = None
        self.page_login = None

        self.page_home = HomePage()
        self.page_home.attributes.update({"class": "col-main"})
        self.page_home.style.update({"height": "100%", "display": "flex"})
        self._openLoginPage = gui.Slot(self.openLoginPage)
        self.page_home.login.connect(self._openLoginPage)
        self.hbox_main.insert(1, self.page_home)

        border_right = gui.Widget(parent=self.hbox_main)
        border_right.attributes.update({"class": "col-right"})
        border_right.style.update({"background": "#222222"})

        self.pages = [self.page_home]

    def set_state(self, location, params, cookies):

        if self.page_main is not None and not self.state.is_authenticated():
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

            self.state.set_authentication(cookies.get("yue_token", None))

            if len(location) == 0:
                self.page_home.set_visible(True)
                self.page_home.set_state([], params, cookies)
                print("done")
            elif location[0] == 'm':
                if self.state.is_authenticated():
                    page = self.getMainPage()
                else:
                    page = self.getLoginPage()
                page.set_visible(True)
                page.set_state(location[1:], params, cookies)
            elif location[0] == "login" and len(location) == 1:
                page = self.getLoginPage()
                page.set_visible(True)
                page.set_state(location[1:], params, cookies)
            else:
                # TODO: 404 page -> home page
                self.page_home.set_visible(True)
                self.page_home.set_state(location, params, cookies)

        except InvalidRoute as e:
            # TODO: 404 page -> home
            for page in self.pages:
                page.set_visible(False)
            self.page_home.set_visible(True)
            self.page_home.set_state([], {}, {})
        except AuthenticationError as e:
            # TODO: 404 page -> home
            for page in self.pages:
                page.set_visible(False)
            self.page_home.set_visible(True)
            self.page_home.set_state([], {}, {})

        return

    def get_state(self):

        path = []
        params = {}
        cookies = {}

        if self.page_home.is_visible():
            pass

        elif self.page_main is not None and self.page_main.is_visible():
            path.append("m")
            _path, _params, _cookies = self.page_main.get_state()
            path += _path
            params.update(_params)
            cookies.update(_cookies)

        elif self.page_login is not None and self.page_login.is_visible():
            path.append("login")
            _path, _params, _cookies = self.page_login.get_state()
            path += _path
            params.update(_params)
            cookies.update(_cookies)

        return path, params, cookies

    def getLoginPage(self):

        if self.page_login is None:
            self.page_login = LoginPage()
            self.page_login.attributes.update({"class": "col-main"})
            self.page_login.style.update({"height": "100%", "display": "flex"})
            self._onLogin = gui.Slot(self.onLogin)
            self.page_login.login.connect(self._onLogin)
            self.hbox_main.insert(1, self.page_login)
            self.pages.append(self.page_login)

        return self.page_login

    def getMainPage(self):

        if self.page_main is None:
            self.page_main = MainPage(self.state)
            self.page_main.attributes.update({"class":"col-main"})
            self.page_main.style.update({"height": "100%", "display": "flex"})
            self.hbox_main.insert(1, self.page_main)
            self.pages.append(self.page_main)
        return self.page_main

    def onLogin(self, username, password):

        try:
            self.state.authenticate(username, password)

            self.getLoginPage().set_error(False)
            for page in self.pages:
                page.set_visible(False)
            self.getMainPage().set_visible(True)
        except Exception as e:
            logging.exception(e)
            self.getLoginPage().set_error(True)

    def openLoginPage(self):
        for page in self.pages:
            page.set_visible(False)
        self.getLoginPage().set_visible(True)
