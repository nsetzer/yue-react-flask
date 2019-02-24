
import os, sys
import logging

"""
settings:
    button to delete  current playlist
    test page layout when no playlist exists

    slider for audio volume 10% - 100%

File "/opt/yueserver/yueserver/framework/backend.py", line 571, in socket_send
    for socketId in self.websockets:
RuntimeError: Set changed size during iteration

res/
    log if file exsits, use send file, not send from directory



"""
from ...framework import gui
from ...framework.backend import InvalidRoute

from ...dao.util import string_quote, format_bytes
from ...dao.storage import CryptMode

from .exception import AuthenticationError, LibraryException

NAV_HEIGHT = "6em"
NAVBAR_HEIGHT = "2em"

class RhombusLabel(gui.Widget):

    def __init__(self, text, *args, **kwargs):
        kwargs['_type'] = 'div'
        super(RhombusLabel, self).__init__(*args, **kwargs)

        self.label = gui.Label(text)
        self.add_child("content", self.label)

        rhombus = {
          "background": "#AAA",
          "margin": "0px auto",
          "border": "1px solid #000",
          "display": "inline-block",
          "padding-left": ".5em",
          "padding-right": ".5em",
          "width": "auto",
          "height": "auto",
          "transform": "skewX(-30deg)",
          "cursor": "pointer",
        }
        self.style.update(rhombus)

        self.label.style.update({"transform": "skewX(30deg)"})
        self.label.style['margin'] = '0'

class Palette(object):

    P_LIGHT     = "#3475B3"  # "#1455A3"  # "#0D5199"
    P_MID_LIGHT = "#325EA2"  # "#124E92"  # "#104479"
    P_MID       = "#2D4991"  # "#0D3981"  # "#0C3662"
    P_MID_DARK  = "#152480"  # "#052460"  # "#052445"
    P_DARK      = "#131579"  # "#031539"  # "#031528"

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
        self.hbox.style['background'] = "transparent"

        self.actions = []

    def addAction(self, icon_url, callback):

        btn = gui.Button()
        btn.onclick.connect(lambda w: callback())
        img = gui.Image(icon_url, parent=btn)
        img.style.update({"width": "100%", "height": "100%"})
        return self.addWidget(btn)

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
        return widget

    def _addWidget(self, widget):
        self.hbox.append(widget)
        self.actions.append(widget)
        return widget

class FileInfoWidget(gui.Widget):
    """docstring for FileInfoWidget"""
    def __init__(self, file_info, *args, url=None, **kwargs):
        super(FileInfoWidget, self).__init__()

        self.file_info = file_info

        self.hbox = gui.Widget(height="100%", width="100%", parent=self)
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
                icon_url = '/res/app/return.svg'
            else:
                icon_url = '/res/app/folder.svg'
        else:
            icon_url = '/res/app/file.svg'
        self.img_icon = gui.Image(icon_url)
        self.img_icon.style.update({
            "height": "32px",
            "width": "32px",
            "margin-left": "3%",
            "margin-left": "3%",
            "margin-right": "3%",
        })
        del self.img_icon.style['margin']

        self.lbl_path = gui.Label(file_info['name'],
            width="100%", height="100%")
        self.lbl_path.style.update({
            "overflow": "hidden",
            "white-space": "nowrap",
            "text-overflow": "ellipsis",
        })

        self.openDirectory = gui.Signal(object)
        self.openPreview = gui.Signal(object)

        self.hbox.append(self.img_icon, "img_icon")
        self.hbox.append(self.lbl_path, "lbl_title")

        if self.file_info['isDir']:
            btn = gui.Button("", parent=self.hbox, image="/res/app/open.svg")
            btn.onclick.connect(self._onOpenClicked)
            btn.style.update({
                "width": "4em",
                "margin-left": "1em",
                "margin-right": "1em",
                "background": "transparent"
            })
            del btn.style['margin']

        else:

            if url:
                btn = gui.Button("", parent=self.hbox, image="/res/app/download.svg")
                btn.onclick.connect(self._onOpenPreviewClicked)
                btn.style.update({
                    "width": "4em",
                    "margin-left": "1em",
                    "margin-right": ".5em",
                    "background": "transparent"
                })
                del btn.style['margin']

                js = "downloadUrl('%s', '%s', '%s');" % (
                    btn.identifier, url, self.file_info['name'])
                btn.attributes['onclick'] = js

                btn.onfailure = gui.ClassEventConnector(self, 'onfailure',
                    lambda *args, **kwargs: tuple([kwargs.get('status', None)]))
                btn.onfailure.connect(self.onFileDownloadFailure)

                btn.onsuccess = gui.ClassEventConnector(self, 'onsuccess',
                    lambda *args, **kwargs: tuple())
                btn.onsuccess.connect(self.onFileDownloadSuccess)

            btn = gui.Button("", parent=self.hbox, image="/res/app/preview.svg")
            btn.onclick.connect(self._onOpenPreviewClicked)
            btn.style.update({
                "width": "4em",
                "margin-left": "0",
                "margin-right": "1em",
                "background": "transparent"
            })
            del btn.style['margin']

    def _onOpenClicked(self, widget):
        if self.file_info['isDir']:
            self.openDirectory.emit(self.file_info)

    def _onOpenPreviewClicked(self, widget):
        if not self.file_info['isDir']:
            self.openPreview.emit(self.file_info)

    def onFileDownloadSuccess(self, *args):
        print("download success", args)

    def onFileDownloadFailure(self, *args):
        print("download success", args)

class SmallNoteCardWidget(gui.Widget):

    def __init__(self, info, *args, **kwargs):
        super(SmallNoteCardWidget, self).__init__()

        self.style.update({
            "border-style": "solid",
            "border-width": "1px",
            "border-radius": "10px 10px 10px 10px",
            "margin-top": "5px",
            "margin-left": "10px",
            "margin-right": "10px",
            "margin-bottom": "10px",
            "box-shadow": "5px 5px 5px rgba(0, 0, 0, 0.5);",
        })
        del self.style['margin']

        self.actionBar = IconBarWidget()
        self.actionBar.style.update({
            "background": "transparent",
            "border-bottom": "1px solid",
        })
        self.append(self.actionBar)

        self.actionBar.addAction("/res/app/edit.svg", self._onEditClicked)
        self.lblTitle = gui.Label("", style={
            "display": "inline",
            "width": "100%",
            "margin": "auto"
        })
        self.actionBar.addWidget(self.lblTitle)

        self.lst = gui.WidgetList()
        self.lst.style.update({
            "background": "transparent"
        })
        self.append(self.lst)

        self.edit = gui.Signal()

        self.setInfo(info)

    def _onEditClicked(self):
        self.edit.emit()

    def _summarize(self, text):
        max_length = 140

        # get at most N characters, prevent splitting a word
        subtext = text[:max_length + 1]
        if len(text) > max_length:
            index = subtext.rfind(" ")
            subtext = subtext[:index]

        # split into multiple lines
        lines = subtext.replace("\r", "").split("\n")[:5]
        if len(text) > max_length:
            lines.append("...")
        return lines

    def setInfo(self, info):
        self.info = info

        title = info['name']
        content = info['content']
        summary = self._summarize(content)

        self.lblTitle.set_text(title)

        self.lst.empty()

        for line in summary:
            if not line:
                line = "\u00A0"
            lbl = gui.Label(line, width="80%")
            lbl.style.update({
                "background": "transparent",
                "margin-bottom": "2px",
                "margin-top": "2px",
                "margin-left": "auto",
                "margin-right": "auto",
            })
            del lbl.style['margin']
            self.lst.append(lbl)

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
            "overflow-y": "scroll",
            "overflow-x": "hidden",
        })

        self.content_scroll.attributes.update({
            "onscroll": "elementScrolled(this, '%s')" % self.identifier})

        if child is not None:
            self.content_scroll.append(child)
        self.content.append(self.content_scroll)
        super(ScrollBox, self).append(self.content)

        self.onscrollend = gui.ClassEventConnector(self, 'onscrollend',
            lambda *args, **kwargs: tuple())
        self.onscrollend.connect(self.onScrollEnd)

        self.scrollend = gui.Signal()

    def append(self, widget):
        self.content_scroll.append(widget)

    def onScrollEnd(self, widget):
        self.scrollend.emit()

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
        self.scrollbox.scrollend.connect(gui.Slot(self.onScrollEnd))
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

    def onScrollEnd(self):

        name, child = self.current()
        child.requestMoreData()

class VolumeSlider(gui.Input):

    def __init__(self, default_value='', min=0, max=100, step=1, **kwargs):
        """
        Args:
            default_value (str):
            min (int):
            max (int):
            step (int):
            kwargs: See Widget.__init__()
        """
        super(VolumeSlider, self).__init__('range', default_value, **kwargs)
        self.attributes['min'] = str(min)
        self.attributes['max'] = str(max)
        self.attributes['step'] = str(step)
        self.attributes[gui.Widget.EVENT_ONCHANGE] = \
            "console.log(this.value);"

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
            "width": "90%",
            "top": "50%",
            "left": "50%",
            "transform": "translate(-50%, -50%)",
            "background": "rgb(240,230,230)",
            "z-index": 100,
            "border": "solid"
        })

        self.vbox = gui.VBox(parent=self)
        self.vbox.style['background'] = "transparent"
        self.vbox.style['height'] = "100%"

        self.btn0 = gui.Button("exit", width="2em", height="2em", parent=self.vbox)
        self.btn0.onclick.connect(lambda w: self.reject())
        self.btn0.style['margin'] = "1em"
        self.btn0.style['align-self'] = 'flex-end'

        # #####################################################################
        # preview text
        self.scrollbox = ScrollBox(None, parent=self.vbox)
        self.scrollbox.style['height'] = "50vh"
        self.scrollbox.style['display'] = "none"
        self.wpre = gui.Widget(_type="pre", parent=self.scrollbox)
        self.wpre.style['padding-left'] = ".25em"
        self.wpre.style['padding-right'] = ".25em"
        self.wpre.style['margin-left'] = "2em"
        self.wpre.style['margin-right'] = "2em"
        self.wpre.style['border-left'] = "1px solid black"
        self.wpre.style['border-right'] = "1px solid black"
        del self.wpre.style['margin']
        self.code = gui.Widget(_type="code", parent=self.wpre)

        # #####################################################################
        # preview media
        self.div_image = gui.Widget(_type="div", parent=self.vbox)
        self.div_image.style.update({
            "width": "80%",
            "margin-left": "5em",
            "margin-right": "5em",
            "margin-bottom": "1em",
            "margin-top": "1em",
            "background": "transparent",
        })
        del self.div_image.style['margin']

        self.video_preview = gui.VideoPlayer("", parent=self.div_image)
        self.video_preview.style.update({
            "max-width": "100%",
            "display": "none",
        })
        del self.video_preview.style['margin']

        self.audio_preview = gui.AudioPlayer("", parent=self.div_image)
        self.audio_preview.style.update({
            "width": "100%",
            "display": "none",
        })
        del self.audio_preview.style['margin']

        self.image_preview = gui.Image("", parent=self.div_image)
        self.image_preview.style.update({
            "width": "auto",
            "height": "auto",
            "max-width": "100%",
            "max-height": "70vh",
            "margin-left": "auto",
            "margin-right": "auto",
            "display": "none",
        })
        del self.image_preview.style['margin']

    def setTextContent(self, text):
        self.scrollbox.style['display'] = 'block'
        self.audio_preview.style['display'] = 'none'
        self.video_preview.style['display'] = 'none'
        self.image_preview.style['display'] = 'none'

        self.code.add_child("content", text)

    def setImageContent(self, url):

        self.scrollbox.style['display'] = 'none'
        self.audio_preview.style['display'] = 'none'
        self.video_preview.style['display'] = 'none'
        self.image_preview.style['display'] = 'block'

        self.image_preview.set_image(url)

    def setAudioContent(self, url):

        self.scrollbox.style['display'] = 'none'
        self.audio_preview.style['display'] = 'inline'
        self.video_preview.style['display'] = 'none'
        self.image_preview.style['display'] = 'none'

        self.audio_preview.set_source(url)

    def setVideoContent(self, url):

        self.scrollbox.style['display'] = 'none'
        self.audio_preview.style['display'] = 'none'
        self.video_preview.style['display'] = 'inline'
        self.image_preview.style['display'] = 'none'

        self.video_preview.set_source(url)

    def reject(self):
        self.style['display'] = 'none'

    def accept(self, index):
        self.style['display'] = 'none'

    def show(self):
        self.style['display'] = 'block'

# ---------------------

class ContentPage(gui.Page):
    """docstring for ContentPage"""
    def __init__(self, *args, **kwargs):
        super(ContentPage, self).__init__(*args, **kwargs)

    # TODO: define a way to register a content generator
    #    which yields widgets, to be appended to a
    #    list, which is also registered

    def requestMoreData(self):
        """
        A method which is called when the user has requested more
        dynamic data to be loaded.

        Instead of returning all query results at once, display the
        first page and wait for this signal before appending more data
        to the current view
        """
        print("%s: request more data" % self.__class__.__name__)

class NowPlayingPage(ContentPage):
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

class LibraryPage(ContentPage):
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
            wdt = IconBarWidget()
            wdt.addAction("/res/app/return.svg", lambda: self.onOpenElement(0))
            wdt.style.update({
                "top": "0",
                "position": "sticky",
                "z-index": "1",
                "border-bottom": "1px solid",
            })
            self.lst.append(wdt)

            for i, artist in enumerate(self.domain_info['artists']):
                item = TitleTextWidget('/res/app/microphone.svg', artist['name'])
                slot = gui.Slot(lambda i=i: self.onOpenAlbums(i))
                item.open.connect(slot)
                self.lst.append(item)

        elif index == 2:  # show artist albums

            wdt = IconBarWidget()
            wdt.style.update({
                "top": "0",
                "position": "sticky",
                "z-index": "1",
                "border-bottom": "1px solid",
            })
            self.lst.append(wdt)

            artist = self.domain_info['artists'][self.page_artist_index]['name']
            query = "artist==%s" % string_quote(artist)

            wdt.addAction("/res/app/return.svg", lambda: self.onOpenElement(1))
            wdt.addAction("/res/app/shuffle.svg", lambda: self.onRandomPlay(query))

            albums = self.domain_info['artists'][self.page_artist_index]['albums']
            self.page_albums = list(sorted(albums.items()))
            for i, (album, count) in enumerate(self.page_albums):
                item = TitleTextWidget('/res/app/album.svg', album)
                slot = gui.Slot(lambda i=i: self.onOpenAlbumSongs(i))
                item.open.connect(slot)
                self.lst.append(item)

        elif index == 3:  # Genres
            wdt = IconBarWidget()
            wdt.style.update({
                "top": "0",
                "position": "sticky",
                "z-index": "1",
                "border-bottom": "1px solid",
            })
            self.lst.append(wdt)
            wdt.addAction("/res/app/return.svg", lambda: self.onOpenElement(0))

            for i, genre in enumerate(self.domain_info['genres']):
                item = TitleTextWidget('/res/app/genre.svg', genre['name'])
                item.open.connect(gui.Slot(lambda i=i: self.onOpenGenre(i)))
                self.lst.append(item)

        elif index == 4:  # Songs

            wdt = IconBarWidget()
            wdt.style.update({
                "top": "0",
                "position": "sticky",
                "z-index": "1",
                "border-bottom": "1px solid",
            })
            self.lst.append(wdt)
            wdt.addAction("/res/app/return.svg", lambda: self.onOpenElement(2))
            wdt.addAction("/res/app/shuffle.svg", lambda: self.onRandomPlay(self.page_query))

            item = TitleTextWidget('/res/app/return.svg', "Random Play All")
            item.open.connect(gui.Slot(lambda: self.onRandomPlay(self.page_query)))
            self.lst.append(item)

            for song in self.context.search(self.page_query):
                item = SongWidget(song, index=index)
                item.openMenu.connect(self._onOpenSongMenu)
                self.lst.append(item)

        elif index == 5:
            wdt = IconBarWidget()
            wdt.style.update({
                "top": "0",
                "position": "sticky",
                "z-index": "1",
                "border-bottom": "1px solid",
            })
            self.lst.append(wdt)
            wdt.addAction("/res/app/return.svg", lambda: self.onOpenElement(3))
            wdt.addAction("/res/app/shuffle.svg", lambda: self.onRandomPlay(self.page_query))

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

class SearchLibraryPage(ContentPage):
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

class FileSystemPage(ContentPage):
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

        self.hbox_path = gui.Widget(parent=self)
        self.hbox_path.style.update({
            "padding-top": ".75em",
            "padding-bottom": ".75em",
            "padding-left": "1em",
            "padding-right": "1em",
        })
        RhombusLabel("roots", parent=self.hbox_path)
        RhombusLabel("default", parent=self.hbox_path)
        RhombusLabel("secure", parent=self.hbox_path)
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
        self.hbox_path.empty()
        self.lst.empty()

        self.menu.reject()

        if self.root == "":

            lbl = RhombusLabel("Home", parent=self.hbox_path)
            lbl.style['background'] = "#CCF"
            lbl.style['cursor'] = "#none"

            for name in self.context.listroots():
                file_info = {'name': name, 'isDir': True, "size": 0}
                item = FileInfoWidget(file_info)
                item.openDirectory.connect(self._onOpenRoot)
                self.lst.append(item)
        else:

            if self.path:
                urlbase = "%s/%s/" % (self.root, self.path)
            else:
                urlbase = "%s/" % (self.root)

            wdt = IconBarWidget()
            wdt.style.update({
                "top": "0",
                "position": "sticky",
                "z-index": "1",
                "border-bottom": "1px solid",
            })
            wdt.addAction("/res/app/return.svg", self.onOpenParent)

            btn = gui.UploadFileButton(urlbase, image="/res/app/upload.svg")
            btn.style.update({"width": "2em", "height": "2em"})
            btn.onsuccess.connect(self.onFileUploadSuccess)
            btn.onfailure.connect(self.onFileUploadFailure)
            wdt.addWidget(btn)
            self.lst.append(wdt)

            lbl = RhombusLabel("Home", parent=self.hbox_path)
            lbl.onclick.connect(lambda x: self.onNavigate("", ""))
            lbl = RhombusLabel(self.root, parent=self.hbox_path)
            lbl.onclick.connect(lambda x, r=self.root: self.onNavigate(r, ""))
            components = self.path.split('/')
            component_path = ""
            for component in components:
                if component:
                    component_path += component
                    lbl = RhombusLabel(component, parent=self.hbox_path)
                    lbl.onclick.connect(
                        lambda x, r=self.root, p=component_path:
                            self.onNavigate(r, p))
                    component_path += "/"
            lbl.style['background'] = "#CCF"
            lbl.style['cursor'] = "#none"
            lbl.onclick.disconnect()

            session_dirs = self.session_directories.get(
                (self.root, self.path), set())

            items = self.context.listdir(self.root, self.path)

            for file_info in items:

                if file_info['name'] in session_dirs:
                    session_dirs.remove(file_info['name'])

                url = "/api/gui/files/%s/path/%s/%s?dl=1" % (
                    self.root, self.path, file_info['name'])

                item = FileInfoWidget(file_info, url=url)
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

        info = self.context.fileInfo(self.root, path)
        print(file_info, info.file_path)

        url = "/api/gui/files/%s/path%s?dl=0" % (self.root, info.file_path)
        ext = file_info['name'].split('.')[-1].lower()

        if info.encryption in (CryptMode.server, CryptMode.client):
            content = "error: file is encrypted"
            self.menu.setTextContent(content)
        elif ext in ("jpg", "jpeg", "png", "gif"):
            self.menu.setImageContent(url)
        elif ext in ("ogg", "mp3", "wav"):
            self.menu.setAudioContent(url)
        elif ext in ("webm", "mp4"):
            self.menu.setVideoContent(url)
        else:
            content = self.context.renderContent(info)
            self.menu.setTextContent(content)

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
        self.listdir()

    def onFileUploadFailure(self, widget, filepath):
        print("failed", filepath)

    def onNavigate(self, root, path):

        self.root = root
        self.path = path
        self.listdir()
        self.location.emit(self.root, self.path)

class SettingsPage(ContentPage):
    def __init__(self, context, *args, **kwargs):
        super(SettingsPage, self).__init__(*args, **kwargs)

        self.context = context

        self.vbox = gui.VBox(height="100%", width="100%", parent=self)

        self.btn_logout = gui.Button("logout", parent=self.vbox)
        self.btn_logout.onclick.connect(self.onLogout)
        self.btn_logout.style['margin'] = "1em"

        self.lst = gui.WidgetList(parent=self)

        wdt = gui.Widget(_type="li", parent=self.lst)
        box = gui.HBox(parent=wdt)
        lbl1 = gui.Label("Volume", parent=box)
        lbl2 = VolumeSlider(parent=box)

        self.lst_info = gui.WidgetList(parent=self)

    def onLogout(self, widget):
        self.context.clear_authentication()

    def onOpen(self):
        status = self.context.healthcheck()
        flat = {}
        for key1, obj in status.items():
            if isinstance(obj, dict):
                for key2, val in obj.items():
                    flat["%s_%s" % (key1, key2)] = str(val)
            else:
                flat[key1] = str(obj)

        self.lst_info.empty()
        for key, val in sorted(flat.items()):
            wdt = gui.Widget(_type="li", parent=self.lst_info)
            box = gui.HBox(parent=wdt)
            lbl1 = gui.Label(key, parent=box)
            lbl2 = gui.Label(val, parent=box)

class NotesPage(ContentPage):
    """docstring for NotesPage"""
    def __init__(self, context, *args, **kwargs):
        super(NotesPage, self).__init__(*args, **kwargs)
        self.context = context

        self.style.update({"height": "100%"})

        self.lst = gui.WidgetList()
        self.lst.style.update({"height": "100%"})
        self.append(self.lst)

        self.actionBarMain = IconBarWidget()
        self.actionBarMain.style.update({
            "top": "0",
            "position": "sticky",
            "z-index": "1",
            "border-bottom": "1px solid",
        })

        self.actionBarMain.addAction("/res/app/create.svg",
            self.onCreateNote)

        self.actionBarEdit = IconBarWidget()
        self.actionBarEdit.style.update({
            "top": "0",
            "position": "sticky",
            "z-index": "1",
            "border-bottom": "1px solid",
        })

        self.actionBarEdit.addAction("/res/app/save.svg",
            lambda: self.onCloseNote(True))
        self.actionBarEdit.addAction("/res/app/media_error.svg",
            lambda: self.onCloseNote(False))

        self.textTitle = gui.TextInput(True)
        self.textEdit = gui.TextInput(False)
        self.textEdit.style.update({"height": "100%"})
        del self.textEdit.style['margin']
        # maxlength

        self._opened = False

    def loadNotes(self):
        # TODO: this needs to be a background process
        self.notes = []
        for info in self.context.listNotes():
            note = SmallNoteCardWidget(info)
            self.notes.append(note)

    def onOpen(self):
        super().onOpen()
        if not self._opened:
            self._opened = True
            self.loadNotes()
            self.showPage()

    def showPage(self, index=None):

        self.lst.empty()
        if index is None or index < 0 or index >= len(self.notes):
            self.lst.append(self.actionBarMain)
            for i, note in enumerate(self.notes):
                self.lst.append(note)
                note.edit.clear()
                note.edit.connect(gui.Slot(lambda i=i: self.onEditNote(i)))
            self.current_index = None
        else:
            self.lst.append(self.actionBarEdit)
            self.lst.append(self.textTitle)
            self.lst.append(self.textEdit)

            note = self.notes[index]

            self.textTitle.set_value(note.info['name'])
            self.textEdit.set_value(note.info['content'])
            self.current_index = index

    def get_route(self):
        path = ""
        if self.current_index is not None:
            path = str(self.current_index)
        return [path], {}, {}

    def set_route(self, location, params, cookies):
        if len(location) > 0:
            self.showPage(int(location[0]))
        else:
            self.showPage()

    def _generateName(self, base):
        # generate a unique name for this note
        name = base
        count = 2
        index = 0
        while index < len(self.notes):
            note = self.notes[index]
            if note.info['name'] == name:
                index = 0
                name = "%s %d" % (base, count)
                count += 1
            index += 1
        return name

    def onCreateNote(self):

        name = self._generateName("New Note")
        info = {'name': name, 'content': ''}
        note = SmallNoteCardWidget(info)
        index = len(self.notes)
        self.notes.append(note)
        self.showPage(index)

    def onCloseNote(self, save):

        if save:
            note = self.notes[self.current_index]
            cur_name = note.info['name']
            txt_name = self.textTitle.get_value().strip()

            remove_path = None
            if cur_name != txt_name:
                # cache the old path, to delete after saving
                if 'file_path' in note.info:
                    remove_path = note.info['file_path']
                note.info['name'] = self._generateName(txt_name)
                note.info['file_name'] = note.info['name'] \
                    .replace(" ", "_") + ".txt"
                note.info['file_path'] = "public/notes/%s" % note.info['file_name']
            elif 'file_path' not in note.info:
                note.info['file_name'] = note.info['name'] \
                    .replace(" ", "_") + ".txt"
                note.info['file_path'] = "public/notes/%s" % note.info['file_name']

            logging.info("saving note: %s" % note.info['file_path'])
            content = self.textEdit.get_value()
            note.info['content'] = content

            # todo, create a rename api to preserve version number
            self.context.setNoteContent(note.info['file_path'], content)
            if remove_path:
                self.context.removeNote(remove_path)

            note.setInfo(note.info)

        self.showPage()

    def onEditNote(self, index):

        self.showPage(index)

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

        self.icon = gui.Image("/res/icon2.png", parent=self.panel)
        self.icon.style.update({
            "display": "block",
            "margin-left": "auto",
            "margin-right": "auto",
            "margin-bottom": "1em",
        })
        del self.icon.style['margin']

        self.label_title = gui.Label("Welcome", parent=self.panel)
        self.label_title.style.update({
            "text-align": "center",
            "font-size": "1.5em"
        })
        del self.label_title.style['margin']

        self.btn_submit = gui.Button("login", parent=self.panel)
        self.btn_submit.style.update({
            "margin-top": "0",
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

class PublicAccessPage(gui.Page):
    """
    Signals:
        submit()
    """
    def __init__(self, context, *args, **kwargs):
        super(PublicAccessPage, self).__init__(*args, **kwargs)

        self.context = context
        self.file_info = None

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

        self.label_title = gui.Label("Download File", parent=self.panel)
        self.label_title.style.update({
            "text-align": "center",
            "font-size": "1.5em"
        })
        del self.label_title.style['margin']

        self.label_name = gui.Label("File Name:", parent=self.panel)
        self.label_name.style.update({
            "width": "80%",
            "margin-left": "10%",
            "margin-right": "10%",
            "margin-bottom": "0",
            "margin-top": "1em",
            "font-weight": "bold"
        })
        del self.label_name.style['margin']

        self.label_name_value = gui.Label("", parent=self.panel)
        self.label_name_value.style.update({
            "width": "80%",
            "margin-left": "10%",
            "margin-right": "10%",
            "margin-bottom": "0",
            "margin-top": "1em",
        })
        del self.label_name_value.style['margin']

        self.label_size = gui.Label("File Size:", parent=self.panel)
        self.label_size.style.update({
            "width": "80%",
            "margin-left": "10%",
            "margin-right": "10%",
            "margin-bottom": "0",
            "margin-top": "1em",
            "font-weight": "bold"
        })
        del self.label_size.style['margin']

        self.label_size_value = gui.Label("", parent=self.panel)
        self.label_size_value.style.update({
            "width": "80%",
            "margin-left": "10%",
            "margin-right": "10%",
            "margin-bottom": "0",
            "margin-top": "1em",
        })
        del self.label_size_value.style['margin']

        self.label_password = gui.Label("Password:", parent=self.panel)
        self.label_password.style.update({
            "width": "80%",
            "margin-left": "10%",
            "margin-right": "10%",
            "margin-bottom": "0",
            "margin-top": "1em",
            "font-weight": "bold"
        })
        del self.label_password.style['margin']

        self.div_image = gui.Widget(_type="div", parent=self.panel)
        self.div_image.style.update({
            "width": "60%",
            "margin-left": "20%",
            "margin-right": "20%",
            "margin-bottom": "0",
            "margin-top": "1em",
            "background": "transparent",
        })
        del self.div_image.style['margin']

        self.audio_preview = gui.AudioPlayer("", parent=self.div_image)
        self.audio_preview.style.update({
            "display": "none",
        })
        del self.audio_preview.style['margin']

        self.image_preview = gui.Image("", parent=self.div_image)
        self.image_preview.style.update({
            "max-width": "100%",
            "display": "none",
        })
        del self.image_preview.style['margin']

        self.form_login = gui.Widget(_type="form", parent=self.panel)
        self.form_login.attributes['autocomplete'] = "off"

        self.input_password = gui.Input("text", parent=self.form_login)
        self.input_password.attributes['tabindex'] = "2"
        self.input_password.attributes['autocomplete'] = "off"
        self.input_password.attributes['autofocus'] = True
        self.input_password.attributes['name'] = "public"
        self.input_password.style.update({
            "width": "80%",
            "margin-left": "10%",
            "margin-right": "10%"
        })
        del self.input_password.style['margin']

        self.label_status = gui.Label("", parent=self.panel)
        self.label_status.style.update({
            "width": "80%",
            "margin-left": "10%",
            "margin-right": "10%",
            "margin-bottom": "0",
            "margin-top": "1em",
        })
        del self.label_status.style['margin']

        self.btn_download = gui.Button("Download", parent=self.panel)
        self.btn_download.style.update({
            "margin-top": "20px",
            "margin-left": "33%",
            "margin-right": "33%",
            "width": "34%"
        })
        del self.btn_download.style['margin']

        js = "alert('error');"
        self.btn_download.attributes['onclick'] = js

        self.onfailure = gui.ClassEventConnector(self, 'onfailure',
            lambda *args, **kwargs: tuple([kwargs.get('status', None)]))
        self.onfailure.connect(self.onFailure)

        self.onsuccess = gui.ClassEventConnector(self, 'onsuccess',
            lambda *args, **kwargs: tuple())
        self.onsuccess.connect(self.onSuccess)

        self.route = ([], {}, {})

    def set_route(self, location, params, cookies):
        """
        persist the route that got us to a page that was not found
        """
        self.route = (location, params, cookies)

        if len(location) == 1:
            self.file_info = self.context.publicFileInfo(location[0])

        self.update()

    def get_route(self):
        return self.route

    def onSubmitClicked(self, widget):

        self.submit.emit()

    def update(self):

        if self.file_info is None:
            return

        self.label_name_value.set_text(self.file_info.name)
        self.label_size_value.set_text(format_bytes(self.file_info.size))

        if self.file_info.public_password is not None:
            self.input_password.attributes['value'] = ""
            pass
        else:
            self.label_password.style['display'] = 'none'
            self.input_password.style['display'] = 'none'

            url = "/api/fs/public/%s?dl=0" % self.file_info.public
            if self.file_info.name.endswith(".png"):
                self.image_preview.style.update({"display": "block"})
                self.audio_preview.style.update({"display": "none"})
                self.image_preview.set_image(url)

            elif self.file_info.name.endswith(".ogg"):
                self.image_preview.style.update({"display": "none"})
                self.audio_preview.style.update({"display": "block"})
                self.audio_preview.set_source(url)

        js = "downloadFile('%s', '%s', document.getElementById('%s').value);" % (
            self.identifier,
            self.file_info.public,
            self.input_password.identifier)
        self.btn_download.attributes['onclick'] = js

    def onFailure(self, widget, status):
        """
        download request failed with status
        """
        if status == 401:
            self.label_status.set_text("Invalid password")
        else:
            self.label_status.set_text("Unexpected error")

    def onSuccess(self, widget):
        """
        user successfully downloaded the file
        """
        self.label_status.set_text("Downloading File")

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
        return self.route

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
        self.input_email.attributes['name'] = "username"
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
        self.input_password.attributes['name'] = "password"
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

        self.tabNotes = NotesPage(self.context,
            height="100%", width="100%")

        self.navbar.addTabIcon("queue", "/res/app/playlist.svg", self.tabNowPlaying)
        self.navbar.addTabIcon("library", "/res/app/album.svg", self.tabLibrary)
        self.navbar.addTabIcon("search", "/res/app/search.svg", self.tabSearchLibrary)
        self.navbar.addTabIcon("files", "/res/app/documents.svg", self.tabFileSystem)
        self.navbar.addTabIcon("settings", "/res/app/settings.svg", self.tabSettings)
        self.navbar.addTabIcon("notes", "/res/app/note.svg", self.tabNotes)

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

        self.style.update({"height": "100%", "width": "100%", "z-index": "0"})

        self.context = context

        # custom css, flex box grid layouts
        # https://www.w3schools.com/css/css_attribute_selectors.asp
        # attribute selectors

        self.hbox_main = gui.Widget(parent=self)
        self.hbox_main.attributes.update({"class": "flex-grid-thirds"})
        self.hbox_main.style.update({"height": "100%", "width": "100%"})

        border_left = gui.Widget(parent=self.hbox_main)
        border_left.attributes.update({"class": "col-left"})
        border_left.style.update({
            "background": Palette.S_DARK, "z-index": "1"})

        self.page_main = None
        self.page_notfound = None
        self.page_login = None
        self.page_public = None

        self.page_home = HomePage()
        self.page_home.attributes.update({"class": "col-main"})
        self.page_home.style.update({
            "height": "100%",
            "display": "flex",
            "z-index": "2"})
        self._openLoginPage = gui.Slot(self.openLoginPage)
        self.page_home.login.connect(self._openLoginPage)
        self.hbox_main.insert(1, self.page_home)

        border_right = gui.Widget(parent=self.hbox_main)
        border_right.attributes.update({"class": "col-right"})
        border_right.style.update({
            "background": Palette.S_DARK, "z-index": "1"})

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
            elif location[0] == "p":
                page = self.getPublicPage()
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

        elif self.page_public is not None and self.page_public.is_visible():
            path.append("p")
            _path, _params, _cookies = self.page_public.get_route()
            path += _path
            params.update(_params)
            cookies.update(_cookies)

        return path, params, cookies

    def getPublicPage(self):

        if self.page_public is None:
            self.page_public = PublicAccessPage(self.context)
            self.page_public.attributes.update({"class": "col-main"})
            self.page_public.style.update({"height": "100%", "display": "flex"})
            self.hbox_main.insert(1, self.page_public)
            self.pages.append(self.page_public)

        return self.page_public

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
