#! cd ../.. && python3 -m yueserver.sync.syncui -n

# syncui cmd push arg with relative path `syncui .` does not work
# remove
# move/cut/copy/paste
#   samefile? keep both? keep all? replace? replace all?
#   after a copy/move operation between sides, refresh both sources
# move/copy/remove/rename should not cause a full refresh
# directory load robustness
#   gracefully handle errors during load()
#   pull files do not exist locally (ignore actions)
#   loading directories with many keys over slow network (partial results, cancel)
# os.path => ctxt.fs; eliminate os.* and os.path.*
# s3 file paths
#   support copy from s3 to local
#   support remove
#   support rename of FILE but not directory
# improve directory push / pop (implementation stack is confusing)
# on exit save session to session.yml in config dir
# create a FileSystemTableView from which sync table view inherits from
#   FileSystemTableView(fs)
#   contains a private class as a SignalHandler for private signals (e.g. rename)
#   takes care of basic file system operations
# eliminate icon cache, and use row height for generating icons: set Decoration
# icons
#   shortcut delighter for link file types
#   favorites icon as path to png
# remove debug colons from file state
# expand executeAction to run in the background
#   emit signal for success / failure
#   menu_action may need a "fork": [true|default: false] option
#   or "blocking", wait until tar, 7z finish, but launch cmd, terminal
# replace FileRecord -> FileSystemEntry -> {FileEntry, DirEntry}
#   use FS_UNK, FS_REG, FS_DIR, FS_LNK
# remove the reference to the locationContext from the FileTableView, use signals
# filter allow `kind = ?` where kind is image, video, document, folder
# formalize stats collection of FS implementations
#
import time
import os
import sys
ts_start = time.time()
errf = open("./werr.log", "w");
errf.write("%.3f : start\n" % ts_start);
errf.write("%s\n" % sys.stdout);
errf.flush()
print("%.3f : start" % ts_start)
errf.write("%s\n" % sys.stdout);
errf.flush()
import math
import logging
import posixpath
import shlex
import subprocess
import fnmatch
import traceback
import argparse
import struct
import socket
import uuid

import inspect

def trace(*args, **kwargs):
    frame = inspect.stack()[1]
    filename = os.path.split(frame.filename)[-1]
    print(f"{filename}:{frame.function}:{frame.lineno}", *args, **kwargs)

import PIL

if sys.platform == 'win32':
    try:
        import win32gui # for SetWindowPos
        has_win32gui = True
    except ImportError:
        has_win32gui = False
        if sys.stderr:
            sys.stderr.write("error importing win32gui")

from datetime import datetime

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *


QT_VERSION_TUPLE = tuple(int(x) for x in QT_VERSION_STR.split(".")[:3])
PYQT_V6 = QT_VERSION_TUPLE >= (6,0,0)
print(PYQT_V6)
print(Qt.Alignment.AlignLeft)

from yueserver.dao.filesys.filesys import FileSystem
from yueserver.dao.filesys.drives import get_drives
from yueserver.dao.filesys.s3fs import BotoFileSystemImpl
from yueserver.qtcommon.GridView import GridView
from yueserver.qtcommon.TableView import (
    TableError, TableModel, TableView, RowValueRole, ImageDelegate,
    SortProxyModel, RowSortValueRole, ListView, EditItemDelegate
)
from yueserver.qtcommon.exceptions import installExceptionHook
from yueserver.qtcommon import resource
from yueserver.qtcommon import tango
from yueserver.framework.config import BaseConfig, yload, ydump

from yueserver.sync import sync

from yueserver.dao.search import (
    SearchGrammar, AndSearchRule, OrSearchRule, NotSearchRule, ColumnSearchRule,
    LessThanSearchRule, GreaterThanSearchRule,
    LessThanEqualSearchRule, GreaterThanEqualSearchRule,
    PartialStringSearchRule, InvertedPartialStringSearchRule,
    Column, case_
)

# -----------------------------------------------------------------------------
if os.name == 'nt':
    cfg_base = os.path.join(os.getenv('APPDATA'))
else:
    cfg_base = os.path.expanduser("~/.config")

if os.name == 'nt':
    if 'HOME' not in os.environ:
        os.environ['HOME'] = os.path.expanduser("~")

# -----------------------------------------------------------------------------

def openNative(url):

    # TODO: replace with subprocess
    if os.name == "nt":
        os.startfile(url)
    elif sys.platform == "darwin":
        os.system("open \"%s\"" % url)
    else:
        # could also use kde-open, gnome-open etc
        # TODO: implement code that tries each one until one works
        # subprocess.call(["xdg-open",filepath])
        sys.stderr.write("open unsupported on %s" % os.name)

def openProcess(args, pwd=None, blocking=False):
    """
    pwd must be provided if it is a network path on windows.
    a network path begins with '\\' or '//'
    otherwise popen will automatically preface the path
    with the drive letter of the current working directory.
    """


    shell = sys.platform == "win32"
    proc = subprocess.Popen(args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=pwd, shell=shell)

    if blocking:
        proc.communicate()

def executeDiffAction(action, pwd, ent1, ent2):

    opts = {"pwd": pwd}

    if isinstance(ent1, sync.DirEnt):
        path = ent1.local_base
    else:
        path = ent1.local_path

    opts['left'] = path

    if isinstance(ent2, sync.DirEnt):
        path = ent2.local_base
    else:
        path = ent2.local_path

    opts['right'] = path

    args = shlex.split(action)

    args = [arg.format(**opts) for arg in args]

    return openProcess(args, pwd)

def executeAction(action, ents, pwd):
    """
    an action is a bash syntax string
    shlex is used to parse the arguments

    ent is a FileEnt or DirEnt, and used to
    format arguments after parsing

    pwd, path, filename, name, ext are valid format options
    format syntax is `echo {filename}`

        pwd      - present working directory
        path     - path of first file
        paths    - special case, all paths
        filename - filename of first file, including ext
        name     - name part of first file, excluding ext
        ext      - ext part of first file, including period
        unique   - a unique prefix

    """

    opts = {
        "pwd": pwd
    }

    paths = []

    if ents is not None and ents:

        for ent in ents:

            if isinstance(ent, sync.DirEnt):
                path = ent.local_base
            else:
                path = ent.local_path

            paths.append(path)

        # assuming single mode operation
        path = paths[0]
        _, filename = os.path.split(path)
        name, ext = os.path.splitext(filename)
        opts.update({
            "path": path,
            "filename": filename,
            "name": name,
            "ext": ext,
        })

    if '{unique}' in action:
        _, name = os.path.split(pwd)
        if not name:
            name = 'root'

        # generate a unique name by looking for existing prefixes
        i = 1
        basename = name
        contents = os.listdir(pwd)
        exists = lambda p: any([c.startswith(p) for c in contents])
        while exists(name):
            name = "%s-%d" % (basename, i)
            i += 1

        opts["unique"] = name

    args = shlex.split(action)
    i = 0
    while i < len(args):
        if args[i] == '{paths}':
            args = args[:i] + paths + args[i+1:]
            i += len(paths)
        else:
            i += 1

    args = [arg.format(**opts) for arg in args]
    print(args)

    return openProcess(args, pwd)

def openAction(fs, actions, pwd, ent):

    ftype = fs.getFileType(ent.local_path)

    text_action = None
    action = None
    for act in actions:
        supported = [stype.upper() for stype in act.get("types", [])]
        # use first action
        if action is None and ftype in supported:
            action = act.get("action", None)
        if act.get('default', False):
            text_action = act.get("action", None)

    if action is not None:
        executeAction(action, [ent], pwd)
        return

    if text_action is not None:

        is_text = False
        with open(ent.local_path, "rb") as rf:
            #g = lambda v: v == 0xD or v == 0xA or v >= 0x20
            #is_text = all(g(b) for b in rf.read(2048))
            g = lambda v: v < 0x0A
            is_text = not any(g(b) for b in rf.read(2048))
            trace("is text", is_text)

        if is_text:
            executeAction(text_action, [ent], pwd)
            return

    openNative(ent.local_path)

def gif_extract_position(path, pos=.5):

    """
    in a single pass through a file, extract one frame

    a gif may have partial updates, that are applied to the previous frame
    """
    img = PIL.Image.open(path)

    last_frame = img.convert('RGBA')
    global_palette = img.getpalette()

    for i in range(int(img.n_frames*pos)):

        if not img.getpalette():
            img.putpalette(global_palette)

        # check for a partial update
        update_region_dims = img.size
        if img.tile:
            tile = img.tile[0]
            update_region = tile[1]
            update_region_dims = update_region[2:]

        if update_region_dims != img.size:
            new_frame = PIL.Image.new('RGBA', img.size)
            new_frame.paste(last_frame)
            new_frame.paste(img, (0,0), img.convert('RGBA'))
        else:
            new_frame = img.convert('RGBA')

        last_frame = new_frame

        try:
            img.seek(img.tell() + 1)
        except EOFError:
            break;

    return img.convert('RGBA')

byte_labels = ['B', 'KB', 'MB', 'GB']
def format_bytes(b):
    kb = 1024
    for label in byte_labels:
        if b < kb:
            if label == "B":
                return "%d %s" % (b, label)
            if label == "KB":
                if b < 10:
                    return "%.2f %s" % (b, label)
                else:
                    return "%d %s" % (b, label)
            else:
                return "%.2f %s" % (b, label)
        b /= kb
    return "%d%s" % (b, byte_labels[-1])

def format_datetime(dt):
    if dt > 0:
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(dt))
    return ""

def format_mode_part(mode):
    s = ""
    s += "r" if 0x4 & mode else "-"
    s += "w" if 0x2 & mode else "-"
    s += "x" if 0x1 & mode else "-"
    return s

def format_mode(mode):
    """ format unix permissions as string
    e.g. octal 0o755 to rwxr-xr-x
    """
    if isinstance(mode, int):
        u = format_mode_part(mode >> 6)  # user
        g = format_mode_part(mode >> 3)  # group
        o = format_mode_part(mode)      # other
        return u + g + o
    return ""

def scale_image(size, img, upscale=False):

    if isinstance(size, QSize):
        xsize = size.width()
        ysize = size.height()
    else:
        xsize = ysize = size

    # scale large images down to given size
    if img.width() > xsize or img.height() > ysize:
        img = img.scaled(QSize(xsize, ysize),
            Qt.KeepAspectRatio, Qt.SmoothTransformation)

    # allow icons to be upscaled by at most 2x
    if upscale and (img.width() < xsize and img.height() < ysize):
        x = xsize
        if (xsize / img.width() > 2):
            s = img.width() * 2
        y = ysize
        if (ysize / img.height() > 2):
            y = img.height() * 2
        img = img.scaled(QSize(x, y),
            Qt.KeepAspectRatio, Qt.SmoothTransformation)

    # scale smaller images up to the given size
    x = 0
    y = 0

    if img.width() < xsize:
        x = (xsize - img.width()) // 2

    if img.height() < ysize:
        y = (ysize - img.height()) // 2

    if x > 0 or y > 0:
        img2 = QImage(xsize, ysize, QImage.Format_ARGB32)
        img2.fill(Qt.transparent)
        painter = QPainter()
        painter.begin(img2)
        painter.drawImage(QPoint(x, y), img)
        painter.end()
        img = img2

    return img

def _dummy_fetch_iter(ctxt):

    for i in range(25):

        record = {
            "remote_size": 0,
            "remote_mtime": 0,
            "remote_permission": 0,
            "remote_version": 0,
            "remote_public": None,
            "remote_encryption": None,
        }

        yield ("dummy/%d" % i, record, "mode")

        QThread.msleep(250)

def _dummy_sync_iter(ctxt, paths, push, pull, force, recursive):

    for dent in paths:

        yield sync.FileEnt(dent.remote_base, dent.local_base, None, None, None)
        yield sync.SyncResult(dent, sync.FileState.ERROR, dent.remote_base)

        QThread.msleep(250)

class SyncConfig(BaseConfig):
    def __init__(self, path):
        super(SyncConfig, self).__init__()

        self._cfg_path = path

        self.init(yload(path))

    def init(self, data):

        self.favorites = self.get_key(data, "favorites", default=[])
        if not self.favorites:
            self.favorites = self._getFavoritesDefault()

        self.state = self.get_key(data, "state", default="")

        # both open and menu actions should be a list of objects
        # {'action': '', 'text': '', 'types': [], 'default': False}
        # action: shell command
        # text: display text
        # types: file extensions (type name from type column)
        # default: True for the default text action
        self.open_actions = self.get_key(data, "open_actions", default=[])
        # {'action': '', 'text': '', 'mode': ''}
        # mode: zero|single|multiple
        self.menu_actions = self.get_key(data, "menu_actions", default=[])

        # an open action
        self.diff_action = self.get_key(data, "diff_action", default={})

        self.showHiddenFiles = True
        self.showBlacklistFiles = True

        self.rowScale = self.get_key(data, "rowScale", default=1.75)
        self.iconSize = self.get_key(data, "iconSize", default=128)

        self.buckets = self.get_key(data, "buckets", default=[])

    def save(self):

        obj = {
            "favorites": self.favorites,
            "state": self.state,
            "open_actions": self.open_actions,
            "menu_actions": self.menu_actions,
            "diff_action": self.diff_action,
            "showHiddenFiles": self.showHiddenFiles,
            "showBlacklistFiles": self.showBlacklistFiles,
            "rowScale": self.rowScale,
            "iconSize": self.iconSize,
            "buckets": self.buckets,
        }

        ydump(self._cfg_path, obj)

    def _getFavoritesDefault(self):

        def b(s, n, p, i="Folder"):
            return {"section": s, "name": n, "path": p, "icon": i}

        if sys.platform == 'darwin':
            return [
                b("system", "Root", "/", "Computer"),
                b("system", "Home", "~"),
                b("system", "Desktop", "~/Desktop", "Desktop"),
                b("system", "Documents", "~/Documents"),
                b("system", "Downloads", "~/Downloads"),
                b("system", "Music", "~/Music"),
            ]
        elif os.name == 'nt':
            return [
                b("system", "Home", "~"),
                b("system", "Desktop", "~/Desktop", "Desktop"),
                b("system", "Documents", "~/Documents"),
                b("system", "Downloads", "~/Downloads"),
            ]
        else:
            return [
                b("system", "Root", "/"),
                b("system", "Home", "~"),
                b("system", "Desktop", "~/Desktop", "Desktop"),
                b("system", "Documents", "~/Documents"),
                b("system", "Downloads", "~/Downloads"),
            ]

    def setFileTableState(self, state):

        self.state = state

def _load_drives():

    _dir_contents = []

    for drive in get_drives():
        ent = sync.DirEnt(drive, None, drive)
        ent._state = sync.FileState.SAME
        _dir_contents.append(ent)

    return _dir_contents

def _load_context(ctxt, directory):

    close = False
    if not ctxt.sameThread():
        ctxt = ctxt.clone()
        close = True

    try:
        abspath, relpath = ctxt.normPath(directory)
        result = sync._check(ctxt, relpath, abspath)

        _dir_contents = result.dirs + result.files
        return _dir_contents

    finally:
        if close:
            ctxt.close()

def _load_default(fs, directory):

    _dir_contents = []
    ts = time.time()
    for record in fs.scandir(directory):
        fullpath = fs.join(directory, record.name)

        try:
            # assuming listdir was used
            #try:
            #    record = fs.file_info(fullpath)
            #except FileNotFoundError as e:
            #    trace("not found: %s" % e)
            #    ent = sync.DirEnt(name, None, fullpath, sync.FileState.ERROR)
            #    _dir_contents.append(ent)
            #    continue
            #except OSError as e:
            #    trace(type(e), e, fullpath)
            #    ent = sync.DirEnt(name, None, fullpath, sync.FileState.ERROR)
            #    _dir_contents.append(ent)
            #    continue

            if not record.isDir:

                af = {
                    "version": record.version,
                    "size": record.size,
                    "mtime": record.mtime,
                    "permission": record.permission,
                }

                ent = sync.FileEnt(None, fullpath, None, None, af)
                ent._state = sync.FileState.SAME
                _dir_contents.append(ent)
            else:
                ent = sync.DirEnt(record.name, None, fullpath)
                ent._permission = record.permission
                ent._mtime = record.mtime
                ent._state = sync.FileState.SAME
                _dir_contents.append(ent)

        except FileNotFoundError:
            pass
    te = time.time()
    trace("load %.3f %s" % (te - ts, directory))
    return _dir_contents

class LoadThread(QThread):
    newContent = pyqtSignal(str, object)

    def __init__(self, fs, ctxt, directory, parent=None):
        super(LoadThread, self).__init__(parent)
        self.fs = fs
        self.ctxt = ctxt
        self.directory = directory

    def run(self):

        try:
            if self.directory == '':
                content = _load_drives()
            elif self.ctxt is not None:
                content = _load_context(self.ctxt, self.directory)
            else:
                content = _load_default(self.fs, self.directory)

            self.newContent.emit(self.directory, content)
        except Exception as e:
            logging.exception(str(e))

class LocationContext(QObject):

    # 3 signals to capture the start of a directory change,
    # then periodic updates as files become available
    # then a final signal to indicate the process is complete
    locationChanging = pyqtSignal()
    #locationUpdate = pyqtSignal(str)  # directory
    locationChanged = pyqtSignal(str, str)  # directory
    locationModified = pyqtSignal()

    #loadContextSuccess = pyqtSignal(str)  # directory
    #loadContextError = pyqtSignal(str, str)  # directory, reason
    #contextOpened = pyqtSignal(str)  # cfgdir

    def __init__(self, appCtxt):
        super(LocationContext, self).__init__()

        self.appCtxt = appCtxt
        self.fs = self.appCtxt.fs

        self._location = ""
        self._location_history = []
        self._location_pop_history = []
        self._dir_contents = []
        self._active_context = None

    def load(self, directory, target=None):

        # don't emit here when using threads to load
        # self.locationChanging.emit()

        # TODO: remove processEvents, once threaded loading is complete
        # QApplication.processEvents()
        # to test slow loading directories
        # QThread.msleep(2000)

        try:

            if directory == '':
                content = _load_drives()
                ctxt = None
            else:
                ctxt = self.appCtxt.getSyncContext(directory)

                if ctxt is not None:
                    content = _load_context(ctxt, directory)
                else:
                    content = _load_default(self.fs, directory)

            # useful for color testing
            # for state in sync.FileState.states():
            #    content.append(sync.DirEnt(state, state, state, state))

            self._active_context = ctxt
            self._dir_contents = content

            stats = self.fs.fsstats(directory)
            if stats:
                trace(stats)

        except Exception as e:
            trace("error changing directory")
            logging.exception(str(e))
            self._dir_contents = []
            self._active_context = None

        finally:
            self._location = directory
            self.locationChanged.emit(directory, target)

        return 0

    def threaded_load(self, directory):
        """
        TODO: requires a reopen of sqlite objects
        """
        self.locationChanging.emit()
        trace("on load", directory)

        if directory == '':
            ctxt = None
        else:
            ctxt = self.appCtxt.getSyncContext(directory)

        self._active_context = ctxt
        self._thread = LoadThread(self.fs, ctxt, directory)
        self._thread.newContent.connect(self.onNewContent)
        self._thread.finished.connect(self.onLoadFinished)
        self._thread.start()

    def onNewContent(self, directory, content):
        self._dir_contents = content
        self._location = directory
        self.locationChanged.emit(directory)

    def onLoadFinished(self):
        self._thread.wait()
        self._thread = None

    def _access(self, directory):
        if directory:
            if self.fs.islocal(directory):
                self.fs.file_info(directory)

    def reload(self):

        # reload the directory if it is no longer accessible
        # load the parent directory instead
        try:
            self._access(self._location)
            return self.load(self._location)
        except OSError:
            return self.pushParentDirectory()

    def removeSelection(self, rows):

        # TODO: fixme
        # filter data and remove display items in rows
        # each row is an instance of FileTableRowItem
        #
        idx = 0
        while idx < len(self._dir_contents):
            for ent in rows:
                if self._dir_contents[idx].samefile(ent):
                    self._dir_contents.pop(idx)
            else:
                idx += 1

        self.locationModified.emit()

        # below is the old behavior
        #try:
        #    self._access(self._location)
        #    return self.load(self._location)
        #except OSError:
        #    return self.pushParentDirectory()

    def pushDirectory(self, directory):

        self._access(directory)

        retval = self.load(directory)

        self._location_history.append((directory, None))
        self._location_pop_history = []

        return retval

    def pushChildDirectory(self, dirname):

        directory = self.fs.join(self._location, dirname)

        self._access(directory)

        # note buttons are enabled based on if there is history
        # but a failed load should not effect state
        self._location_history.append((directory, dirname))
        self._location_pop_history = []

        return self.load(directory)

    def pushParentDirectory(self):
        directory, name = self.fs.split(self._location)

        if self.fs.islocal(directory) and directory == self._location:
            directory = ""
            name = None

        self._access(directory)

        # note buttons are enabled based on if there is history
        # but a failed load should not effect state
        self._location_history.append((directory, name))
        self._location_pop_history = []

        return self.load(directory, name)

    def popDirectory(self):

        # return to the previous directory
        # if the history stack is empty, go to the parent directory

        if len(self._location_history) <= 1:
            directory, name = self.fs.split(self._location)

            if self.fs.islocal(directory) and directory == self._location:
                directory = ""
                name = None

            self._location_pop_history.append((self._location, None))
        else:

            # note buttons are enabled based on if there is history
            # but a failed load should not effect state
            directory, _ = self._location_history[-2]
            _, name = self._location_history[-1]

            self._location_pop_history.append(self._location_history.pop())

        self._access(directory)

        return self.load(directory, name)

    def unpopDirectory(self):

        if len(self._location_pop_history) < 1:
            raise Exception("no history")

        directory, name = self._location_pop_history.pop()
        self._access(directory)
        self._location_history.append((directory, name))
        return self.load(directory)

    def hasBackHistory(self):
        return len(self._location_history) > 1

    def hasForwardHistory(self):
        return len(self._location_pop_history) > 0

    def hasActiveContext(self):
        return self._active_context is not None

    def activeContext(self):
        return self._active_context

    def contents(self):
        # todo: deprecate this method
        # will make it easier than trying to have the table
        # model update the context
        return self._dir_contents

    def currentLocation(self):
        return self._location

    def renameEntry(self, ent, name):

        if isinstance(ent, sync.DirEnt):
            local_path = ent.local_base
            remote_path = ent.remote_base
        else:
            local_path = ent.local_path
            remote_path = ent.remote_path

        if local_path:
            fpath, fname = self.fs.split(local_path)
            new_local_path = self.fs.join(fpath, name)
        else:
            new_local_path = local_path

        if local_path == new_local_path:
            return None

        self.fs.rename(local_path, new_local_path)

        if remote_path:
            fpath, fname = posixpath.split(remote_path)
            new_remote_path = posixpath.join(fpath, name)
        else:
            new_remote_path = remote_path

        if isinstance(ent, sync.DirEnt):
            new_ent = sync.DirEnt(name, new_remote_path, new_local_path)

        elif not self.hasActiveContext():
            new_ent = sync.FileEnt(None, new_local_path, None, None, af)
            new_ent._state = sync.FileState.SAME

        else:
            new_ent = sync._check_file(
                self.activeContext(), remote_path, local_path)

        return new_ent

    # -----------------------------------------

    def getIcon(self, kind):
        return self.appCtxt.getIcon(kind)

    def getFileStateIcon(self, state):
        return self.appCtxt.getFileStateIcon(state)

    def getFileIcon(self, path):
        return self.appCtxt.getFileIcon(path)

    def clearContext(self):

        self._dir_contents = []
        self.locationChanged.emit(self.currentLocation(), None)

class AppContext(QObject):

    def __init__(self, cfg):
        super(AppContext, self).__init__()

        self.cfg = cfg
        self.fs = FileSystem()

        self.fs.open("mem://test/file.txt", "wb").close()
        self.fs.open("mem://test/subfolder/file.txt", "wb").close()

        self.initIcons(cfg.iconSize)

        self._icon_provider = QFileIconProvider()
        self._icon_ext = {}

        self._syncContext = {}

        self._compare_left_entry = None

    def _isSubPath(self, dir_path, file_path):
        return os.path.abspath(file_path).startswith(os.path.abspath(dir_path) + os.sep)

    def getSyncContext(self, directory):
        if not self.fs.islocal(directory):
            return None
        for local_base, ctxt in self._syncContext.items():
            if self._isSubPath(local_base, directory):
                return ctxt
        else:
            return self._get_context(directory)
        return None

    def _get_context(self, directory):

        # this duplicates the logic from get_ctxt
        try:
            userdata = sync.get_cfg(directory)

        except sync.SyncException as e:
            return None

        try:
            db_path = self.fs.join(
                userdata['local_base'], ".yue", "database.sqlite")

            db = sync.db_connect("sqlite:///" + db_path)

            # TODO: emit connection details
            trace(userdata['hostname'])
            client = sync.connect(userdata['hostname'],
                userdata['username'], userdata['password'])

            storageDao = sync.LocalStorageDao(db, db.tables)

            ctxt = sync.SyncContext(client, storageDao, self.fs,
                userdata['root'], userdata['remote_base'], userdata['local_base'])

            # replace the get password implementation
            ctxt.getPassword = PasswordDialog.getPasswordKind

            ctxt.current_local_base = userdata['current_local_base']
            ctxt.current_remote_base = userdata['current_remote_base']
            ctxt.hostname = userdata['hostname']
            ctxt.username = userdata['username']
            ctxt.showHiddenNames = True

        except sync.SyncException as e:
            #self.loadContextError.emit(directory, str(e))
            trace("ld ctxt error", str(e))
            return None

        except Exception as e:
            #self.loadContextError.emit(directory, str(e))
            trace("ld ctxt exception",str(e))
            return None

        else:

            local_base = userdata['local_base']
            self._syncContext[local_base] = ctxt
            # self.contextOpened.emit(local_base)

            return ctxt

    def getIcon(self, kind):
        """
        https://doc.qt.io/qt-5/qfileiconprovider.html

        """
        #if kind in self._icon_ext:
        #    return self._icon_ext[kind]

        if isinstance(kind, str):
            icon = QIcon.fromTheme(kind)
            if icon.isNull():
                raise Exception("invalid icon: %s" % kind)
        else:
            icon = self._icon_provider.icon(kind)

        image = icon.pixmap(QSize(64, 64)).toImage()
        #self._icon_ext[kind] = image
        return image

    def getImage(self, path):

        if path in self._icon_ext:
            return self._icon_ext[path]

        image = QImage(path)
        self._icon_ext[path] = image
        return image

    def getFileStateIcon(self, state):
        state = state.split(":")[0]
        image = self._getFileStateIcon(state)
        if image is not None and image.isNull():
            trace("error loading image for ", state)
        return image

    def _getFileStateIcon(self, state):

        if state == sync.FileState.SAME:
            # return self.getImage(":img/fs_same.png")
            return None

        elif state == sync.FileState.IGNORE:
            return self.getImage(":img/fs_ignore.png")

        elif state == sync.FileState.PUSH:
            return self.getImage(":/img/fs_push.png")

        elif state == sync.FileState.PULL:
            return self.getImage(":/img/fs_pull.png")

        elif state == sync.FileState.CONFLICT_MODIFIED:
            return self.getImage(":/img/fs_conflict.png")

        elif state == sync.FileState.CONFLICT_CREATED:
            return self.getImage(":/img/fs_conflict.png")

        elif state == sync.FileState.CONFLICT_VERSION:
            return self.getImage(":/img/fs_conflict.png")

        elif state == sync.FileState.CONFLICT_TYPE:
            return self.getImage(":/img/fs_conflict.png")

        elif state == sync.FileState.DELETE_BOTH:
            return self.getImage(":/img/fs_delete.png")

        elif state == sync.FileState.DELETE_REMOTE:
            return self.getImage(":/img/fs_delete.png")

        elif state == sync.FileState.DELETE_LOCAL:
            return self.getImage(":/img/fs_delete_remote.png")

        # state == sync.FileState.ERROR:
        return self.getImage(":/img/fs_error.png")

    def getFileIcon(self, path):

        _, ext = self.fs.splitext(path)
        if ext and ext in self._icon_ext:
            return self._icon_ext[ext]

        info = QFileInfo(path)
        icon = self._icon_provider.icon(info)
        image = icon.pixmap(QSize(32, 32)).toImage()
        self._icon_ext[ext] = image
        return image

    def compareSetLeft(self, ent):
        self._compare_left_entry = ent

    def compareLeftSelected(self):
        return self._compare_left_entry is not None

    def compareTo(self, pwd, ent):

        action = self.cfg.diff_action.get('action')
        executeDiffAction(action, pwd, self._compare_left_entry, ent)
        self._compare_left_entry = None

    def initIcons(self, size):

        icon = QFileIconProvider().icon(QFileIconProvider.Folder)
        img = icon.pixmap(QSize(size, size)).toImage()
        self._icon_folder = scale_image(size, img, True)

        icon = QFileIconProvider().icon(QFileIconProvider.File)
        img = icon.pixmap(QSize(size, size)).toImage()
        self._icon_file = scale_image(size, img, True)

class OverlayText(QWidget):

    def __init__(self, text, parent = None):
        super(OverlayText, self).__init__(parent)

        palette = QPalette(self.palette())
        palette.setColor(palette.Background, Qt.transparent)
        self.setPalette(palette)

        self._text = text

    def setText(self, text):
        self._text = text

    def showEvent(self, event):
        self.resize(self.parent().size())

    def paintEvent(self, event):

        if self.size() != self.parent().size():
            self.resize(self.parent().size())

        painter = QPainter()
        painter.begin(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.parent().rect(), QBrush(QColor(255, 255, 255, 127)))

        painter.drawText(self.parent().rect(), Qt.AlignHCenter|Qt.AlignVCenter, self._text)

        painter.end()

class OverlaySpinner(QWidget):

    def __init__(self, parent = None):
        super(OverlaySpinner, self).__init__(parent)

        palette = QPalette(self.palette())
        palette.setColor(palette.Background, Qt.transparent)
        self.setPalette(palette)

        self.cos = [(30 * math.cos(2 * math.pi * i / 6.0) - 10) for i in range(6)]
        self.sin = [(30 * math.sin(2 * math.pi * i / 6.0) - 10) for i in range(6)]

        self.counter = 0

    def paintEvent(self, event):

        if self.size() != self.parent().size():
            self.resize(self.parent().size())

        painter = QPainter()

        painter.begin(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(event.rect(), QBrush(QColor(255, 255, 255, 127)))
        painter.setPen(QPen(Qt.NoPen))

        for i in range(6):
            if (self.counter // 5) % 6 == i:
                color = QColor(127, 127 + (self.counter % 5)*32, 127)
                painter.setBrush(QBrush(color))
            else:
                color = QColor(127, 127, 127)
                painter.setBrush(QBrush(color))
            x = int(self.width()/2 + self.cos[i])
            y = int(self.height()/2 + self.sin[i])
            painter.drawEllipse(x, y, 20, 20)

        painter.end()

    def showEvent(self, event):

        self.resize(self.parent().size())
        self.timer = self.startTimer(75)
        self.counter = 0

    def hideEvent(self, event):
        self.killTimer(self.timer)

    def timerEvent(self, event):

        self.counter += 1
        self.update()

class Pane(QWidget):

    def __init__(self, parent):
        super(Pane, self).__init__(parent)
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(0, 0, 0, 0)
        self._firstShow = True

    def addWidget(self, widget):
        self.vbox.addWidget(widget)

    def setVisible(self, b):
        super().setVisible(b)

        if b and self._firstShow:
            self.onFirstShow()
            self._firstShow = False

    def onFirstShow(self):
        pass

    def onEnter(self):
        pass

    def onExit(self):
        pass

class ImageView(QLabel):

    image_extensions = [".png", ".jpg", "jpeg", ".bmp"]
    movie_extensions = [".gif"]

    def __init__(self, parent=None):
        super(ImageView, self).__init__(parent)

        self.dialog = None

        self.image = None
        self.pixmap = None

        self.setFixedHeight(128)
        self.setHidden(True)

        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)

    def setPath(self, path):

        try:
            image = ImageView.loadPath(path)
            if image is not None:
                self.setImage(image)
                return
        except Exception as e:
            trace("failed to set image: %s" % e)
        self.setHidden(True)

    def setImage(self, image):

        if image is None:
            self.setHidden(True)
            return

        self.image = image

        self.pixmap = QPixmap.fromImage(scale_image(self.size(), image))

        super().setPixmap(self.pixmap)
        self.setHidden(False)

    @staticmethod
    def loadPath(path):

        if path is None:
            return None

        _, ext = os.path.splitext(path)

        if ext.lower() in ImageView.image_extensions:
            image = QImage(path)
            if not image.isNull():
                return image

        elif ext.lower() in ImageView.movie_extensions:
            frame = gif_extract_position(path)
            data = frame.tobytes("raw","RGBA")
            image = QImage(data, frame.size[0], frame.size[1], QImage.Format_RGBA8888)
            if not image.isNull():
                return image

        return None

class TabWidget(QTabWidget):
    def __init__(self, parent = None):
        super(TabWidget, self).__init__( parent)
        self.currentChanged.connect(self.onCurrentTabChanged)

        self.previousTab = None

    def onCurrentTabChanged(self,index):

        w = self.widget( index )

        if self.previousTab is not None:
            if hasattr(self.previousTab, 'onExit'):
                self.previousTab.onExit()

        if hasattr(w, 'onEnter'):
            w.onEnter();

        self.previousTab = w

class LineEdit(QLineEdit):
    def __init__(self, parent=None):
        super(LineEdit, self).__init__(parent)

    def keyPressEvent(self, event):

        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Home:
                self.setCursorPosition(0)
                event.accept()
                return

            if event.key() == Qt.Key_End:
                self.setCursorPosition(len(self.text()))
                event.accept()
                return

        return super().keyPressEvent(event)

class ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super(ClickableLabel, self).__init__(parent)

    def mouseReleaseEvent(self, event):
        self.clicked.emit()

class Calculator(QWidget):
    def __init__(self, parent=None):
        super(Calculator, self).__init__(parent)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 0, 16, 0)
        self.edit_text = LineEdit(self)
        self.lbl_result = QLabel(self)
        self.lbl_result.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_result.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.lbl_result.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_result.setFrameStyle(QFrame.Panel | QFrame.Sunken)

        self.edit_text.editingFinished.connect(self.evaluate)
        self.layout.addWidget(self.edit_text)
        self.layout.addWidget(self.lbl_result)

        self._initvars()

    def _initvars(self):

        self.globals = {"__builtins__":None}
        self.locals = {}
        for key in dir(math):
            if not key.startswith("_"):
                self.locals[key] = getattr(math,key);
        self.locals['ans'] = 0
        self.locals['abs'] = abs
        self.locals['ascii'] = ascii
        self.locals['bin'] = bin
        self.locals['bool'] = bool
        self.locals['chr'] = chr
        self.locals['complex'] = complex
        self.locals['divmod'] = divmod
        self.locals['float'] = float
        self.locals['hex'] = hex
        self.locals['int'] = int
        self.locals['max'] = max
        self.locals['min'] = min
        self.locals['oct'] = oct
        self.locals['ord'] = ord
        self.locals['pow'] = pow
        self.locals['round'] = round
        self.locals['str'] = str
        self.locals['sum'] = sum
        self.locals['fold'] = lambda initial,seq: sum(seq,initial)
        self.locals['sign'] = lambda x: 1 if x>=0 else -1
        self.locals['j'] = complex(0,1)
        #trace(' '.join(list(self.locals.keys())))

    def evaluate(self):

        text= self.edit_text.text().strip()
        if not text:
            return

        try:
            result = eval(text,self.globals,self.locals)
            self.lbl_result.setText(str(result))
            self.locals["ans"] = result
        except Exception as e:
            self.lbl_result.setText(str(e))

class Calendar(ClickableLabel):
    def __init__(self, parent=None):
        super(Calendar, self).__init__(parent)

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.setSingleShot(False)
        self.timer.timeout.connect(self.updateDate)
        self.timer.start()

        fm = QFontMetrics(self.font())

        if PYQT_V6:
            self._width = fm.maxWidth() * 14;
        else:
            self._width = fm.width("X") * 14

        self._size = QSize(self._width, -1)

    def sizeHint(self):
        return self._size

    def updateDate(self):
        date = datetime.now().strftime("%a %Y/%m/%d")
        self.setText(date)

    def setEnabled(self, enable):

        if enable:
            self.timer.start()
        else:
            self.timer.stop()

        super().setEnabled(enable)

class Clock(QWidget):
    """docstring for Clock"""
    def __init__(self, parent=None):
        super(Clock, self).__init__(parent)

        self.timer = QTimer(self)
        self.timer.setInterval(333)
        self.timer.setSingleShot(False)
        self.timer.timeout.connect(self.updateTime)
        self.timer.start()

        self.output1 = QLabel(self)
        self.output1.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.output1.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Maximum)
        self.output1.setTextInteractionFlags(Qt.TextSelectableByMouse)
        #self.output1.setFrameStyle(QFrame.Panel | QFrame.Raised)

        self.output2 = QLabel(self)
        self.output2.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.output2.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Maximum)
        self.output2.setTextInteractionFlags(Qt.TextSelectableByMouse)
        #self.output2.setFrameStyle(QFrame.Panel | QFrame.Raised)

        self.hbox = QHBoxLayout(self)
        self.hbox.addWidget(self.output1)
        self.hbox.addWidget(self.output2)
        self.hbox.setContentsMargins(16, 0, 16, 0)

        fm = QFontMetrics(self.font())
        self._width = fm.width("X") * 10
        margin = self.hbox.contentsMargins().left() + \
                 self.hbox.contentsMargins().right()
        self._size = QSize(margin + self._width * 2, -1)

    def sizeHint(self):
        return self._size

    def updateTime(self):

        self.output1.setText(datetime.now().strftime("%H:%M:%S"))
        self.output2.setText(datetime.utcnow().strftime("%H:%M:%S"))

    def setEnabled(self, enable):

        if enable:
            self.timer.start()
        else:
            self.timer.stop()

        super().setEnabled(enable)

class GlobStringSearchRule(ColumnSearchRule):

    def check(self, elem, ignoreCase=True):
        v1 = self.type_(case_(self.value, ignoreCase))
        v2 = self.type_(case_(elem[self.column.name], ignoreCase))
        return fnmatch.fnmatch(v2, v1)

    def __repr__(self):
        return "<%s matches `%s`>" % (self.fmtval(self.value), self.column)

    def sql(self):
        return self.column.ilike("%%%s%%" % self.value)

class InvertedGlobStringSearchRule(ColumnSearchRule):

    def check(self, elem, ignoreCase=True):
        v1 = self.type_(case_(self.value, ignoreCase))
        v2 = self.type_(case_(elem[self.column.name], ignoreCase))
        trace(self.column, v2, v1)
        return not fnmatch.fnmatch(v2, v1)

    def __repr__(self):
        return "<%s does not match `%s`>" % (self.fmtval(self.value), self.column)

    def sql(self):
        return self.column.notilike("%%%s%%" % self.value)

class FilterGrammar(SearchGrammar):

    META_DIRECTORY = "dir"

    def __init__(self, dtn=None):
        super(FilterGrammar, self).__init__(dtn)

        self.colmap = {
            "filename": FileTableRowItem.COL_NAME,
            "state": FileTableRowItem.COL_STATE,
            "timestamp": FileTableRowItem.COL_L_MTIME,
            "size": FileTableRowItem.COL_L_SIZE,
            "public": FileTableRowItem.COL_PUBLIC,
            "encryption": FileTableRowItem.COL_ENCRYPTION,
            "type": FileTableRowItem.COL_TYPE,
        }

    def translateColumn(self, colid):

        return Column(self.colmap[colid])

    def compile_operators(self):

        self.all_text = 'all_text'
        # sigil is used to define the oldstyle syntax marker
        # it should not appear in tok_special
        self.sigil = '.'

        # tokens control how the grammar is parsed.
        self.tok_whitespace = " \t"  # token separators
        # all meaningful non-text chars
        self.tok_operators = '~!=<>'
        self.tok_flow = "|&"
        self.tok_special = self.tok_operators + self.tok_flow
        self.tok_negate = "!"
        self.tok_nest_begin = '('
        self.tok_nest_end = ')'
        self.tok_quote = "\""
        self.tok_escape = "\\"

        self.oldstyle_operator_default = GlobStringSearchRule

        # does not require left token
        self.operators = {
            "=": PartialStringSearchRule,
            "!=": InvertedPartialStringSearchRule,
        }

        self.operators_invert = {
            InvertedGlobStringSearchRule: GlobStringSearchRule,
            InvertedPartialStringSearchRule: PartialStringSearchRule,
        }

        # require left/right token
        self.special = {
            "<": LessThanSearchRule,
            ">": GreaterThanSearchRule,
            "<=": LessThanEqualSearchRule,
            ">=": GreaterThanEqualSearchRule,
        }

        self.special_invert = {
            GreaterThanSearchRule: LessThanSearchRule,
            LessThanSearchRule: GreaterThanSearchRule,
            GreaterThanEqualSearchRule: LessThanEqualSearchRule,
            LessThanEqualSearchRule: GreaterThanEqualSearchRule,
        }

        # meta options can be used to control the query results
        # by default, limit could be used to limit the number of results

        self.meta_columns = set([
            FilterGrammar.META_DIRECTORY,
            FilterGrammar.META_LIMIT,
            FilterGrammar.META_OFFSET,
            FilterGrammar.META_DEBUG
        ])
        self.meta_options = dict()

        self.old_style_operators = self.operators.copy()
        self.old_style_operators.update(self.special)

        self.old_style_operators_invert = self.operators_invert.copy()
        self.old_style_operators_invert.update(self.special_invert)

        self.operators_flow = {
            "&&": AndSearchRule,
            "||": OrSearchRule,
            "!": NotSearchRule,
        }

        self.operators_flow_invert = {v: k for k, v in self.operators_flow.items()}

        self.operators_flow_join = AndSearchRule

    def buildRule(self, colid, rule, value):

        if colid == self.all_text:
            if rule in [GlobStringSearchRule, InvertedGlobStringSearchRule]:
                if '*' not in value and '?' not in value:
                    value = "*%s*" % value.strip()
            colid = 'filename'
        col = self.translateColumn(colid)

        if colid == 'size':
            return self.buildSizeRule(col, rule, value)
        elif colid == "timestamp":
            return self.buildDateRule(col, rule, value)

        return rule(col, value, type_=str)

    def buildSizeRule(self, col, rule, value):

        # remove whitespace and apply a multiplier
        # parse suffix: b, kb, mb, gb

        value = value.replace(" ", "").lower()

        m = 1
        if value.endswith('b'):
            value = value[:-1]
        elif value.endswith('k'):
            m = 1024
            value = value[:-1]
        elif value.endswith('m'):
            m = 1024 * 1024
            value = value[:-1]
        elif value.endswith('g'):
            m = 1024 * 1024 * 1024
            value = value[:-1]
        elif value.endswith('kb'):
            m = 1024
            value = value[:-2]
        elif value.endswith('mb'):
            m = 1024 * 1024
            value = value[:-2]
        elif value.endswith('gb'):
            m = 1024 * 1024 * 1024
            value = value[:-2]
        value = int(value) * m

        return rule(col, value, type_=int)

class FileContentSortProxyModel(SortProxyModel):
    """
    A sort proxy model that is aware of the file content

    directories are allways sorted before files

    Note: the proxy model could be extended to support filtering
        remote/local/synced files
    """

    def __init__(self, *args):
        super(FileContentSortProxyModel, self).__init__(*args)

        self._rule = None
        self._dir = False

        self._show_hidden = False
        self._show_blacklist = False

        self.grammar = FilterGrammar()

    def lessThan(self, indexL, indexR):

        order = self.sortOrder()
        left = self._key(indexL, order)
        right = self._key(indexR, order)
        return left < right

    def _key(self, index, order):
        val = index.data(RowSortValueRole)
        if not isinstance(val, (int, float, str)):
            val = None
        row = index.data(RowValueRole)
        ent = row[0]
        dir = isinstance(ent, sync.DirEnt)

        if order == Qt.AscendingOrder:
            dir = not dir

        return (dir, val, ent.name())

    def setFilterGlobPattern(self, pattern):

        # TODO: support multiple patterns
        # {pattern: str, mode: int}
        # mode: {glob, state, size, date. permission, etc}
        # pattern: raw text
        # direction: <= < = > =>

        try:
            self._rule = self.grammar.ruleFromString(pattern)
            self._dir = 'dir' in self.grammar.meta_options
            trace("compiled rule:", self._rule, "match dirname:", self._dir)
        except Exception as e:
            self._rule = None
            self._dir = False
            trace("error compiling rule", type(e), e)

        self.invalidateFilter()

    def setShowHiddenFiles(self, hidden):
        self._show_hidden = hidden
        self.invalidateFilter()

    def setShowBlacklistFiles(self, hidden):
        self._show_blacklist = hidden
        self.invalidateFilter()

    def filterAcceptsRow(self, row, parent):

        item = self.parent().baseModel().tabledata[row]

        name = item[FileTableRowItem.COL_NAME]
        ent = item[FileTableRowItem.COL_ENT]
        state = item[FileTableRowItem.COL_STATE]

        if name.startswith("."):
            if not self._show_hidden:
                return False
        # D:\Storage\public\code\python\ekanscrypt
        if state == sync.FileState.IGNORE:
            if not self._show_blacklist:
                return False

        if not self._rule:
            return True

        if not self._dir and isinstance(ent, sync.DirEnt):
            return True

        return self._rule.check(item)

class FileContextMenu(QMenu):

    createDirectory = pyqtSignal()
    createEmptyFile = pyqtSignal()
    rename = pyqtSignal()
    copyUrls = pyqtSignal(list, object)

    showHiddenFiles = pyqtSignal(bool)
    showBlacklistFiles = pyqtSignal(bool)

    def __init__(self, ctxt, cfg, selection, parent=None):
        super(FileContextMenu, self).__init__(parent)

        self.ctxt = ctxt
        self.cfg = cfg

        isLocal = self.ctxt.fs.islocal(self.ctxt.currentLocation())

        ents = [row[0] for row in selection]

        menu = self.addMenu("New")
        menu.addAction("Directory", self._action_new_directory)
        menu.addAction("Empty File", self._action_new_file)

        if isLocal and len(selection) == 1:
            ent = selection[0][0]
            menu = self.addMenu("Open")
            act = menu.addAction("Native", lambda: self._action_open_native(ent))

            if self.cfg.open_actions:
                menu.addSeparator()

            for item in self.cfg.open_actions:
                act = item['action']
                text = item['text']
                g = lambda ents=ents, act=act: self._action_open_action(ents, act)

                if 'icon' in item:
                    icon = QIcon.fromTheme(item['icon'])
                    act = menu.addAction(icon, text, g)
                else:
                    act = menu.addAction(text, g)

        if isLocal and self.ctxt.hasActiveContext():

            menu = self.addMenu("Sync")
            act = menu.addAction("Sync", lambda: self._action_sync(ents))
            act = menu.addAction("Push", lambda: self._action_push(ents))
            act = menu.addAction("Pull", lambda: self._action_pull(ents))

        if len(selection) == 1:
            ico = self.style().standardIcon(QStyle.SP_FileDialogInfoView)
            act = self.addAction(ico, "Properties", lambda: self._action_info(ents[0]))

        self.addSeparator()

        if isLocal and self.ctxt.hasActiveContext():

            if self.cfg.showBlacklistFiles:
                self.addAction("Hide Blacklist Files", self._action_toggle_show_blacklist)
            else:
                self.addAction("Show Blacklist Files", self._action_toggle_show_blacklist)

        if self.cfg.showHiddenFiles:
            self.addAction("Hide Hidden Files", self._action_toggle_show_hidden)
        else:
            self.addAction("Show Hidden Files", self._action_toggle_show_hidden)

        self.addSeparator()

        ico = self.style().standardIcon(QStyle.SP_BrowserReload)
        act = self.addAction(ico, "Refresh", lambda: self.ctxt.reload())

        self.addAction("Rename", self._action_rename)

        ico = QIcon.fromTheme("edit-copy")
        act = self.addAction(ico, "Copy", lambda: self._action_copy(ents))
        ico = QIcon.fromTheme("edit-cut")
        act = self.addAction(ico, "Cut", lambda: self._action_cut(ents))

        clipboard = QGuiApplication.clipboard();
        mimeData = clipboard.mimeData()
        if mimeData.hasUrls():
            text = "Paste (%d)" % len(mimeData.urls())
        else:
            text = "Paste (0)"

        ico = QIcon.fromTheme("edit-paste")
        act = self.addAction(ico, text, self._action_paste)
        act.setEnabled(mimeData.hasUrls())

        #if self.ctxt.hasActiveContext():
        #    menu = self.addMenu("Delete")
        #    act = menu.addAction("Delete Local")
        #    act = menu.addAction("Delete Remote")
        #else:
        #    act = self.addAction("Delete")

        ico = self.style().standardIcon(QStyle.SP_TrashIcon)
        act = self.addAction(ico, "Delete", lambda: self._action_remove(ents))

        self.addSeparator()

        act = self.addAction("Copy File Name", lambda: self._action_copy_name(ents[0]))
        act = self.addAction("Copy File Path", lambda: self._action_copy_path(ents[0]))

        self.addSeparator()


        diff_action = self.cfg.diff_action.get('action', None)
        if isLocal and diff_action:
            act = self.addAction("Compare: Set Left File", lambda: self._action_compare_set_left(ents[0]))

            icon_name = self.cfg.diff_action.get('icon', None)
            if icon_name:
                ico = QIcon.fromTheme(icon_name)
                act = self.addAction(ico, "Compare Files", lambda: self._action_compare_files(ents[0]))
            else:
                act = self.addAction("Compare Files", lambda: self._action_compare_files(ents[0]))
            act.setEnabled(self.ctxt.appCtxt.compareLeftSelected())


        self.addSeparator()

        if isLocal:
            act = self.addAction("Open Current Directory",
                lambda: openNative(self.ctxt.currentLocation()))

        if isLocal:
            groups = {}
            for item in self.cfg.menu_actions:
                act = item['action']
                text = item['text']
                mode = item.get('mode')
                grp = item.get("group", None)
                #
                if mode == 'zero' and len(selection) != 0:
                    continue

                if mode == 'single' and len(selection) != 1:
                    continue

                if mode == 'multiple' and len(selection) == 0:
                    continue

                tgt = self
                if grp is not None:
                    if grp not in groups:
                        groups[grp] = self.addMenu(grp)
                    tgt = groups[grp]

                g = lambda ents=ents, act=act: self._action_menu_action(ents, act)

                if 'icon' in item:
                    icon = QIcon.fromTheme(item['icon'])
                    act = tgt.addAction(icon, text, g)
                else:
                    act = tgt.addAction(text, g)

    def _action_template(self):
        pass

    def _action_open_native(self, ent):

        if isinstance(ent, sync.DirEnt):
            openNative(ent.local_base)
        else:
            openNative(ent.local_path)

    def _action_sync_impl(self, ents, push, pull):

        # convert mix of FileEnt and DirEnt into just DirEnt

        paths = []
        for ent in ents:
            if isinstance(ent, sync.DirEnt):
                paths.append(ent)
            else:
                paths.append(sync.DirEnt(None, ent.remote_path, ent.local_path))

        optdialog = SyncOptionsDialog(self)
        if optdialog.exec_() == QDialog.Accepted:
            opts = optdialog.options()
            dialog = SyncProgressDialog()

            thread = SyncProgressThread(self.ctxt,
                paths, push, pull, opts['force'],  opts['recursive'],
                dialog)

            dialog.setThread(thread)
            dialog.exec_()
            self.ctxt.reload()

    def _action_sync(self, ents):
        self._action_sync_impl(ents, True, True)

    def _action_push(self, ents):
        self._action_sync_impl(ents, True, False)

    def _action_pull(self, ents):
        self._action_sync_impl(ents, False, True)

    def _action_info(self, ent):

        dialog = FileEntryInfoDialog(self)
        hostname = None
        if self.ctxt.hasActiveContext():
            hostname = self.ctxt.activeContext().hostname
        dialog.setEntry(ent, hostname)
        dialog.exec_()

    def _action_open_action(self, ents, act):

        self._action_exec(ents, act)

    def _action_menu_action(self, ents, act):

        # todo: should be blocking
        # todo: should auto refresh
        self._action_exec(ents, act)

    def _action_exec(self, ents, act):

        pwd = self.ctxt.currentLocation()

        executeAction(act, ents, pwd)

    def _action_new_directory(self):
        self.createDirectory.emit()

    def _action_new_file(self):

        self.createEmptyFile.emit()

    def _action_rename(self):

        self.rename.emit()

    def _action_compare_set_left(self, ent):
        self.ctxt.appCtxt.compareSetLeft(ent)

    def _action_compare_files(self, ent):

        self.ctxt.appCtxt.compareTo(self.ctxt.currentLocation(), ent)

    def _action_toggle_show_hidden(self):

        self.cfg.showHiddenFiles = not self.cfg.showHiddenFiles
        self.showHiddenFiles.emit(self.cfg.showHiddenFiles)

    def _action_toggle_show_blacklist(self):

        self.cfg.showBlacklistFiles = not self.cfg.showBlacklistFiles
        self.showBlacklistFiles.emit(self.cfg.showBlacklistFiles)

    def _action_copy_name(self, ent):

        mimeData = QMimeData()
        mimeData.setText(ent.name())

        clipboard = QGuiApplication.clipboard();
        clipboard.setMimeData(mimeData)

    def _action_copy_path(self, ent):

        if isinstance(ent, sync.DirEnt):
            path = ent.local_base
        else:
            path = ent.local_path

        mimeData = QMimeData()
        mimeData.setText(path)

        clipboard = QGuiApplication.clipboard();
        clipboard.setMimeData(mimeData)

    def _action_copy(self, ents):

        urls = []
        for ent in ents:
            if isinstance(ent, sync.DirEnt):
                path = ent.local_base
            else:
                path = ent.local_path
            if path:
                urls.append(QUrl(self.ctxt.fs.url(path)))

        trace(urls)
        if urls:

            mimeData = QMimeData()

            # windows explorer hint for copy
            mimeData.setData("Preferred DropEffect", b'\x05\x00\x00\x00')
            mimeData.setUrls(urls)

            clipboard = QGuiApplication.clipboard();
            clipboard.setMimeData(mimeData)

    def _action_cut(self, ents):

        urls = []
        for ent in ents:
            if isinstance(ent, sync.DirEnt):
                path = ent.local_base
            else:
                path = ent.local_path
            if path:
                urls.append(QUrl(self.ctxt.fs.url(path)))

        if urls:

            mimeData = QMimeData()

            # windows explorer hint for move (cut)
            mimeData.setData("Preferred DropEffect", b'\x02\x00\x00\x00')
            mimeData.setUrls(urls)

            clipboard = QGuiApplication.clipboard();
            clipboard.setMimeData(mimeData)

    def _action_paste(self):

        clipboard = QGuiApplication.clipboard();
        mimeData = clipboard.mimeData()

        # trace(mimeData.formats())

        data = mimeData.data("Preferred DropEffect")

        dropAction = Qt.IgnoreAction
        if data == b'\x02\x00\x00\x00':
            dropAction = Qt.MoveAction
        elif data == b'\x05\x00\x00\x00':
            dropAction = Qt.CopyAction
        else:
            trace("unknown action:", data)
            return

        if mimeData.hasUrls():
            urls = []
            for url in mimeData.urls():
                if url.isLocalFile():
                    urls.append(url.toLocalFile())
                else:
                    urls.append(url.url())

            self.copyUrls.emit(urls, dropAction)

    def _action_remove(self, ents):

        urls = []
        for ent in ents:
            if isinstance(ent, sync.DirEnt):
                path = ent.local_base
            else:
                path = ent.local_path

            if path:
                urls.append(path)

        if urls:
            dialog = SyncProgressDialog()
            thread = RemoveProgressThread(self.ctxt.fs, urls, self)
            dialog.setThread(thread)
            dialog.exec_()
            # TODO: fixme
            #self.ctxt.reload()
            self.ctxt.removeSelection(ents)

class FileTableRowItem(object):

    COL_ENT        = 0
    COL_STATE      = 1
    COL_ICON       = 2
    COL_NAME       = 3
    COL_L_SIZE     = 4
    COL_R_SIZE     = 5
    COL_L_PERM     = 6
    COL_R_PERM     = 7
    COL_PUBLIC     = 8
    COL_ENCRYPTION = 9
    COL_L_MTIME    = 10
    COL_R_MTIME    = 11
    COL_TYPE       = 12
    COL_STATE      = 13
    COL_ICON2      = 14

    COL_COUNT      = 14  # number of columns

    def __init__(self, data=None):
        super(FileTableRowItem, self).__init__()

        if data:
            self._data = data
        else:
            self._data = [None] * COL_COUNT

    def __getitem__(self, index):
        return self._data[index]

    def __setitem__(self, index, value):
        self._data[index] = value

    # TODO: remove dependency on ctxt
    @staticmethod
    def fromEntry(ctxt, ent):

        if isinstance(ent, sync.FileEnt):

            df = {'size': 0, "permission": 0, "mtime": 0, "version": 0,
                  "public": "", "encryption": ""}

            lf = ent.lf or df
            rf = ent.rf or df
            af = ent.af or df

            if ctxt.fs.islocal(ent.local_path):
                icon = ctxt.getFileIcon(ent.local_path)
            else:
                icon = ctxt.getIcon(QFileIconProvider.File)
            item = [
                ent,                                      # 0
                ctxt.getFileStateIcon(ent.state()),       # 1
                icon,         # 2
                ent.name(),                               # 3
                af['size'],                               # 4
                rf['size'],                               # 5
                af['permission'],                         # 6
                rf['permission'],                         # 7
                rf['public'],                             # 8
                rf['encryption'],                         # 9
                af['mtime'],                              # 10
                rf['mtime'],                              # 11
                ctxt.fs.getFileType(ent.name()),          # 12
                ent.state(),                              # 13
                ctxt.appCtxt._icon_file                   # 14
            ]

        elif isinstance(ent, sync.DirEnt):

            item = [
                ent,                                       # 0
                ctxt.getFileStateIcon(ent.state()),        # 1
                ctxt.getIcon(QFileIconProvider.Folder),    # 2
                ent.name(),                                # 3
                0,                                         # 4
                0,                                         # 5
                ent._permission,                           # 6
                0,                                         # 7
                "",                                        # 8
                "",                                        # 9
                ent._mtime,                                # 10
                0,                                         # 11
                "",                                        # 12
                ent.state(),                               # 13
                ctxt.appCtxt._icon_folder                  # 14
            ]

        return FileTableRowItem(item)

class FileTableView(TableView):

    loadLocation = pyqtSignal(str, object)  # async load, mode, dir
    locationChanged = pyqtSignal(str, int, int)  # dir, dcount, fcount

    triggerSave = pyqtSignal()
    triggerRestore = pyqtSignal()

    createDirectory = pyqtSignal(QModelIndex, object)
    createEmptyFile = pyqtSignal(QModelIndex, object)
    renameDirectory = pyqtSignal(QModelIndex, object)
    renameFile = pyqtSignal(QModelIndex, object)
    openEntry = pyqtSignal(object)

    copyEntries = pyqtSignal(list)  # deprecate?
    moveEntries = pyqtSignal(list)
    pasteEntries = pyqtSignal()
    copyUrls = pyqtSignal(list, object)

    loadDetails = pyqtSignal(QObject, QObject)  # table, base model

    def __init__(self, ctxt, cfg, parent=None):
        super(FileTableView, self).__init__(parent)

        self.ctxt = ctxt
        self.cfg = cfg

        fm = QFontMetrics(self.font())
        v = self.verticalHeader()
        v.setSectionResizeMode(QHeaderView.Fixed)
        v.setDefaultSectionSize(int(fm.height() * self.cfg.rowScale))

        self.setWordWrap(False)

        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setVerticalHeaderVisible(False)
        self.setSortingEnabled(True)
        self.setColumnsMovable(True)
        self.setColumnHeaderClickable(True)
        # double click to open is also firing edit selected
        # self.setEditTriggers(QAbstractItemView.SelectedClicked)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)

        model = self.baseModel()

        idx = model.addColumn(2, "icon", editable=False)
        self.setDelegate(idx, ImageDelegate(self))
        model.getColumn(idx).setDisplayName("")
        model.getColumn(idx).setSortTransform(lambda data, row: self.ctxt.fs.splitext(data[row][3])[-1])

        idx = model.addColumn(1, "state", editable=False)
        self.setDelegate(idx, ImageDelegate(self))
        model.getColumn(idx).setSortTransform(lambda data, row: data[row][-2])

        idx = model.addColumn(3, "filename", editable=True)
        delegate = EditItemDelegate(self)
        delegate.editRow.connect(self.editRow)
        self.setDelegate(idx, delegate)

        model.getColumn(idx).setShortName("Name")
        model.getColumn(idx).setDisplayName("File Name")
        model.getColumn(idx).setDecorationKey(None)

        idx = model.addTransformColumn(4, "local_size", self._fmt_size)
        model.getColumn(idx).setDefaultTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        model.getColumn(idx).setSortTransform(lambda data, row: data[row][4])

        idx = model.addTransformColumn(5, "remote_size", self._fmt_size)
        model.getColumn(idx).setDefaultTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        model.getColumn(idx).setSortTransform(lambda data, row: data[row][5])

        idx = model.addTransformColumn(6, "local_permission", self._fmt_octal)
        self.setDelegate(idx, MonospaceDelegate(self))
        model.getColumn(idx).setDefaultTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        model.getColumn(idx).setSortTransform(lambda data, row: data[row][6])
        model.getColumn(idx).setShortName("permission")

        idx = model.addTransformColumn(7, "remote_permission", self._fmt_octal)
        self.setDelegate(idx, MonospaceDelegate(self))
        model.getColumn(idx).setDefaultTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        model.getColumn(idx).setSortTransform(lambda data, row: data[row][7])
        model.getColumn(idx).setShortName("r_perm")

        idx = model.addTransformColumn(10, "local_mtime", self._fmt_datetime)
        self.setDelegate(idx, MonospaceDelegate(self))
        model.getColumn(idx).setDefaultTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        model.getColumn(idx).setSortTransform(lambda data, row: data[row][10])

        idx = model.addTransformColumn(11, "remote_mtime", self._fmt_datetime)
        self.setDelegate(idx, MonospaceDelegate(self))
        model.getColumn(idx).setDefaultTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        model.getColumn(idx).setSortTransform(lambda data, row: data[row][11])

        idx = model.addTransformColumn(0, "remote_path", self._fmt_remote_path)

        idx = model.addColumn(8, "remote_public", editable=False)
        model.getColumn(idx).setDefaultTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

        idx = model.addColumn(9, "remote_encryption", editable=False)
        model.getColumn(idx).setDefaultTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

        idx = model.addColumn(12, "type", editable=False)
        model.getColumn(idx).setDefaultTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

        model.addForegroundRule("fg1", self._foregroundRule)
        model.addBackgroundRule("fg2", self._backgroundRule)

        self.model().setShowHiddenFiles(self.cfg.showHiddenFiles)
        self.model().setShowBlacklistFiles(self.cfg.showBlacklistFiles)

        self.xcut_copy = QShortcut(QKeySequence(QKeySequence.Copy), self)
        self.xcut_copy.setContext(Qt.WidgetShortcut)
        self.xcut_copy.activated.connect(lambda: self.copyEntries.emit(self.getSelection()))

        self.xcut_cut = QShortcut(QKeySequence(QKeySequence.Cut), self)
        self.xcut_cut.setContext(Qt.WidgetShortcut)
        self.xcut_cut.activated.connect(lambda: self.moveEntries.emit(self.getSelection()))

        self.xcut_paste = QShortcut(QKeySequence(QKeySequence.Paste), self)
        self.xcut_paste.setContext(Qt.WidgetShortcut)
        self.xcut_paste.activated.connect(self.pasteEntries)

        self.xcut_refresh = QShortcut(QKeySequence(QKeySequence.Refresh), self)
        self.xcut_refresh.setContext(Qt.WidgetShortcut)
        self.xcut_refresh.activated.connect(lambda: self.loadLocation.emit("reload", None))

        self.xcut_delete = QShortcut(QKeySequence(QKeySequence.Delete), self)
        self.xcut_delete.setContext(Qt.WidgetShortcut)
        self.xcut_delete.activated.connect(self.onRemoveSelection)

        self.selectionChangedEvent.connect(self.onSelectionChanged)

        self.createDirectory.connect(self.onCreateDirectory)
        self.createEmptyFile.connect(self.onCreateEmptyFile)
        self.renameDirectory.connect(self.onRenameDirectory)
        self.renameFile.connect(self.onRenameFile)

        self._detailed_view = False

        self._wheel_accumulator = QPoint(0, 0)
        self._wheel_counter = 0

    def getSortProxyModel(self):
        """
        returns a new instance of SortProxyModel, used for
        sorting the baseModel()
        """
        model = FileContentSortProxyModel(self)
        model.setSourceModel(self.baseModel())
        return model

    def setVisible(self, b):
        super().setVisible(b)

        idx = self.baseModel().getColumnIndexByName("filename")
        self.sortByColumn(idx, Qt.AscendingOrder)

    def resetColumns(self):

        self._setHiddenColumns([])
        self._setColumnOrder(list(range(self.columnCount())))

        fm1 = QFontMetrics(self.font())

        self.horizontalHeader().setSectionResizeMode(0)
        idx = self.baseModel().getColumnIndexByName("icon")
        self.setColumnWidth(idx, 40)

        idx = self.baseModel().getColumnIndexByName("state")
        self.setColumnWidth(idx, 40)

        idx = self.baseModel().getColumnIndexByName("filename")
        self.setColumnWidth(idx, 200)

        w = fm1.width("XXXX XX")
        trace("set w", w)

        idx = self.baseModel().getColumnIndexByName("local_size")
        self.setColumnWidth(idx, w * 1.25)

        idx = self.baseModel().getColumnIndexByName("remote_size")
        self.setColumnWidth(idx, w * 1.25)

        w = fm1.width("---------")
        trace("set w", w)

        idx = self.baseModel().getColumnIndexByName("local_permission")
        self.setColumnWidth(idx, w * 1.5) # 125

        idx = self.baseModel().getColumnIndexByName("remote_permission")
        self.setColumnWidth(idx, w * 1.5)

        w = fm1.width("XXXX-XX-XX XX:XX:XX")
        trace("set w", w)

        idx = self.baseModel().getColumnIndexByName("local_mtime")
        self.setColumnWidth(idx, w * 1.25)

        idx = self.baseModel().getColumnIndexByName("remote_mtime")
        self.setColumnWidth(idx, w * 1.25)

        idx = self.baseModel().getColumnIndexByName("remote_path")
        self.setColumnWidth(idx, 100)

        idx = self.baseModel().getColumnIndexByName("remote_public")
        self.setColumnWidth(idx, 100)

        idx = self.baseModel().getColumnIndexByName("remote_encryption")
        self.setColumnWidth(idx, 100)

        idx = self.baseModel().getColumnIndexByName("type")
        self.setColumnWidth(idx, 100)

        trace("setting column widths")

    def onShowHeaderContextMenu(self, event):

        contextMenu = QMenu(self)

        index = self.horizontalHeader().logicalIndexAt(event.x(), event.y())
        name = self.baseModel().getColumn(index).name()
        contextMenu.addAction("Hide %s" % name,
            lambda index=index: self.setColumnHidden(index, True))

        contextMenu.addSeparator()

        for index in self.getHiddenColumns():
            name = self.baseModel().getColumn(index).name()
            contextMenu.addAction("Show %s" % name,
                lambda index=index: self.setColumnHidden(index, False))

        contextMenu.addSeparator()
        contextMenu.addAction("Save State", self.onActionSaveState)
        contextMenu.addAction("Restore State", self.onActionRestoreState)
        contextMenu.addAction("Resize Columns", self.resetColumns)

        contextMenu.exec_(event.globalPos())

    def onActionSaveState(self):
        self.triggerSave.emit()

    def onActionRestoreState(self):
        self.triggerRestore.emit()

    def _fmt_remote_path(self, data, row, key):
        ent = data[row][key]
        if isinstance(ent, sync.DirEnt):
            return ent.remote_base
        return ent.remote_path

    def _fmt_size(self, data, row, key):
        return format_bytes(data[row][key])

    def _fmt_octal(self, data, row, key):
        return format_mode(data[row][key])

    def _fmt_datetime(self, data, row, key):
        return format_datetime(data[row][key])

    def onLocationChanging(self):

        self.setEnabled(False)
        self.setNewData([])

    def refreshData(self):
        data = []
        # todo change record to FileEnt..
        fcount = 0
        dcount = 0
        for ent in self.ctxt.contents():
            item = FileTableRowItem.fromEntry(self.ctxt, ent)
            data.append(item)
            if isinstance(ent, sync.FileEnt):
                fcount += 1
            elif isinstance(ent, sync.DirEnt):
                dcount += 1

        self.setNewData(data)

        return fcount, dcount

    # @ ctxt
    def onLocationChanged(self, directory, target):

        self.setEnabled(True)

        self._details_load_start = False

        fcount, dcount = self.refreshData()

        self.locationChanged.emit(directory, dcount, fcount)

        self.viewport().setFocus(Qt.OtherFocusReason)

        if target is not None:
            current_index = None
            col = self.baseModel().getColumnIndexByName("filename")
            for row in range(0, self.model().rowCount(QModelIndex())):
                index = self.model().index(row, col)
                row = index.data(RowValueRole)
                if row[0].name() == target:
                    current_index = index
                    break
            if current_index is not None:
                self.setCurrentIndex(current_index)
                self.scrollToRow(current_index.row())
            else:
                self.setCurrentIndex(self.model().index(0, 0))
        else:
            # give keyboard focus to the first item
            # TODO: location change should emit a row to highlight
            self.setCurrentIndex(self.model().index(0, 0))

        if self._detailed_view:
            self.loadDetails.emit(self, self.baseModel())
            self._details_load_start = True

    def onMouseDoubleClick(self, index):

        self.onOpenIndex(index)

    def onOpenIndex(self, index):

        row = index.data(RowValueRole)

        if row is None:
            return

        ent = row[0]

        self.openEntry.emit(ent)

    # @ ctxt
    def onMouseReleaseRight(self, event):

        rows = self.getSelection()

        contextMenu = FileContextMenu(self.ctxt, self.cfg, rows, self)

        contextMenu.copyUrls.connect(self.copyUrls)
        contextMenu.createDirectory.connect(self.onBeginCreateDirectory)
        contextMenu.createEmptyFile.connect(self.onBeginCreateEmptyFile)
        contextMenu.rename.connect(self.onBeginRename)
        contextMenu.showHiddenFiles.connect(
            lambda b: self.model().setShowHiddenFiles(b))
        contextMenu.showBlacklistFiles.connect(
            lambda b: self.model().setShowBlacklistFiles(b))

        contextMenu.exec_(event.globalPos())

    def onMouseReleaseMiddle(self, event):
        pass

    def onMouseReleaseBack(self, event):

        self.loadLocation.emit("pop", None)

    def onMouseReleaseForward(self, event):

        self.loadLocation.emit("unpop", None)

    # @ ctxt
    def onDragBegin(self):

        selection = self.getSelection()

        urls = []
        for row in selection:
            ent = row[FileTableRowItem.COL_ENT]

            if isinstance(ent, sync.DirEnt):
                path = ent.local_base
            else:
                path = ent.local_path
            if path:
                urls.append(QUrl(self.ctxt.fs.url(path)))

        if urls:
            drag = QDrag(self)
            mimeData = QMimeData()
            mimeData.setUrls(urls)
            drag.setMimeData(mimeData)
            action = drag.exec_(Qt.CopyAction|Qt.MoveAction|Qt.LinkAction, Qt.MoveAction)
            trace("drag exec action chosen is", action)

    def keyPressEvent(self, event):
        # trace(event.key(), self.state(), QTableView.EditingState)

        # if the editor is open prevent firing open events
        if self.state() == QTableView.EditingState:
            if event.key() == Qt.Key_Home:
                event.accept()
            elif event.key() == Qt.Key_End:
                event.accept()
            else:
                super().keyPressEvent(event)
            return

        if event.key() == Qt.Key_Return:
            row_indices = self.selectionModel().selectedRows()
            if len(row_indices) == 1:
                self.onOpenIndex(row_indices[0])
        elif event.key() == Qt.Key_Backspace:
            self.loadLocation.emit("push-parent", None)
        elif event.key() == Qt.Key_Home:
            self.scrollToRow(0)
        elif event.key() == Qt.Key_End:
            self.scrollToRow(self.rowCount()-1)
        elif Qt.Key_A <= event.key() <= Qt.Key_Z:
            # scroll to the next file that starts with letter
            # loop to the beginning if needed, set the current index
            # to always follow the item names
            col = self.baseModel().getColumnIndexByName("filename")
            index = self.currentIndex()
            if index.column() != col:
                self.setCurrentIndex(self.model().index(index.row(), col))

            super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    # @ ctxt
    def onBeginCreateDirectory(self):
        """
        create a dummy DirEnt and open an editor
        """
        col = self.baseModel().getColumnIndexByName("filename")
        # todo: check for unique name
        ent = sync.DirEnt("New Directory", "", "")
        ent.create = True
        item = FileTableRowItem.fromEntry(self.ctxt, ent)
        self.insertRow(0, item)

        # find the newly inserted index
        current_index = None
        for row in range(0, self.model().rowCount(QModelIndex())):
            index = self.model().index(row, col)
            row = index.data(RowValueRole)
            if ent is row[0]:
                current_index = index
                break;

        self.setCurrentIndex(current_index)
        self.edit(current_index)

    # @ ctxt
    def onCreateDirectory(self, index, value):
        """
        modify the dummy DirEnt with the editor value
        """
        row = index.data(RowValueRole)
        ent = row[0]

        try:

            path = self.ctxt.fs.join(self.ctxt.currentLocation(), value)

            if self.ctxt.hasActiveContext():
                abspath, relpath = self.ctxt.activeContext().normPath(path)
            else:
                abspath = path
                relpath = ""

            if self.ctxt.fs.exists(abspath):
                QMessageBox.information(self, "Create Directory",
                    f"`{value}` already exists")
                self.loadLocation.emit("reload", None)
                return

            self.ctxt.fs.makedirs(abspath)

            # construct a new ent to replace the dummy
            ent = sync.DirEnt(value, relpath, abspath, sync.FileState.PUSH)

            item = FileTableRowItem.fromEntry(self.ctxt, ent)
            self.replaceRow(index.row(), item)

            current_index = None
            col = self.baseModel().getColumnIndexByName("filename")
            for row in range(0, self.model().rowCount(QModelIndex())):
                index = self.model().index(row, col)
                row = index.data(RowValueRole)
                if ent is row[0]:
                    current_index = index
                    break;
            self.setCurrentIndex(current_index)
            self.scrollToRow(current_index.row())

        except Exception as e:
            self.loadLocation.emit("reload", None)
            raise e

    # @ ctxt
    def onBeginCreateEmptyFile(self):
        """
        create a dummy FileEnt and open an editor
        """

        col = self.baseModel().getColumnIndexByName("filename")
        path = self.ctxt.fs.join(self.ctxt.currentLocation(), "newfile.txt")
        ent = sync.FileEnt(None, path, None, None, None)
        ent.create = True
        item = FileTableRowItem.fromEntry(self.ctxt, ent)
        self.insertRow(0, item)

        # find the newly inserted index
        current_index = None
        for row in range(0, self.model().rowCount(QModelIndex())):
            index = self.model().index(row, col)
            row = index.data(RowValueRole)
            if ent is row[0]:
                current_index = index
                break;

        self.setCurrentIndex(current_index)
        self.edit(current_index)

    # @ ctxt
    def onCreateEmptyFile(self, index, value):
        """
        modify the dummy FileEnt with the editor value
        """
        row = index.data(RowValueRole)
        ent = row[0]

        try:

            path = self.ctxt.fs.join(self.ctxt.currentLocation(), value)

            if self.ctxt.hasActiveContext():
                abspath, relpath = self.ctxt.activeContext().normPath(path)
            else:
                abspath = path
                relpath = None

            if self.ctxt.fs.exists(abspath):
                QMessageBox.information(self, "Create File",
                    f"`{value}` already exists")
                self.loadLocation.emit("reload", None)
                return

            open(abspath, "w").close()

            # construct a new ent to replace the dummy
            if self.ctxt.hasActiveContext():
                ent = sync._check_file(self.ctxt.activeContext(), relpath, abspath)
            else:
                ent = sync.FileEnt(relpath, abspath, None, None, None)

            item = FileTableRowItem.fromEntry(self.ctxt, ent)
            self.replaceRow(index.row(), item)

            current_index = None
            col = self.baseModel().getColumnIndexByName("filename")
            for row in range(0, self.model().rowCount(QModelIndex())):
                index = self.model().index(row, col)
                row = index.data(RowValueRole)
                if ent is row[0]:
                    current_index = index
                    break;
            self.setCurrentIndex(current_index)
            self.scrollToRow(current_index.row())

        except Exception as e:
            self.loadLocation.emit("reload", None)
            raise e

    def onBeginRename(self):

        row_indices = self.selectionModel().selectedRows()

        if len(row_indices) == 0:
            return

        trace("begin rename", row_indices)
        index = row_indices[0]
        col = self.baseModel().getColumnIndexByName("filename")
        index = self.model().index(index.row(), col)

        palette = self.palette()
        c = palette.color(QPalette.Active, QPalette.Highlight)
        palette.setColor(QPalette.Inactive,QPalette.Highlight, c)
        self.setPalette(palette)

        # self.setCurrentIndex(index)
        self.selectionModel().setCurrentIndex(index, QItemSelectionModel.NoUpdate)
        self.edit(index)

    # @ ctxt
    def onRenameDirectory(self, index, value):
        row = index.data(RowValueRole)
        ent = row[0]

        try:

            path = self.ctxt.fs.join(self.ctxt.currentLocation(), value)

            if self.ctxt.hasActiveContext():
                abspath, relpath = self.ctxt.activeContext().normPath(path)
            else:
                abspath = path
                relpath = ""

            if self.ctxt.fs.exists(abspath):
                if self.ctxt.fs.samefile(path, abspath):
                    # new name is the same as the old name
                    return
                return

            trace("rename %s -> %s" % (ent.local_base, abspath))
            self.ctxt.fs.rename(ent.local_base, abspath)

            # construct a new ent to replace the dummy
            ent = sync.DirEnt(value, relpath, abspath, sync.FileState.PUSH)

            item = FileTableRowItem.fromEntry(self.ctxt, ent)
            self.replaceRow(index.row(), item)

            # TODO: if in an active context
            #   _check_directory on old path, if remote exists insert ent
            #   check for duplicate entries in the list and remove

            current_index = None
            col = self.baseModel().getColumnIndexByName("filename")
            for row in range(0, self.model().rowCount(QModelIndex())):
                index = self.model().index(row, col)
                row = index.data(RowValueRole)
                if ent is row[0]:
                    current_index = index
                    break;
            self.setCurrentIndex(current_index)
            self.scrollToRow(current_index.row())

        except Exception as e:
            self.loadLocation.emit("reload", None)
            raise e

    # @ ctxt
    def onRenameFile(self, index, value):

        #if index.column() != FileTableRowItem.COL_NAME:
        #    trace("error", index.row(), value)
        #    return

        row = index.data(RowValueRole)
        ent = row[0]

        try:

            path = self.ctxt.fs.join(self.ctxt.currentLocation(), value)

            if self.ctxt.hasActiveContext():
                abspath, relpath = self.ctxt.activeContext().normPath(path)
            else:
                abspath = path
                relpath = None

            if self.ctxt.fs.exists(abspath):
                if self.ctxt.fs.samefile(path, abspath):
                    # new name is the same as the old name
                    return
                return

            trace("rename %s -> %s" % (ent.local_path, abspath))
            self.ctxt.fs.rename(ent.local_path, abspath)

            # construct a new ent to replace the dummy
            if self.ctxt.hasActiveContext():
                ent = sync._check_file(self.ctxt.activeContext(), relpath, abspath)
            else:
                ent = sync.FileEnt(relpath, abspath, None, None, None)

            item = FileTableRowItem.fromEntry(self.ctxt, ent)
            self.replaceRow(index.row(), item)

            # TODO: if in an active context
            #   _check_file on old path, if remote exists insert ent
            #   check for duplicate entries in the list and remove

            current_index = None
            col = self.baseModel().getColumnIndexByName("filename")
            for row in range(0, self.model().rowCount(QModelIndex())):
                index = self.model().index(row, col)
                row = index.data(RowValueRole)
                if ent is row[0]:
                    current_index = index
                    break;
            self.setCurrentIndex(current_index)
            self.scrollToRow(current_index.row())

        except Exception as e:
            self.loadLocation.emit("reload", None)
            raise e

    # @ ctxt
    def onRemoveSelection(self):

        rows = self.getSelection()
        paths = []
        for row in rows:
            ent = row[FileTableRowItem.COL_ENT]
            if isinstance(ent, sync.DirEnt):
                path = ent.local_base
            else:
                path = ent.local_path
            if path:
                paths.append(path)

        dialog = SyncProgressDialog()
        thread = RemoveProgressThread(self.ctxt.fs, paths, self)
        dialog.setThread(thread)
        dialog.exec_()
        self.loadLocation.emit("remove", [row[FileTableRowItem.COL_ENT] for row in rows])

    def onSetFilterPattern(self, pattern):
        self.model().setFilterGlobPattern(pattern)

    def editRow(self, row, col):
        """ used by the edit delegate to edit next/previous row"""
        # todo: bounds checking?

        palette = self.palette()
        c = palette.color(QPalette.Active, QPalette.Highlight)
        palette.setColor(QPalette.Inactive,QPalette.Highlight, c)
        self.setPalette(palette)

        index = self.model().index(row, col)
        self.setCurrentIndex(index)
        self.edit(index)

    def onCommitValidateData(self, index, value):


        colidx = self.baseModel().getColumnIndexByName("filename")
        if index.column() != colidx:
            return True

        trace(value)

        selection = self.selectionModel().selectedRows()

        if len(selection) < 2:
            selection = [index]

        trace(selection)
        original_value = value

        # TODO: this needs to be reworked
        # when renaming multiple, emit a specific signal to handle that case

        for count, index in enumerate(selection):

            if count > 0:
                a, b = os.path.splitext(original_value)
                temp = f"{a} ({count}){b}"
            else:
                temp = original_value

            trace(index.data(RowValueRole)[FileTableRowItem.COL_ENT].name(), '=>', temp)


        for count, index in enumerate(selection):

            row = index.data(RowValueRole)
            ent = row[FileTableRowItem.COL_ENT]
            trace(ent)

            if count > 0:
                a, b = os.path.splitext(original_value)
                value = f"{a} ({count}){b}"
            else:
                value = original_value

            # todo: on editor close remove dummy ents if not committing
            if isinstance(ent, sync.DirEnt):
                # todo: better dummy entry checking?
                if hasattr(ent, 'create'):
                    self.createDirectory.emit(index, value)
                else:
                    self.renameDirectory.emit(index, value)

            if isinstance(ent, sync.FileEnt):
                if hasattr(ent, 'create'):
                    self.createEmptyFile.emit(index, value)
                else:
                    self.renameFile.emit(index, value)

        # always fail the validation, the row will be updated
        # during a successful rename
        return False

    def closeEditor(self, editor, hint):

        super().closeEditor(editor, hint)

        if hint == QAbstractItemDelegate.RevertModelCache:
            i = 0
            while i < len(self.baseModel().tabledata):
                row = self.baseModel().tabledata[i]
                ent = row[0]
                if hasattr(row[0], 'create'):
                    self.baseModel().removeRow(i)
                else:
                    i += 1

        trace("reset color")
        palette = self.palette()
        c = QApplication.instance().palette().color(QPalette.Inactive,QPalette.Highlight)
        palette.setColor(QPalette.Inactive, QPalette.Highlight, c)
        self.setPalette(palette)

    def onSelectionChanged(self):
        pass

    def paintEvent(self, event):

        super().paintEvent(event)

        if self.rowCount() == 0:
            text = "Directory Empty"
            painter = QPainter()
            painter.begin(self.viewport())
            painter.setRenderHint(QPainter.Antialiasing)
            #painter.fillRect(self.rect(),
            #    QBrush(QColor(255, 0, 0, 127)))
            painter.drawText(self.rect(),
                Qt.AlignHCenter|Qt.AlignVCenter, text)
            painter.end()

    def _foregroundRule(self, index, col):

        #row = index.data(RowValueRole)
        #ent = row[0]
        #state = row[-1].split(":")[0]

        return None

    # @ ctxt
    def _backgroundRule(self, index, col):

        row = index.data(RowValueRole)
        ent = row[0]
        state = row[FileTableRowItem.COL_STATE].split(":")[0]

        if not self.ctxt.hasActiveContext():
            return

        idx = self.baseModel().getColumnIndexByName("state")
        if index.column() == idx:
            if row[9] == 'client':
                return QColor(0xFF, 0xD7, 0x00)
            if row[9] == 'server':
                return QColor(0x0F, 0x52, 0xBA)
            if row[9] == 'system':
                return QColor(0x9B, 0x11, 0x1E)

        if state == sync.FileState.SAME:
            return None

        elif state == sync.FileState.IGNORE:
            return QColor(200, 32, 200, 32)

        elif state == sync.FileState.PUSH:
            return QColor(32, 200, 32, 32)

        elif state == sync.FileState.PULL:
            return QColor(32, 32, 200, 32)

        elif state == sync.FileState.CONFLICT_MODIFIED:
            return QColor(255, 170, 0, 32)

        elif state == sync.FileState.CONFLICT_CREATED:
            return QColor(255, 170, 0, 32)

        elif state == sync.FileState.CONFLICT_VERSION:
            return QColor(255, 170, 0, 32)

        elif state == sync.FileState.CONFLICT_TYPE:
            return QColor(255, 170, 0, 32)

        elif state == sync.FileState.DELETE_BOTH:
            return QColor(255, 50, 0, 32)

        elif state == sync.FileState.DELETE_REMOTE:
            return QColor(255, 50, 0, 32)

        elif state == sync.FileState.DELETE_LOCAL:
            return QColor(255, 50, 0, 32)

        if state == sync.FileState.ERROR:
            return QColor(255, 0, 0, 64)

        return None

    def onToggleDetailedView(self):
        self._detailed_view = not self._detailed_view

        fm = QFontMetrics(self.font())
        v = self.verticalHeader()

        idx_icon = self.baseModel().getColumnIndexByName("icon")
        idx_state = self.baseModel().getColumnIndexByName("state")

        if self._detailed_view:

            w = int(4.5 * fm.height() * self.cfg.rowScale)
            v.setDefaultSectionSize(w)
            trace(w,w)
            self.setColumnWidth(idx_icon, w)
            self.setColumnWidth(idx_state, w)
        else:

            w = int(fm.height() * self.cfg.rowScale)
            v.setDefaultSectionSize(w)
            trace(40, w)

            self.setColumnWidth(idx_icon, 40)
            self.setColumnWidth(idx_state, 40)

        if not self._details_load_start:
            self.loadDetails.emit(self, self.baseModel())
            self._details_load_start = True

        return self._detailed_view

    def wheelEvent(self, event):
        """
        some platforms / mice (windows) send angle increments
        of +/- 120 degrees other platforms send updates more frequently.

        capture the angle events in an accumulator and supress events
        until some threshold has been met
        """

        # bar = self.horizontalScrollBar()
        # trace(bar.value(), "|", bar.minimum(), bar.maximum(), bar.singleStep(), bar.pageStep())

        if sys.platform == 'win32':
            return super().wheelEvent(event)

        xdelta_thresh = 40
        ydelta_thresh = 120

        self._wheel_accumulator += event.angleDelta()
        self._wheel_counter += 1

        dx = self._wheel_accumulator.x() // xdelta_thresh
        dy = self._wheel_accumulator.y() // ydelta_thresh

        if dx != 0 or dy != 0:
            rx = self._wheel_accumulator.x() % xdelta_thresh
            ry = self._wheel_accumulator.y() % ydelta_thresh

            event = QWheelEvent(
                event.pos(),
                event.globalPos(),
                event.pixelDelta(),
                QPoint(xdelta_thresh * dx, ydelta_thresh * dy),
                event.buttons(),
                event.modifiers(),
                event.phase(),
                event.inverted(),
                event.source())

            self._wheel_accumulator = QPoint(rx, ry)
            self._wheel_counter = 0

            return super().wheelEvent(event)

class FileGridView(GridView):

    openEntry = pyqtSignal(object)

    def __init__(self, cfg, parent=None):
        super(FileGridView, self).__init__(parent)

        self.cfg = cfg
        self.doubleClicked.connect(self.onOpenIndex)

        s1 = int(self.cfg.iconSize)
        s2 = int(self.cfg.iconSize * 1.5)
        self.setIconSize(QSize(s1, s1))
        self.setGridSize(QSize(s2, s2))
        self.setSpacing(100)

    def onOpenIndex(self, index):

        row = index.data(RowValueRole)

        if row is None:
            return

        ent = row[0]

        self.openEntry.emit(ent)


    def resizeEvent(self, event):

        #s = 80
        #n = self.width()//s
        #p = self.width()%s//n
        #trace(p)
        super().resizeEvent(event)

class FavoritesDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super(FavoritesDelegate, self).__init__(parent)

    def paint(self, painter, option, index):

        opt = QStyleOptionViewItem(option)

        opt.font.setBold(self.isBold(index))

        super().paint(painter, opt, index)

    def isBold(self, index):
        # each row for this table contains a bool indicating
        # if the row should be bold
        row = index.data(RowValueRole)
        return row[-1]

class MonospaceDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super(MonospaceDelegate, self).__init__(parent)

    def paint(self, painter, option, index):

        opt = QStyleOptionViewItem(option)

        opt.font.setStyleHint(QFont.Monospace)
        opt.font.setFamily("Courier New")

        super().paint(painter, opt, index)

class FavoritesListView(TableView):

    pushDirectoryMain = pyqtSignal(str)
    pushDirectorySecondary = pyqtSignal(str)
    toggleHiddenSection = pyqtSignal(str)

    def __init__(self, cfg, parent=None):
        super(FavoritesListView, self).__init__(parent)

        self.cfg = cfg

        fm = QFontMetrics(self.font())
        v = self.verticalHeader()
        v.setSectionResizeMode(QHeaderView.Fixed)
        trace(v.defaultSectionSize(), fm.height())
        v.setDefaultSectionSize(int(fm.height() * self.cfg.rowScale))

        self.setLastColumnExpanding(True)

        self.setWordWrap(False)
        self.setVerticalHeaderVisible(False)
        self.setHorizontalHeaderVisible(False)

        #idx = self.baseModel().addColumn(0, "icon")
        #self.setDelegate(idx, ImageDelegate(self))
        idx = self.baseModel().addColumn(1, "favorites")
        self.setDelegate(idx, FavoritesDelegate(self))
        self.model().getColumn(idx).setDecorationKey(0)

        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

    def setVisible(self, b):
        super().setVisible(b)

        #idx = self.baseModel().getColumnIndexByName("icon")
        #self.setColumnWidth(idx, 32)

    def onMouseDoubleClick(self, index):
        data = index.data(RowValueRole)
        path = data[2]
        if path is not None:
            path = os.path.expanduser(path)
            path = os.path.expandvars(path)
            self.pushDirectoryMain.emit(path)
        else:
            self.toggleHiddenSection.emit(data[1])

    def onMouseReleaseRight(self, event):

        contextMenu = QMenu(self)

        contextMenu.addAction("Open Directory (Left)", self.onPushDirectoryMain)
        contextMenu.addAction("Open Directory (Right)", self.onPushDirectorySecondary)

        contextMenu.exec_(event.globalPos())

    def onMouseReleaseMiddle(self, event):
        pass

    def onHeaderClicked(self, idx):
        pass

    def onPushDirectoryMain(self):
        rows = self.getSelection()
        if len(rows) > 0:
            path = rows[0][2]
            path = os.path.expanduser(path)
            path = os.path.expandvars(path)
            if path is not None:
                self.pushDirectoryMain.emit(path)

    def onPushDirectorySecondary(self):
        rows = self.getSelection()
        if len(rows) > 0:
            path = rows[0][2]
            path = os.path.expanduser(path)
            path = os.path.expandvars(path)
            if path is not None:
                self.pushDirectorySecondary.emit(path)

class LocationView(QWidget):

    loadLocation = pyqtSignal(str, str)  # async load, mode, dir
    setFilterPattern = pyqtSignal(str)
    splitInterface = pyqtSignal()
    toggleDetailedView = pyqtSignal()

    def __init__(self, ctxt, parent=None):
        super(LocationView, self).__init__(parent)

        self.ctxt = ctxt
        self.vbox = QVBoxLayout(self)
        self.hbox1 = QHBoxLayout()
        self.hbox3 = QHBoxLayout()
        self.hbox2 = QHBoxLayout()
        self.hbox2.setContentsMargins(0, 0, 0, 0)

        # https://joekuan.wordpress.com/2015/09/23/list-of-qt-icons/
        self.edit_location = LineEdit(self)
        self.edit_filter = LineEdit(self)
        self.edit_filter.setMaximumWidth(250)
        #self.edit_filter.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self.edit_filter.setPlaceholderText("Filter")

        self.btn_back = QToolButton(self)
        self.btn_back.setIcon(self.style().standardIcon(QStyle.SP_FileDialogBack))
        self.btn_back.setAutoRaise(True)

        self.btn_forward = QToolButton(self)
        self.btn_forward.setIcon(self.style().standardIcon(QStyle.SP_ArrowForward))
        self.btn_forward.setAutoRaise(True)

        self.btn_up = QToolButton(self)
        self.btn_up.setIcon(self.style().standardIcon(QStyle.SP_FileDialogToParent))
        self.btn_up.setAutoRaise(True)

        self.btn_refresh = QToolButton(self)
        self.btn_refresh.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        self.btn_refresh.setAutoRaise(True)

        self.btn_open = QToolButton(self)
        self.btn_open.setIcon(self.style().standardIcon(QStyle.SP_ArrowForward))
        self.btn_open.setAutoRaise(True)

        self.btn_details = QToolButton(self)
        self.btn_details.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        self.btn_details.setAutoRaise(True)

        self.btn_split = QToolButton(self)
        self.btn_split.clicked.connect(self.splitInterface)

        self.hbox1.addWidget(self.btn_back)
        self.hbox1.addWidget(self.btn_forward)
        self.hbox1.addWidget(self.btn_up)
        self.hbox1.addWidget(self.btn_refresh)
        self.hbox1.addStretch(1)
        #self.hbox1.addWidget(self.edit_location)
        self.hbox1.addWidget(self.edit_filter)
        self.hbox1.addWidget(self.btn_details)
        self.hbox1.addWidget(self.btn_split)

        self.hbox3.addWidget(self.edit_location)
        self.hbox3.addWidget(self.btn_open)

        self.vbox.addLayout(self.hbox1)
        self.vbox.addLayout(self.hbox3)

        self.btn_fetch = QPushButton("Fetch", self)
        self.btn_sync = QPushButton("Sync", self)
        self.btn_push = QPushButton(
            self.style().standardIcon(QStyle.SP_ArrowUp), "Push", self)
        self.btn_pull = QPushButton(self.style().standardIcon(QStyle.SP_ArrowDown),
            "Pull", self)
        self.hbox2.addWidget(self.btn_fetch)
        self.hbox2.addWidget(self.btn_sync)
        self.hbox2.addWidget(self.btn_push)
        self.hbox2.addWidget(self.btn_pull)
        self.hbox2.addStretch(1)

        self.vbox.addLayout(self.hbox2)

        self.btn_back.clicked.connect(self.onBackButtonPressed)
        self.btn_forward.clicked.connect(self.onForwardButtonPressed)
        self.btn_up.clicked.connect(self.onUpButtonPressed)
        self.btn_refresh.clicked.connect(self.onRefreshButtonPressed)
        self.btn_open.clicked.connect(self.onOpenButtonPressed)
        self.btn_fetch.clicked.connect(self.onFetchButtonPressed)
        self.btn_sync.clicked.connect(self.onSyncButtonPressed)
        self.btn_push.clicked.connect(self.onPushButtonPressed)
        self.btn_pull.clicked.connect(self.onPullButtonPressed)
        self.btn_details.clicked.connect(self.toggleDetailedView)
        self.edit_filter.textChanged.connect(self.setFilterPattern)
        self.edit_location.returnPressed.connect(self.onOpenButtonPressed)
        self.ctxt.locationChanging.connect(self.onLocationChanging)
        self.ctxt.locationChanged.connect(self.onLocationChanged)
        self.ctxt.locationModified.connect(self.onLocationModified)

    def showSplitButton(self, visible):
        self.btn_split.setVisible(visible)

    def setSplitIcon(self, bSplit):

        img = QPixmap(32, 32)
        img.fill( Qt.transparent)
        painter = QPainter()
        painter.begin(img)
        painter.setPen(QColor(0, 0, 0))
        painter.setRenderHint(QPainter.Antialiasing)
        # painter.fillRect(3, 3, 27, 27, QColor(127, 127, 127))
        painter.drawRoundedRect(2, 2, 28, 28, 4, 4)
        if bSplit:
            painter.drawRoundedRect(2, 2, 15, 28, 4, 4)
            painter.drawRoundedRect(15, 2, 15, 28, 4, 4)
        painter.end()
        self.btn_split.setIcon(QIcon(img))
        self.btn_split.setAutoRaise(True)

    def onBackButtonPressed(self):
        self.loadLocation.emit("pop", None)

    def onForwardButtonPressed(self):
        self.loadLocation.emit("unpop", None)

    def onUpButtonPressed(self):
        self.loadLocation.emit("push-parent", None)

    def onRefreshButtonPressed(self):
        self.loadLocation.emit("reload", None)

    def onOpenButtonPressed(self):
        directory = self.edit_location.text().strip()

        directory = os.path.expanduser(directory)
        directory = os.path.expandvars(directory)

        if self.ctxt.fs.islocal(directory) and not self.ctxt.fs.exists(directory):
            trace("directory does not exist", directory)
            # TODO: change bar to red background color until successful load
            #return

        self.loadLocation.emit("push", directory)

    def _getEnt(self):
        path = self.ctxt.currentLocation()
        abspath, relpath = self.ctxt.activeContext().normPath(path)
        ent = sync.DirEnt(abspath.split()[-1], relpath, abspath)
        return ent

    def onFetchButtonPressed(self):

        dialog = SyncProgressDialog()
        thread = FetchProgressThread(self.ctxt, dialog)
        dialog.setThread(thread, "Fetching...")
        dialog.exec_()
        self.loadLocation.emit("reload", None)

    def _onSyncButtonPressedImpl(self, push, pull):

        dent = self._getEnt()

        optdialog = SyncOptionsDialog(self)
        if optdialog.exec_() == QDialog.Accepted:
            opts = optdialog.options()
            dialog = SyncProgressDialog()
            thread = SyncProgressThread(
                self.ctxt,
                [dent], push, pull, opts['force'],  opts['recursive'],
                dialog)
            dialog.setThread(thread, "Syncing...")
            dialog.exec_()
            self.loadLocation.emit("reload", None)

    def onSyncButtonPressed(self):
        self._onSyncButtonPressedImpl(True, True)

    def onPushButtonPressed(self):
        self._onSyncButtonPressedImpl(True, False)

    def onPullButtonPressed(self):
        self._onSyncButtonPressedImpl(False, True)

    def onLocationChanging(self):

        self.setEnabled(False)

    def onLocationChanged(self, directory, target):

        self.setEnabled(True)

        self.btn_forward.setEnabled(self.ctxt.hasForwardHistory())
        self.btn_back.setEnabled(self.ctxt.hasBackHistory())

        active = self.ctxt.hasActiveContext()

        self.btn_fetch.setVisible(active)
        self.btn_sync.setVisible(active)
        self.btn_push.setVisible(active)
        self.btn_pull.setVisible(active)

        active = self.ctxt.fs.islocal(directory)

        self.btn_details.setEnabled(active)

        self.edit_location.setText(directory)

    def onLocationModified(self):

        self.setEnabled(True)


    def resizeEvent(self, event):

        # hide certain buttons as the ui shrinks
        visible = self.width() > 350
        isVisible = self.edit_filter.isVisible()

        if visible != isVisible:
            self.btn_back.setVisible(visible)
            self.btn_forward.setVisible(visible)
            self.edit_filter.setVisible(visible)

        visible = self.width() > 200
        isVisible = self.btn_open.isVisible()

        if visible != isVisible:
            self.btn_up.setVisible(visible)
            self.btn_refresh.setVisible(visible)
            self.btn_open.setVisible(visible)

class ProgressThread(QThread):

    processingFile = pyqtSignal(str)  # path
    fileStatus = pyqtSignal(object)  # list of status result
    getEncryptionPassword = pyqtSignal(str)  # kind

    # show a message box to the user
    # (title, text, icon, choices)
    getChoice = pyqtSignal(str, str, object, list)

    def __init__(self, parent=None):
        super(ProgressThread, self).__init__(parent)

        self.alive = True

        self._tlimit_1 = 0
        self._tlimit_2 = 0
        self._results = []

        self._password = None
        self._userChoiceIndex = None
        self._lk_password = QMutex()
        self._cv_password = QWaitCondition()

    def run(self):

        try:
            self.main()
        except StopIteration as e:
            pass
        except Exception as e:
            logging.exception(e)

    def main(self):
        pass

    def getEncryptionPasswordWaiter(self, kind):
        """
        emit a signal to open a password dialog on the main thread
        then wait for the dialog to close and the password to be set
        return the password

        this blocks the calling thread while the ui is operated
        """

        self._lk_password.lock()
        try:
            self._password = None
            self.getEncryptionPassword.emit(kind)
            self._cv_password.wait(self._lk_password)
        finally:
            self._lk_password.unlock()

        return self._password

    def setEncryptionPassword(self, password):

        self._lk_password.lock()
        try:
            self._password = password
            self._cv_password.wakeAll()
        finally:
            self._lk_password.unlock()

    def getUserChoice(self, title, text, icon, choices):
        # icons:
        #     QMessageBox.NoIcon
        #     QMessageBox.Question
        #     QMessageBox.Information
        #     QMessageBox.Warning
        #     QMessageBox.Critical
        # choices: a list of strings for button text
        #
        # returns: index of the button clicked or None on error

        self._lk_password.lock()
        try:
            self._userChoiceIndex = None
            self.getChoice.emit(title, text, icon, choices)
            self._cv_password.wait(self._lk_password)
        finally:
            self._lk_password.unlock()

        return self._userChoiceIndex

    def setUserChoice(self, choiceIndex):
        self._lk_password.lock()
        try:
            self._userChoiceIndex = choiceIndex
            self._cv_password.wakeAll()
        finally:
            self._lk_password.unlock()

    def sendUpdate(self, path):

        now = time.time()

        if self._tlimit_1 + .5 < now:
            self._tlimit_1 = now

            self.processingFile.emit(path)

    def sendStatus(self, status, force=False):

        if isinstance(status, list):
            self._results.extend(status)
        else:
            self._results.append(status)

        now = time.time()

        if force or self._tlimit_2 + .5 < now:
            self._tlimit_2 = now

            self.fileStatus.emit(self._results)
            self._results = []

    def checkAlive(self):
        if not self.alive:
            raise StopIteration()

class FetchProgressThread(ProgressThread):

    def __init__(self, ctxt, parent=None):
        super(FetchProgressThread, self).__init__(parent)

        self.ctxt = ctxt

    def main(self):

        # construct a new sync context for this thread
        ctxt = self.ctxt.activeContext().clone()
        ctxt.getPassword = self.getEncryptionPasswordWaiter

        # create an iterable in this thread for processing the command

        # iterable = _dummy_fetch_iter(ctxt)
        iterable = sync._fetch_iter(ctxt)

        while True:

            try:

                item = next(iterable)

                if item[2] == 'insert':
                    text = "+ %s" % item[0]
                elif item[2] == 'update':
                    text = ". %s" % item[0]
                elif item[2] == 'delete':
                    text = "- %s" % item[0]
                self.sendUpdate(text)
                self.sendStatus(text)

            except StopIteration as e:
                trace("stop iteration")
                break
            except Exception as e:
                # TODO: reraise in main thread
                logging.exception(e)
                break

            if not self.alive:
                break

        self.fileStatus.emit(self._results)

        # close the database connection
        ctxt.close()

class SyncProgressThread(ProgressThread):

    def __init__(self, ctxt, paths, push, pull, force, recursive, parent=None):
        super(SyncProgressThread, self).__init__(parent)

        self.ctxt = ctxt
        self.paths = paths
        self.push = push
        self.pull = pull
        self.force = force
        self.recursive = recursive

    def main(self):

        ctxt = self.ctxt.activeContext().clone()
        ctxt.getPassword = self.getEncryptionPasswordWaiter

        # iterable = _dummy_sync_iter(
        #    ctxt, self.paths,
        #    self.push, self.pull, self.force, self.recursive
        # )

        iterable = sync._sync_impl_iter(
            ctxt, self.paths,
            self.push, self.pull, self.force, self.recursive
        )

        if self.push and self.pull:
            mode = "sync"
        elif self.push:
            mode = "push"
        else:
            mode = "pull"

        self.sendStatus("mode: %s\nforce: %s\nrecursive: %s" % (
            mode, self.force, self.recursive))

        while True:

            try:

                fent = next(iterable)
                self.sendUpdate(fent.remote_path)

                result = next(iterable)

                sym = sync.FileState.symbol(result.state)

                self.sendStatus("%s %s" % (sym, result.ent.remote_path))

                if result.message:
                    self.sendStatus(result.message.strip())

            except StopIteration as e:
                break

            except Exception as e:
                # TODO: reraise in main thread
                lines = traceback.format_exception(*sys.exc_info())
                self.sendStatus(lines, True)
                logging.exception(e)
                break

            if not self.alive:
                break

        self.fileStatus.emit(self._results)

        ctxt.close()

class CopyProgressThread(ProgressThread):

    def __init__(self, fs, urls, dst, action, parent=None):
        super(CopyProgressThread, self).__init__(parent)

        self.fs = fs
        self.urls = urls
        self.dst = dst
        self.action = action

        self._new_names = []

    def main(self):

        #index = self.getUserChoice("Text", "click a button",
        #    QMessageBox.Information,
        #    ["Skip", "Replace", "Replace All", "Keep", "Keep All"])
        #trace("user chose", index)

        discoveredSize = 0
        transferedSize = 0

        if self.action == Qt.MoveAction:
            for url in self.urls:
                if not self.fs.samedrive(url, self.dst):
                    self.action = Qt.CopyAction
                    break

        if self.action == Qt.MoveAction:
            generator = self.fs.move_multiple(self.urls, self.dst)
            handler = self._move_one
            self.sendStatus("Moving Files", force=True)
        else:
            generator = self.fs.copy_multiple(self.urls, self.dst)
            handler = self._copy_one
            self.sendStatus("Copying Files", force=True)

        while True:
            self.checkAlive()

            try:
                kind, src, dst, size = next(generator)

            except StopIteration:
                break

            discoveredSize += size
            self.sendUpdate("%d/%d %s" % (
                transferedSize, discoveredSize, dst))

            try:
                handler(kind, src, dst)
            except OSError as e:
                self.sendStatus("%s:\n %s" % (src, e))
            except Exception as e:
                self.sendStatus("%s:\n %s" % (src, e))

        self.sendStatus("done", force=True)

    def _move_one(self, kind, src, dst):

        if self.fs.exists(dst):
            self.sendStatus("Cannot move file destination exists:\n  %s\n  %s" % (src, dst))
            return

        if kind == FileSystem.FS_DIR:
            self.fs.rename(src, dst)
        elif kind == FileSystem.FS_REG:
            self.fs.rename(src, dst)

    def _copy_one(self, kind, src, dst):


        if kind == FileSystem.FS_DIR:
            self.fs.makedirs(dst)

        elif kind == FileSystem.FS_REG:

            if self.fs.exists(dst):
                dst = self._safe_name(dst)

            self._copy_file(src, dst)

        # discover new names in the root directory
        parent, name = self.fs.split(dst)
        if parent == self.dst:
            self._new_names.append(name)


    def _safe_name(self, path):
        i = 1
        while True:
            new_path = "%s (%d)" % (path, i)
            if not self.fs.exists(new_path):
                path = new_path
                break
            i += 1
        return path

    def _copy_file(self, src, dst):

        with self.fs.open(dst, "wb") as wb:
            with self.fs.open(src, "rb") as rb:
                buf = rb.read(4096)
                while buf:
                    wb.write(buf)
                    buf = rb.read(4096)

class RemoveProgressThread(ProgressThread):

    def __init__(self, fs, urls, parent=None):
        super(RemoveProgressThread, self).__init__(parent)

        self.fs = fs
        self.urls = urls

    def main(self):

        index = self.getUserChoice("Delete", "Remove items?",
            QMessageBox.Warning,
            ["Delete", "Cancel"])

        if index != 0:
            self.sendStatus("Action canceled by user")
            return

        discoveredSize = 0
        transferedSize = 0
        generator = self.fs.delete_multiple(self.urls)

        for url in self.urls:
            self.sendStatus(url)

        while True:

            self.checkAlive()

            try:
                kind, src, size = next(generator)
            except StopIteration:
                break

                discoveredSize += size
                self.sendUpdate("%d/%d" % (transferedSize, discoveredSize))

            try:
                self._remove_one(kind, src)
            except OSError as e:
                self.sendStatus("%s:\n %s" % (src, e))
            except Exception as e:
                self.sendStatus("%s:\n %s" % (src, e))

        self.sendStatus("done", force=True)

    def _remove_one(self, kind, src):

        if kind == FileSystem.FS_DIR:
            self._remove_dir(src)

        elif kind == FileSystem.FS_REG:
            self._remove_reg(src)

    def _remove_dir(self, src):
        #self.fs.rmdir(src)
        pass

    def _remove_reg(self, src):

        #self.fs.remove(src)
        pass

class SyncOptionsDialog(QDialog):

    def __init__(self, parent=None):
        super(SyncOptionsDialog, self).__init__(parent)

        self.vbox = QVBoxLayout(self)

        self.chk_force = QCheckBox("Force", self)
        self.chk_recursive = QCheckBox("Recursive", self)

        self.btn_sync = QPushButton("Sync", self)
        self.btn_cancel = QPushButton("Cancel", self)

        self.hbox = QHBoxLayout()
        self.hbox.addStretch(1)
        self.hbox.addWidget(self.btn_sync)
        self.hbox.addWidget(self.btn_cancel)

        self.vbox.addWidget(self.chk_force)
        self.vbox.addWidget(self.chk_recursive)
        self.vbox.addLayout(self.hbox)

        self._options = None

        self.btn_sync.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

    def accept(self):

        self._options = {
            "force": self.chk_force.isChecked(),
            "recursive": self.chk_recursive.isChecked(),
        }

        super().accept()

    def options(self):
        return self._options

class SyncProgressDialog(QDialog):

    def __init__(self, parent=None):
        super(SyncProgressDialog, self).__init__(None)

        self.vbox = QVBoxLayout(self)

        self.lbl_action = QLabel(self)
        self.lbl_action.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.lbl_action.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.lbl_status = QLabel(self)
        self.lbl_status.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.lbl_status.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.txt_status = QTextEdit(self)
        self.txt_status.setReadOnly(True)
        self.txt_status.setWordWrapMode(QTextOption.NoWrap)

        self.btn_exit = QPushButton("Cancel", self)

        self.hbox = QHBoxLayout()
        self.hbox.addStretch(1)
        self.hbox.addWidget(self.btn_exit)

        self.vbox.addWidget(self.lbl_action)
        self.vbox.addWidget(self.lbl_status)
        self.vbox.addWidget(self.txt_status)
        self.vbox.addLayout(self.hbox)

        self.btn_exit.clicked.connect(self.onExitPressed)

        self._run_fetch = False
        self._run_sync = False

        self.thread = None

        self._resizeTimer = QTimer()
        self._resizeTimer.setSingleShot(True)
        self._resizeTimer.timeout.connect(self.onResizeTimeout)

    def setThread(self, thread, action="Running..."):

        if self.thread is not None:
            return

        self.lbl_action.setText(action)

        self.thread = thread

        self.thread.getEncryptionPassword.connect(self.onGetEncryptionPassword)
        self.thread.getChoice.connect(self.onGetUserChoice)
        self.thread.processingFile.connect(lambda path: self.lbl_status.setText(path))
        self.thread.fileStatus.connect(lambda paths: self.txt_status.append('\n'.join(paths)))
        self.thread.finished.connect(self.onThreadFinished)

    def onGetEncryptionPassword(self, kind):

        password = None

        try:
            password = PasswordDialog.getPasswordKind(kind)

        finally:
            # set the password, or None if the user canceled
            # wake up the thread that was waiting
            self.thread.setEncryptionPassword(password)

    def onGetUserChoice(self, title, text, icon, choices):

        index = None
        try:
            box = QMessageBox(self)

            box.setWindowTitle(title)
            box.setText(text)
            box.setIcon(icon)

            # create buttons for all choices
            btns = []
            for choice in choices:
                btns.append(box.addButton(choice, QMessageBox.AcceptRole))
            if btns:
                box.setDefaultButton(btns[-1])

            box.exec_()

            # figure out which button index was clicked
            for i, btn in enumerate(btns):
                if btn == box.clickedButton():
                    index = i
                    break
        finally:
            self.thread.setUserChoice(index)

    def onThreadFinished(self):

        self.lbl_status.setText("Finished.")
        self.btn_exit.setText("Close")
        # TODO: if no thread errors
        self.accept()

    def reject(self):
        if self.thread.isRunning():
            return

        self.thread.wait()

        super().reject()

    def accept(self):
        if self.thread.isRunning():
            return

        self.thread.wait()

        super().accept()

    def onExitPressed(self):

        self.thread.alive = False
        self.accept()

    def exec_(self):

        self.thread.start()
        super().exec_()

    def show(self):
        self.thread.start()
        super().show()

    def resizeEvent(self, event):
        # failed attempt at improving resize performance
        #self._resizeTimer.start(500)
        #self.txt_status.hide()
        #super().resizeEvent(event)
        pass

    def onResizeTimeout(self):
        #self.txt_status.show()
        pass

class FileEntryInfoDialog(QDialog):

    def __init__(self, parent=None):
        super(FileEntryInfoDialog, self).__init__(parent)

        self.layout = QGridLayout()

        self.btn_accept = QPushButton("Close")
        self.btn_accept.clicked.connect(self.accept)

        self.hbox = QHBoxLayout()
        self.hbox.addStretch(1)
        self.hbox.addWidget(self.btn_accept)

        self.vbox = QVBoxLayout(self)
        self.vbox.addLayout(self.layout)
        self.vbox.addStretch(1)
        self.vbox.addLayout(self.hbox)

        self.txt_local = QLineEdit(self)
        self.txt_local.setReadOnly(True)

        self.txt_remote = QLineEdit(self)
        self.txt_remote.setReadOnly(True)

        self.lbl_status = QLabel(self)
        self.lbl_status.setAlignment(Qt.AlignRight)

        self.lbl_status_image = QLabel(self)
        self.lbl_status_image.setFixedHeight(32)
        self.lbl_status_image.setFixedWidth(32)
        #self.lbl_status_image.setFrameStyle(QFrame.Panel | QFrame.Raised)

        self.lbl_disk = QLabel("Disk", self)
        self.lbl_disk.setAlignment(Qt.AlignCenter)

        self.lbl_cache = QLabel("Cache", self)
        self.lbl_cache.setAlignment(Qt.AlignCenter)

        self.lbl_remote = QLabel("Remote", self)
        self.lbl_remote.setAlignment(Qt.AlignCenter)

        self.lbl_r_public = QLabel(self)
        self.lbl_r_encryption = QLabel(self)

        self.lbl_r_public.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.lbl_r_public.setFrameStyle(QFrame.Panel | QFrame.Raised)
        self.lbl_r_public.setAlignment(Qt.AlignRight)

        self.lbl_r_encryption.setFrameStyle(QFrame.Panel | QFrame.Raised)
        self.lbl_r_encryption.setAlignment(Qt.AlignRight)

        self.btn_r_public_copy = QPushButton("Copy Link", self)
        self.btn_r_public = QPushButton("Create/Revoke", self)

        self.lbl_a_version = QLabel(self)
        self.lbl_l_version = QLabel(self)
        self.lbl_r_version = QLabel(self)

        self.lbl_a_size = QLabel(self)
        self.lbl_l_size = QLabel(self)
        self.lbl_r_size = QLabel(self)

        self.lbl_a_mtime = QLabel(self)
        self.lbl_l_mtime = QLabel(self)
        self.lbl_r_mtime = QLabel(self)

        self.lbl_a_permission = QLabel(self)
        self.lbl_l_permission = QLabel(self)
        self.lbl_r_permission = QLabel(self)

        self.lbl_a_version.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.lbl_l_version.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.lbl_r_version.setFrameStyle(QFrame.Panel | QFrame.Sunken)

        self.lbl_a_size.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.lbl_l_size.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.lbl_r_size.setFrameStyle(QFrame.Panel | QFrame.Sunken)

        self.lbl_a_mtime.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.lbl_l_mtime.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.lbl_r_mtime.setFrameStyle(QFrame.Panel | QFrame.Sunken)

        self.lbl_a_permission.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.lbl_l_permission.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.lbl_r_permission.setFrameStyle(QFrame.Panel | QFrame.Sunken)

        self.lbl_a_version.setAlignment(Qt.AlignRight)
        self.lbl_l_version.setAlignment(Qt.AlignRight)
        self.lbl_r_version.setAlignment(Qt.AlignRight)

        self.lbl_a_size.setAlignment(Qt.AlignRight)
        self.lbl_l_size.setAlignment(Qt.AlignRight)
        self.lbl_r_size.setAlignment(Qt.AlignRight)

        self.lbl_a_mtime.setAlignment(Qt.AlignRight)
        self.lbl_l_mtime.setAlignment(Qt.AlignRight)
        self.lbl_r_mtime.setAlignment(Qt.AlignRight)

        self.lbl_a_permission.setAlignment(Qt.AlignRight)
        self.lbl_l_permission.setAlignment(Qt.AlignRight)
        self.lbl_r_permission.setAlignment(Qt.AlignRight)

        font = self.font()
        font.setFamily("courier")

        self.lbl_a_mtime.setFont(font)
        self.lbl_l_mtime.setFont(font)
        self.lbl_r_mtime.setFont(font)
        self.lbl_a_permission.setFont(font)
        self.lbl_l_permission.setFont(font)
        self.lbl_r_permission.setFont(font)

        row = 0

        row += 1
        self.layout.addWidget(QLabel("File Path"), row, 0, 1, 1)
        self.layout.addWidget(self.txt_local, row, 1, 1, 3)

        row += 1
        self.layout.addWidget(QLabel("Remote Path"), row, 0, 1, 1)
        self.layout.addWidget(self.txt_remote, row, 1, 1, 3)

        row += 1
        self.layout.addWidget(QLabel("Status"), row, 0, 1, 1)
        self.layout.addWidget(self.lbl_status, row, 1, 1, 1,
            Qt.AlignHCenter|Qt.AlignVCenter)
        self.layout.addWidget(self.lbl_status_image, row, 2, 1, 1,
            Qt.AlignHCenter|Qt.AlignVCenter)


        row += 1
        hline = QLabel(self)
        hline.setFrameStyle(QFrame.HLine | QFrame.Sunken)
        self.layout.addWidget(hline, row, 0, 1, 4)

        row += 1
        self.layout.addWidget(QLabel("Public URL"), row, 0, 1, 1)
        self.layout.addWidget(self.lbl_r_public, row, 1, 1, 3)

        row += 1
        self.layout.addWidget(self.btn_r_public_copy, row, 1, 1, 1)
        self.layout.addWidget(self.btn_r_public, row, 2, 1, 2)

        row += 1
        self.layout.addWidget(QLabel("Encryption Mode"), row, 0, 1, 1)
        self.layout.addWidget(self.lbl_r_encryption, row, 1, 1, 3)

        row += 1
        hline = QLabel(self)
        hline.setFrameStyle(QFrame.HLine | QFrame.Sunken)
        self.layout.addWidget(hline, row, 0, 1, 4)

        row += 1
        self.layout.addWidget(self.lbl_disk, row, 1, 1, 1)
        self.layout.addWidget(self.lbl_cache, row, 2, 1, 1)
        self.layout.addWidget(self.lbl_remote, row, 3, 1, 1)

        row += 1
        self.layout.addWidget(QLabel("Version"), row, 0, 1, 1)
        self.layout.addWidget(self.lbl_a_version, row, 1, 1, 1)
        self.layout.addWidget(self.lbl_l_version, row, 2, 1, 1)
        self.layout.addWidget(self.lbl_r_version, row, 3, 1, 1)

        row += 1
        self.layout.addWidget(QLabel("Size"), row, 0, 1, 1)
        self.layout.addWidget(self.lbl_a_size, row, 1, 1, 1)
        self.layout.addWidget(self.lbl_l_size, row, 2, 1, 1)
        self.layout.addWidget(self.lbl_r_size, row, 3, 1, 1)

        row += 1
        self.layout.addWidget(QLabel("Modified Time"), row, 0, 1, 1)
        self.layout.addWidget(self.lbl_a_mtime, row, 1, 1, 1)
        self.layout.addWidget(self.lbl_l_mtime, row, 2, 1, 1)
        self.layout.addWidget(self.lbl_r_mtime, row, 3, 1, 1)

        row += 1
        self.layout.addWidget(QLabel("Permission"), row, 0, 1, 1)
        self.layout.addWidget(self.lbl_a_permission, row, 1, 1, 1)
        self.layout.addWidget(self.lbl_l_permission, row, 2, 1, 1)
        self.layout.addWidget(self.lbl_r_permission, row, 3, 1, 1)

    def setEntry(self, ent, hostname=None):

        if isinstance(ent, sync.DirEnt):
            self.setDirEntry(ent, hostname)
        else:
            self.setFileEntry(ent, hostname)

    def setDirEntry(self, ent, hostname):

        self.txt_local.setText(ent.local_base)
        self.txt_remote.setText(ent.remote_base)

        # TODO: status should have an icon
        state = ent.state().split(":")[0]
        self.lbl_status_image.setPixmap(self.getStatePixmap(state))
        self.lbl_status.setText(state)

        df = {'size': 0, "permission": 0, "mtime": 0, "version": 0,
              "public": "", "encryption": ""}

        self.setAttrs(df, df, df)

    def setFileEntry(self, ent, hostname):
        self.txt_local.setText(ent.local_path)
        self.txt_remote.setText(ent.remote_path)

        # TODO: status should have an icon
        state = ent.state().split(":")[0]
        self.lbl_status_image.setPixmap(self.getStatePixmap(state))
        self.lbl_status.setText(state)

        df = {'size': 0, "permission": 0, "mtime": 0, "version": 0,
              "public": "", "encryption": ""}

        af = ent.af or df
        lf = ent.lf or df
        rf = ent.rf or df

        if hostname and rf['public']:
            public = "%s/p/%s" % (hostname, rf['public'])
            public = "<a href=\"%s\">%s</a>" % (public, rf['public'])
            self.lbl_r_public.setTextFormat(Qt.RichText)
            self.lbl_r_public.setOpenExternalLinks(True)
            self.lbl_r_public.setTextInteractionFlags(Qt.TextBrowserInteraction)
        else:
            public = "N/A"
            self.lbl_r_public.setTextFormat(Qt.RichText)
            self.lbl_r_public.setOpenExternalLinks(False)
            self.lbl_r_public.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.lbl_r_public.setText(public)

        self.setAttrs(af, lf, rf)

    def setAttrs(self, af, lf, rf):


        self.lbl_r_encryption.setText(rf['encryption'] or "none")

        self.lbl_a_version.setText(str(af['version']))
        self.lbl_l_version.setText(str(lf['version']))
        self.lbl_r_version.setText(str(rf['version']))

        self.lbl_a_size.setText(str(af['size']))
        self.lbl_l_size.setText(str(lf['size']))
        self.lbl_r_size.setText(str(rf['size']))

        default = "                   "

        self.lbl_a_mtime.setText(format_datetime(af['mtime']) or default)
        self.lbl_l_mtime.setText(format_datetime(lf['mtime']) or default)
        self.lbl_r_mtime.setText(format_datetime(rf['mtime']) or default)

        self.lbl_a_permission.setText(format_mode(af['permission']))
        self.lbl_l_permission.setText(format_mode(lf['permission']))
        self.lbl_r_permission.setText(format_mode(rf['permission']))



    def getStatePixmap(self, state):

        if state == sync.FileState.SAME:
            return QPixmap(":/img/fs_same.png")
        if state == sync.FileState.IGNORE:
            return QPixmap(":/img/fs_ignore.png")
        elif state == sync.FileState.PUSH:
            return QPixmap(":/img/fs_push.png")
        elif state == sync.FileState.PULL:
            return QPixmap(":/img/fs_pull.png")
        elif state == sync.FileState.CONFLICT_MODIFIED:
            return QPixmap(":/img/fs_conflict.png")
        elif state == sync.FileState.CONFLICT_CREATED:
            return QPixmap(":/img/fs_conflict.png")
        elif state == sync.FileState.CONFLICT_VERSION:
            return QPixmap(":/img/fs_conflict.png")
        elif state == sync.FileState.CONFLICT_TYPE:
            return QPixmap(":/img/fs_conflict.png")
        elif state == sync.FileState.DELETE_BOTH:
            return QPixmap(":/img/fs_delete.png")
        elif state == sync.FileState.DELETE_REMOTE:
            return QPixmap(":/img/fs_delete.png")
        elif state == sync.FileState.DELETE_LOCAL:
            return QPixmap(":/img/fs_delete_remote.png")
        return QPixmap(":/img/fs_delete_error.png")

class PasswordDialog(QDialog):

    def __init__(self, prompt, parent=None):
        super(PasswordDialog, self).__init__(parent)

        self.vbox = QVBoxLayout(self)
        self.hbox = QHBoxLayout()

        self.chk_password = QCheckBox("Hide Password", self)
        self.edit_password = QLineEdit(self)
        self.btn_accept = QPushButton("OK", self)
        self.btn_cancel = QPushButton("Cancel", self)

        self.hbox.addStretch(1)
        self.hbox.addWidget(self.btn_cancel)
        self.hbox.addWidget(self.btn_accept)

        self.vbox.addWidget(QLabel(prompt, self))
        self.vbox.addWidget(self.edit_password)
        self.vbox.addWidget(self.chk_password)
        self.vbox.addStretch(1)
        self.vbox.addLayout(self.hbox)

        self.chk_password.setChecked(True)
        self.edit_password.setEchoMode(QLineEdit.Password)

        self.chk_password.stateChanged.connect(self.onStateChanged)

        self.btn_accept.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

    def onStateChanged(self, state):

        if state == Qt.Checked:
            self.edit_password.setEchoMode(QLineEdit.Password)
        else:
            self.edit_password.setEchoMode(QLineEdit.Normal)

    def getPassword(self):
        return self.edit_password.text()

    @staticmethod
    def getPasswordKind(kind):
        prompt = "Enter %s password:" % kind
        dialog = PasswordDialog(prompt)
        if dialog.exec_() == QDialog.Accepted:
            return dialog.getPassword()
        return None

class PreferencesListView(ListView):
    def __init__(self, parent=None):
        super(PreferencesListView, self).__init__(parent)

        self.setNewData(["theme", "aws"])

class PreferencesDialog(QDialog):
    def __init__(self, cfg, parent=None):
        super(PreferencesDialog, self).__init__(parent)

        # list on the left hand side, displaying categories
        # stacked widget on the right displays the preferences to edit

        self.cfg = cfg

        self._init_layout()

        self.stack_sections.addWidget(QLabel("hello world"))

        self.updateFromConfig()

    def _init_layout(self):

        self.lst_sections = PreferencesListView(self)
        self.scroll_sections = QScrollArea(self)
        self.scroll_sections.setWidgetResizable(True)
        self.stack_sections = QStackedWidget(self)
        self.scroll_sections.setWidget(self.stack_sections)
        self.vbox = QVBoxLayout(self)
        self.hbox = QHBoxLayout()
        self.hbox.addWidget(self.lst_sections)
        self.hbox.addWidget(self.scroll_sections)
        self.vbox.addLayout(self.hbox)

    def updateFromConfig(self):
        pass

    def updateConfig(self):
        pass

class FavoritesPane(Pane):

    pushDirectoryMain = pyqtSignal(str)
    pushDirectorySecondary = pyqtSignal(str)

    def __init__(self, appCtxt, cfg, parent=None):
        super(FavoritesPane, self).__init__(parent)

        self.appCtxt = appCtxt
        self.cfg = cfg

        self.table_favorites = FavoritesListView(cfg, self)
        self.view_image = ImageView(self)

        self.calculator = Calculator(self)
        self.calendar = QCalendarWidget(self)
        self.calendar.hide()

        self.addWidget(self.table_favorites)
        self.addWidget(self.view_image)
        self.addWidget(self.calculator)
        self.addWidget(self.calendar)

        self._hidden_sections = set()

        self.onFavoritesChanged()

        self.table_favorites.pushDirectoryMain.connect(
            self.pushDirectoryMain)
        self.table_favorites.pushDirectorySecondary.connect(
            self.pushDirectorySecondary)

        self.table_favorites.toggleHiddenSection.connect(
            self.onToggleHiddenSection)

    def previewEntry(self, ent):

        if isinstance(ent, sync.FileEnt):
            self.view_image.setPath(ent.local_path)
        else:
            logging.info(f"cannot create preview for entry {ent}")
            self.view_image.setPath(None)


    def onFavoritesChanged(self):

        data = []
        g = lambda row: (row['section'], row['name'])
        section = None
        for row in sorted(self.cfg.favorites, key=g):
            if row['section'] != section:
                data.append([None, row['section'], None, True])
                section = row['section']

            if section in self._hidden_sections:
                continue

            icon = None
            kind = QFileIconProvider.Folder
            if 'icon' in row and isinstance(row['icon'], str):
                if hasattr(QFileIconProvider, row['icon']):
                    kind = getattr(QFileIconProvider, row['icon'])
                else:
                    temp = QIcon.fromTheme(row['icon'])
                    if not temp.isNull():
                        icon = temp.pixmap(22, 22).toImage()

            if icon is None:
                icon = self.appCtxt.getIcon(kind).scaled(22, 22, Qt.KeepAspectRatio, Qt.SmoothTransformation)

            data.append([icon, row['name'], row['path'], False])

        self.table_favorites.setNewData(data)

    def onToggleHiddenSection(self, section):

        if section in self._hidden_sections:
            self._hidden_sections.remove(section)
        else:
            self._hidden_sections.add(section)

        self.onFavoritesChanged()

    def toggleCalendar(self):
        if self.calendar.isHidden():
            self.calendar.show()
            self.calendar.setSelectedDate(QDate.currentDate())
            self.calculator.hide()
        else:
            self.calendar.hide()
            self.calculator.show()

class LocationPane(Pane):

    locationChanged = pyqtSignal(Pane, str)
    locationModified = pyqtSignal(Pane)
    previewEntry = pyqtSignal(object)
    splitInterface = pyqtSignal()
    submitBatchJob = pyqtSignal(object, list, object)

    def __init__(self, appCtxt, cfg, parent=None):
        super(LocationPane, self).__init__(parent)

        self.appCtxt = appCtxt
        self.ctxt = LocationContext(self.appCtxt)
        self.cfg = cfg

        self.setAcceptDrops(True)

        self.view_location = LocationView(self.ctxt, self)
        self.table_file = FileTableView(self.ctxt, self.cfg, self)
        #self.table_file.hide()
        self.grid_file = FileGridView(self.cfg, self)
        idx = self.table_file.baseModel().getColumnIndexByName("filename")
        self.grid_file.setModel(self.table_file.model())
        self.grid_file.setModelColumn(idx)
        self.grid_file.hide()

        self.spinner = OverlaySpinner(self.table_file)
        self.spinner.hide()

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(lambda: self.spinner.show())

        self.lbl_status_1 = QLabel(self) # display dir content info
        self.lbl_status_2 = QLabel(self) # display selection info
        self.lbl_status_3 = QLabel(self) # display address
        #self.lbl_status_1.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        #self.lbl_status_2.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        #self.lbl_status_3.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)

        self.lbl_status_1.setMinimumSize(1, 1)
        self.lbl_status_2.setMinimumSize(1, 1)
        self.lbl_status_3.setMinimumSize(1, 1)

        #self.lbl_status_1.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        #self.lbl_status_2.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        #self.lbl_status_3.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)


        #self.lbl_status_3.setFrameShape(QFrame.Box);
        #self.lbl_status_3.setFrameShadow(QFrame.Raised);

        self.hbox_status = QHBoxLayout()
        self.hbox_status.addWidget(self.lbl_status_1)
        self.hbox_status.addWidget(self.lbl_status_2)
        self.hbox_status.addWidget(self.lbl_status_3)
        self.hbox_status.addStretch(1)

        self.addWidget(self.view_location)
        self.addWidget(self.table_file)
        self.addWidget(self.grid_file)
        self.vbox.addLayout(self.hbox_status)

        self.table_file.locationChanged.connect(self.onTableLocationChanged)
        self.table_file.selectionChangedEvent.connect(self.onTableSelectionChanged)

        self.table_file.triggerSave.connect(self.onTriggerSave)
        self.table_file.triggerRestore.connect(self.onTriggerRestore)

        self.table_file.copyEntries.connect(self.onCopyEntries)
        self.table_file.moveEntries.connect(self.onMoveEntries)
        self.table_file.pasteEntries.connect(self.onPasteEntries)
        self.table_file.loadDetails.connect(self.onLoadDetails)
        self.table_file.openEntry.connect(self.onOpenEntry)
        self.table_file.copyUrls.connect(self.onCopyUrls)
        self.table_file.loadLocation.connect(self.onLoadLocation)

        # TODO: this could be reworked
        self.ctxt.locationChanging.connect(self.table_file.onLocationChanging)
        self.ctxt.locationChanged.connect(self.table_file.onLocationChanged)

        self.grid_file.openEntry.connect(self.onOpenEntry)

        self.ctxt.locationChanging.connect(self.onLocationChanging)
        self.ctxt.locationChanged.connect(self.onLocationChanged)
        self.ctxt.locationModified.connect(self.onLocationModified)

        self.view_location.loadLocation.connect(self.onLoadLocation)
        self.view_location.setFilterPattern.connect(self.table_file.onSetFilterPattern)
        self.view_location.splitInterface.connect(self.splitInterface)
        self.view_location.toggleDetailedView.connect(self.onToggleDetailedView)

    def setSplitIcon(self, bSplit):
        self.view_location.setSplitIcon(bSplit)

    def onTableLocationChanged(self, path, dcount, fcount):

        msg = []

        if fcount == 1:
            msg.append("1 file")
        elif fcount > 1:
            msg.append("%d files" % fcount)

        if dcount == 1:
            msg.append("1 directory")
        elif dcount > 1:
            msg.append("%d directories" % dcount)

        self.lbl_status_1.setText(" ".join(msg))

    def onTableSelectionChanged(self):

        count = self.table_file.getSelectionCount()

        msg = ""
        if count == 1:
            msg = "1 selected"
        elif count > 1:
            msg = "%d selected" % count

        self.lbl_status_2.setText(msg)

        if count == 1:
            ent = self.table_file.getSelection()[0][FileTableRowItem.COL_ENT]
            if isinstance(ent, sync.FileEnt) and self.ctxt.fs.islocal(ent.local_path):
                self.previewEntry.emit(ent)
            else:
                self.previewEntry.emit(None)

    def onTriggerSave(self):

        self.cfg.state = self.table_file.getColumnState()
        self.cfg.save()

    def onTriggerRestore(self):

        self.table_file.setColumnState(self.cfg.state)

    def onLocationChanging(self):
        trace("location change begin: start spinner")
        self.timer.start(333)

    def onOpenEntry(self, ent):

        if isinstance(ent, sync.DirEnt):
            # self.ctxt.pushChildDirectory(ent.name())
            self.onLoadLocation("child", ent.name())
        else:
            if self.ctxt.fs.islocal(ent.local_path):
                openAction(self.ctxt.fs, self.cfg.open_actions, self.ctxt.currentLocation(), ent)

    def onLocationChanged(self, directory, target):

        self.timer.stop()
        self.spinner.hide()

        if self.ctxt.hasActiveContext():
            ctxt = self.ctxt.activeContext()
            txt = "%s@%s" % (ctxt.username, ctxt.hostname)
            self.lbl_status_3.setText(txt)
        else:
            self.lbl_status_3.setText("")

        self.locationChanged.emit(self.parent(), directory)

    def onLocationModified(self):

        self.timer.stop()
        self.spinner.hide()

        self.table_file.refreshData()

        # self.table_file.
        self.table_file.setEnabled(True)

        self.locationModified.emit(self.parent())

    def showSplitButton(self, visible):
        self.view_location.showSplitButton(visible)

    def resetTableView(self):
        if not self.cfg.state:
            self.table_file.resetColumns()
        else:
            self.table_file.setColumnState(self.cfg.state)

    def onFirstShow(self):
        # on first enter
        QTimer.singleShot(0, self.resetTableView)

    def dragEnterEvent(self, event):

        if event.source() is self.table_file:
            event.ignore()
            return

        if event.mimeData().hasUrls():
            if event.possibleActions() & Qt.MoveAction:
                event.setDropAction(Qt.MoveAction)
                event.accept()
            else:
                event.acceptProposedAction()

    def dropEvent(self, event):

        dropAction = event.dropAction()&(Qt.MoveAction|Qt.CopyAction)
        if not dropAction:
            event.ignore()

        if event.mimeData().hasUrls():

            urls = []
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    urls.append(url.toLocalFile())
                else:
                    urls.append(url.url())
            event.accept()

            self.onCopyUrls(urls, dropAction)

    def onCopyEntries(self, entries):

        urls = []
        for item in entries:
            ent = item[FileTableRowItem.COL_ENT]
            if isinstance(ent, sync.DirEnt):
                path = ent.local_base
            else:
                path = ent.local_path
            if path:
                urls.append(QUrl(self.ctxt.fs.url(path)))

        trace("copy", urls)
        if urls:

            mimeData = QMimeData()

            # windows explorer hint for copy
            mimeData.setData("Preferred DropEffect", b'\x05\x00\x00\x00')
            mimeData.setUrls(urls)

            clipboard = QGuiApplication.clipboard();
            clipboard.setMimeData(mimeData)

    def onMoveEntries(self, entries):

        urls = []
        for ent in entries:
            if isinstance(ent, sync.DirEnt):
                path = ent.local_base
            else:
                path = ent.local_path
            if path:
                urls.append(QUrl(self.ctxt.fs.url(path)))

        if urls:

            mimeData = QMimeData()

            # windows explorer hint for move (cut)
            mimeData.setData("Preferred DropEffect", b'\x02\x00\x00\x00')
            mimeData.setUrls(urls)

            clipboard = QGuiApplication.clipboard();
            clipboard.setMimeData(mimeData)

    def onPasteEntries(self):

        clipboard = QGuiApplication.clipboard();
        mimeData = clipboard.mimeData()

        # trace(mimeData.formats())

        data = mimeData.data("Preferred DropEffect")

        dropAction = Qt.IgnoreAction
        if data == b'\x02\x00\x00\x00':
            dropAction = Qt.MoveAction
        elif data == b'\x05\x00\x00\x00':
            dropAction = Qt.CopyAction
        else:
            trace("unknown action:", data)
            return

        if mimeData.hasUrls():
            urls = []
            for url in mimeData.urls():
                if url.isLocalFile():
                    urls.append(url.toLocalFile())
                else:
                    urls.append(url.url())

            self.onCopyUrls(urls, dropAction)

    def onCopyUrls(self, urls, dropAction):

        # TODO: in order to not reload, get the list of new urls
        # in the currentLocation
        dialog = SyncProgressDialog()
        thread = CopyProgressThread(self.ctxt.fs, urls, self.ctxt.currentLocation(), dropAction, self)
        dialog.setThread(thread)
        dialog.exec_()
        # given this list of names, one could refresh only these files
        trace(thread._new_names)
        self.ctxt.reload()

    def onToggleDetailedView(self):


        idx = self.table_file.baseModel().getColumnIndexByName("filename")
        self.grid_file.setModelColumn(idx)

        if self.table_file.onToggleDetailedView():

            self.table_file.baseModel().getColumn(idx).setDecorationKey(FileTableRowItem.COL_ICON2)
            #self.table_file.baseModel().setGridMode(
            #    FileTableRowItem.COL_NAME, FileTableRowItem.COL_ICON2)
            self.table_file.hide()
            self.grid_file.show()

        else:
            self.table_file.baseModel().getColumn(idx).setDecorationKey(None)
            #self.table_file.baseModel().setGridMode(-1, -1)
            self.table_file.show()
            self.grid_file.hide()

    def onLoadLocation(self, mode, directory):

        #if mode == 'pop' and not self.ctxt.hasBackHistory():
        #    return

        # this tasks will fail
        if mode == 'unpop' and not self.ctxt.hasForwardHistory():
            return

        # emit before submitting the job
        self.ctxt.locationChanging.emit()

        # submit a single job
        self.submitBatchJob.emit(
            self.onLoadLocationTask,
            [(mode, directory)],
            self.onLoadLocationTaskComplete)

    def onLoadLocationTask(self, args):

        # if any exception is raised it is passed to
        # onLoadLocationTaskComplete, which can handle it

        mode, extra = args

        if mode == "push":
            # extra should be a directory path
            self.ctxt.pushDirectory(extra)
        elif mode == "child":
            # extra should be a directory path
            self.ctxt.pushChildDirectory(extra)  # actually a name, not dir
        elif mode == "reload":
            self.ctxt.reload()
        elif mode == "pop":
            self.ctxt.popDirectory()
        elif mode == "unpop":
            self.ctxt.unpopDirectory()
        elif mode == "push-parent":
            self.ctxt.pushParentDirectory()
        elif mode == "remove":
            # extra should be a list of rows
            self.ctxt.removeSelection(extra)
        else:
            raise Exception(f"unknown mode {mode} for {directory}")

    def onLoadLocationTaskComplete(self, result, ex):
        if ex is not None:
            self.ctxt.clearContext()

    def onLoadDetails(self, table, model):
        # start a thread which updates the model
        # replace the icon for image types with
        # a representation of that image

        # TODO: only a mild case of thread unsafe-ty
        seq = range(self.table_file.baseModel().rowCount(QModelIndex()))
        col = self.table_file.baseModel().getColumnIndexByName("icon")
        data = [table.baseModel().index(index, col) for index in seq]
        self.submitBatchJob.emit(self.onLoadDetailsTask, data, self.onLoadDetailsTaskComplete)

    def onLoadDetailsTask(self, index):

        row = index.data(RowValueRole)

        ent = row[FileTableRowItem.COL_ENT]

        size = self.cfg.iconSize

        if not isinstance(ent, sync.FileEnt):
            return None

        path = ent.local_path
        ftype = self.ctxt.fs.getFileType(path)

        if ftype == "GIF":
            try:
                frame = PIL.Image.open(path)
                frame = gif_extract_position(path)
                data = frame.tobytes("raw","RGBA")
                image = QImage(data, frame.size[0], frame.size[1], QImage.Format_RGBA8888)
                frame.close()

                image = scale_image(size, image)

                # https://gist.github.com/BigglesZX/4016539
                # example for correctly rendering frames

                #if frame.is_animated:
                #    skip = int(frame.n_frames * .75)
                #    for i in range(skip):
                #        frame.seek(frame.tell()+1)
                #        trace(skip, frame.tell())

                # image = frame.toqimage()
                #frame = frame.convert("RGBA")
                #data = frame.tobytes("raw","RGBA")
                #image = QImage(data, frame.size[0], frame.size[1], QImage.Format_RGBA8888)

                return(index, image)
            except Exception as e:
                trace(e)

        if ftype not in ['JPG', 'JPEG', 'BMP', 'PNG']:
            #info = QFileInfo(path)
            #icon = self.appCtxt._icon_provider.icon(info)
            #img = icon.pixmap(QSize(size, size)).toImage()
            #img = scale_image(size, img)
            return None
        else:
            img = QImage(path)
            img = scale_image(size, img)
        return (index, img)

    def onLoadDetailsTaskComplete(self, result, ex):

        if result is None:
            return

        index, img = result

        item = index.data(RowValueRole)

        # item = FileTableRowItem.fromEntry(self.ctxt, ent)
        #trace(index, img.width(), img.height())
        # consider replace whole row to fix visual issue
        #self.table_file.model().setData(index, img)

        item[FileTableRowItem.COL_ICON2] = img
        self.table_file.replaceRow(index.row(), item)

class DoubleLocationPane(QWidget):

    def __init__(self, appCtxt, cfg, parent=None):
        super(DoubleLocationPane, self).__init__(parent)

        self.primary = LocationPane(appCtxt, cfg, self)
        self.secondary = LocationPane(appCtxt, cfg, self)
        self.secondary.hide()

        self.primary.setSplitIcon(True)
        self.secondary.setSplitIcon(False)

        self.hbox = QHBoxLayout(self)

        self.hbox.addWidget(self.primary)
        self.hbox.addWidget(self.secondary)

        self.primary.splitInterface.connect(self.onShowSecondary)
        self.secondary.splitInterface.connect(self.onHideSecondary)

    def showSecondary(self, show):

        if show:
            self.onShowSecondary()
        else:
            self.onHideSecondary()

    def onShowSecondary(self):
        self.secondary.show()
        self.primary.showSplitButton(False)

    def onHideSecondary(self):
        self.secondary.hide()
        self.primary.showSplitButton(True)

    def setPrimaryDirectory(self, path):
        self.primary.ctxt.pushDirectory(path)

    def setSecondaryDirectory(self, path):
        self.secondary.ctxt.pushDirectory(path)

class EventFilter(QObject):

    def __init__(self, parent=None):
        super().__init__(parent)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.ActivationChange:
            self.parent().onFocusChanged(self.parent().isActiveWindow())
        return super().eventFilter(obj, event)

class ConditionVariable(QObject):
    def __init__(self):
        super(ConditionVariable, self).__init__()

        self.lk = QMutex()
        self.cv = QWaitCondition()

    def __enter__(self):
        self.lk.lock()
        return self

    def __exit__(self, *args):
        self.lk.unlock()

    def wait(self):
        self.cv.wait(self.lk)

    def notify_all(self):
        self.cv.wakeAll()

class _TaskThread(QThread):

    def __init__(self, parent):
        super(_TaskThread, self).__init__(parent)

        self._cv = parent._cv

        self._alive = True

    def run(self):

        tid = None
        op = None
        while self._alive:
            with self._cv:
                tid, op = self.main()

            if op is not None:
                retval = self.execute(*op)

                with self._cv:
                    self.delete(tid, retval)

    def main(self):

        while len(self.parent()._queue) == 0 and self._alive:
            self._cv.wait()

        if len(self.parent()._queue) > 0:

            tid = self.parent()._queue.pop()
            op = self.parent()._tasks[tid]

            return tid, op

        return None, None

    def execute(self, fn, args, kwargs):

        try:
            return fn(*args, **kwargs), None, time.time()
        except Exception as e:
            return None, e, time.time()

    def delete(self, tid, retval):
        del self.parent()._tasks[tid]
        retval, e, time = retval
        self.parent().taskFinished.emit(tid, retval, e, time)
        self._cv.notify_all()

    def join(self):
        self._alive = False
        with self._cv:
            self._cv.notify_all()

        self.wait()

class TaskQueue(QObject):

    taskFinished = pyqtSignal(str, object, object, float)

    def __init__(self, size, parent=None):
        super(TaskQueue, self).__init__(parent)

        self._cv = ConditionVariable()

        self._queue = []
        self._tasks = {}
        self._threads = []

        for i in range(size):
            t = _TaskThread(self)
            t.start()
            self._threads.append(t)

    def submit(self, fn, *args, **kwargs):

        tid = str(uuid.uuid4())

        if len(self._threads) == 0:
            self._execute(tid, fn, args, kwargs)
            return tid

        with self._cv:

            self._tasks[tid] = (fn, args, kwargs)
            self._queue.append(tid)
            self._cv.notify_all()

        return tid

    def submit_batch(self, fn, arglist):

        tids = []
        with self._cv:

            for args in arglist:
                tid = str(uuid.uuid4())
                self._tasks[tid] = (fn, args, {})
                self._queue.append(tid)
                tids.append(tid)

            self._cv.notify_all()

        return tids

    def reset_and_submit_batch(self, fn, arglist):

        tids = []
        with self._cv:

            for tid in self._queue:
                del self._tasks[tid]
            self._queue = []

            for args in arglist:
                tid = str(uuid.uuid4())
                self._tasks[tid] = (fn, args, {})
                self._queue.append(tid)
                tids.append(tid)

            self._cv.notify_all()
        return tids

    def _execute(self, tid, fn, args, kwargs):

        with self.cv_tasks:
            try:
                retval = (fn(*args, **kwargs), None, time.time())
            except Exception as e:
                retval = (None, e, time.time())

        self.taskFinished.emit(tid, *retval)

    def join(self):
        for i, thread in enumerate(self._threads):
            trace("stopping thread %d" % i)
            thread.join()

class RpcThread(QThread):

    message_recieved = pyqtSignal(object)

    def __init__(self, host=None, port=0, parent=None):
        super(RpcThread, self).__init__(parent)

        self.host = host or 'localhost'
        self.port = 0 if port <= 0 else port

        self.alive = True
        self.sock = None

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:

            self.sock.bind((self.host, self.port))
            self.sock.listen(1)
            self.sock.settimeout(.5)
        except OSError:
            sys.stderr.write("unable to bind socket %s:%d\n"%(self.host, self.port))
            self.alive = False

    def run(self):

        while self.alive:
            try:
                conn, addr = self.sock.accept()

                self.handleConnection(conn, addr)

            except socket.timeout as e:
                pass
            except Exception as e:
                trace(type(e), e)
                self.sock.close()
                self.sock = None
                break
        sys.stderr.write("Remote Socket Thread has ended.\n")

    def handleConnection(self, conn, addr):
        dat = conn.recv(5)
        version, size = struct.unpack("<bI", dat)

        # drop connections with large amounts of data
        if size > 10240:
            trace(dat)
            trace("error: size")
            conn.close()
            return

        data = conn.recv(size)

        msg = RpcMessage.decode(data)

        self.message_recieved.emit(msg)

        conn.close()

    def join(self):
        self.alive = False
        if self.sock is not None:
            self.sock.close()
        trace("closing socket\n")
        self.wait()

class RpcOpenTabMessage(object):
    type = 1

    def __init__(self, paths):
        super(RpcOpenTabMessage, self).__init__()
        self.paths = paths

    def encode(self):
        msg = b'\x00'.join([p.encode("utf-8") for p in self.paths])
        return msg

    @staticmethod
    def decode(data):
        paths = [p.decode('utf-8') for p in data.split(b'\x00')]
        trace('decode', paths)
        return RpcOpenTabMessage(paths)

class RpcMessage(object):

    types = {
        RpcOpenTabMessage.type: RpcOpenTabMessage,
    }

    @staticmethod
    def encode(rpcMsg):
        type = struct.pack("<I", rpcMsg.type)
        return type + rpcMsg.encode()

    @staticmethod
    def decode(data):
        type, = struct.unpack("<I", data[:4])
        return RpcMessage.types[type].decode(data[4:])

    @staticmethod
    def send(host, port, packet):
        packet = struct.pack('<bI', 1, len(packet)) + packet
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        trace(host, port)
        sock.connect((host, port))
        trace("sent", sock.send(packet))
        sock.close()

def _exec_task(fn, arg, cbk):

    try:
        result = fn(arg)
    except Exception as e:
        return cbk, None, e

    return cbk, result, None

class SyncMainWindow(QMainWindow):

    def __init__(self, cfg, procinfo=None):
        super(SyncMainWindow, self).__init__()

        # useful for debugging layouts
        # self.setStyleSheet("QWidget {border: 1px solid red}")

        self.cfg = cfg
        self._procinfo_path = procinfo

        self.initMenuBar()
        self.initStatusBar()

        self.appCtxt = AppContext(self.cfg)

        self.btn_newTab = QToolButton(self)
        self.btn_newTab.clicked.connect(self.newTab)
        self.btn_newTab.setIcon(self.style().standardIcon(QStyle.SP_FileDialogNewFolder))

        self.tabview = TabWidget(self)
        self.tabview.tabBar().setMovable(True)
        self.tabview.setCornerWidget(self.btn_newTab)
        self.tabview.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tabview.tabBar().setUsesScrollButtons(True)
        self.tabview.tabBar().setElideMode(Qt.ElideNone)
        self.tabview.tabCloseRequested.connect(self.onTabCloseRequest)

        self.pane_favorites = FavoritesPane(self.appCtxt, cfg, self)

        self.pane_favorites.pushDirectoryMain.connect(
            self.onPushDirectory)
        self.pane_favorites.pushDirectorySecondary.connect(
            self.onPushSecondaryDirectory)

        self.splitter = QSplitter(self)
        self.splitter.addWidget(self.pane_favorites)
        self.splitter.addWidget(self.tabview)

        self.setCentralWidget(self.splitter)

        self.installEventFilter(EventFilter(self))

        self._rpc_msg_count = 0
        self.rpc_thread = RpcThread('0.0.0.0', 20123, self)
        self.rpc_thread.message_recieved.connect(self.onRpcMessage)
        self.rpc_thread.started.connect(self.onRpcStarted)
        self.rpc_thread.finished.connect(self.onRpcFailed)
        if self._procinfo_path is not None:
            self.rpc_thread.connect()
            self.rpc_thread.start()

        self.task_queue = TaskQueue(4)
        self.task_queue.taskFinished.connect(self.onTaskFinished)

    def initMenuBar(self):

        menubar = self.menuBar()

        self.file_menu = menubar.addMenu("File")
        self.file_menu.addSeparator()
        self.file_menu.addAction("Exit")

    def initStatusBar(self):

        statusbar = self.statusBar()

        self.calendar = Calendar(self)
        statusbar.addWidget(self.calendar)
        self.calendar.clicked.connect(self.onToggleCalendar)

        self.clock = Clock(self)
        statusbar.addWidget(self.clock)

        self.lbl_rpc = QLabel(self)
        statusbar.addWidget(self.lbl_rpc)

    def showWindow(self):

        geometry = QDesktopWidget().screenGeometry()
        sw = geometry.width()
        sh = geometry.height()
        # calculate default values
        dw = int(sw * .6)
        dh = int(sh * .6)
        dx = sw // 2 - dw // 2
        dy = sh // 2 - dh // 2
        # use stored values if they exist
        cw = 0  # s.getDefault("window_width",dw)
        ch = 0  # s.getDefault("window_height",dh)
        cx = -1  # s.getDefault("window_x",dx)
        cy = -1  # s.getDefault("window_y",dy)
        # the application should start wholly on the screen
        # otherwise, default its position to the center of the screen
        if cx < 0 or cx + cw > sw:
            cx = dx
            cw = dw
        if cy < 0 or cy + ch > sh:
            cy = dy
            ch = dh
        if cw <= 0:
            cw = dw
        if ch <= 0:
            ch = dh
        self.resize(cw, ch)
        self.move(cx, cy)
        self.show()

        # self.table_file.setState(self.cfg.state)

        # somewhat arbitrary
        # set the width of the quick access view to something
        # reasonable
        lw = 200
        if cw > lw * 2:
            self.splitter.setSizes([lw, cw - lw])

        # TODO: fix for multi tab views
        # run this function immediately after the event loop starts
        #

    def onToggleCalendar(self):
        self.pane_favorites.toggleCalendar()

    def onTabCloseRequest(self, idx):

        if 0 <= idx < self.tabview.count():
            self.tabview.removeTab(idx)
            self.tabview.setTabsClosable(self.tabview.count()>1)

    def newTab(self):
        path = os.path.join(os.getcwd(), "playground")
        if os.path.exists(path):
            self.addTab(path, path, None)
        else:
            self.addTab(os.getcwd(), os.getcwd(), None)

    def addTab(self, primaryPath, secondaryPath, icon=None):

        if icon is None:
            icon = self.appCtxt._icon_provider.icon(QFileIconProvider.Folder)

        pane = DoubleLocationPane(self.appCtxt, self.cfg, self)

        pane.primary.previewEntry.connect(self.onPreviewEntry)
        pane.secondary.previewEntry.connect(self.onPreviewEntry)
        pane.primary.locationChanged.connect(self.onDirectoryChanged)
        pane.primary.submitBatchJob.connect(self.submitBatch)
        pane.secondary.submitBatchJob.connect(self.submitBatch)

        self.tabview.addTab(pane, icon, "")

        self.tabview.setTabsClosable(self.tabview.count()>1)

        self.tabview.setCurrentWidget(pane)

        try:
            # TODO: error if path does not exists...
            pane.setPrimaryDirectory(primaryPath)
            pane.setSecondaryDirectory(secondaryPath)
        except Exception as e:
            pass

    def onDirectoryChanged(self, pane, path):

        index = self.tabview.indexOf(pane)
        _, name = self.appCtxt.fs.split(path)
        if name:
            self.tabview.setTabText(index, name)
        else:
            self.tabview.setTabText(index, "root")

    def onPushDirectory(self, path):
        w = self.tabview.currentWidget()
        w.setPrimaryDirectory(path)

    def onPushSecondaryDirectory(self, path):
        w = self.tabview.currentWidget()
        w.setSecondaryDirectory(path)
        w.showSecondary(True)

    def onFocusChanged(self, focus):

        self.calendar.setEnabled(focus)
        self.clock.setEnabled(focus)

    def onAboutToQuit(self):

        self.hide()

        if self._procinfo_path and os.path.exists(self._procinfo_path):
            os.remove(self._procinfo_path)

        self.rpc_thread.join()

        self.task_queue.join()

    def focusWindow(self):
        # todo: platform dependent options

        if has_win32gui:

            # https://forum.qt.io/topic/1939/activatewindow-does-not-send-window-to-front/5

            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_SHOWWINDOW = 0x0040

            HWND_TOPMOST = -1
            HWND_NOTOPMOST = -2
            win32gui.SetWindowPos(self.effectiveWinId(),
                HWND_TOPMOST, 0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
            win32gui.SetWindowPos(self.effectiveWinId(),
                HWND_NOTOPMOST, 0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)

        self.setFocus()
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def onRpcMessage(self, msg):
        trace(msg.encode())

        self._rpc_msg_count += 1

        self.focusWindow()

        if isinstance(msg, RpcOpenTabMessage):
            for path in msg.paths:
                if path:
                    self.addTab(path, "")

        self.lbl_rpc.setText("RPC: 20123 (%d)" % self._rpc_msg_count)

    def onRpcStarted(self):
        self.lbl_rpc.setText("RPC: 20123")

    def onRpcFailed(self):
        self.yue
        lbl_rpc.setText("RPC: failed")

    def onPreviewEntry(self, ent):
        if ent is None:
            self.pane_favorites.previewEntry(None)

        else:
            # todo: add job cancel, or tasg to reject completed jobs
            # quickly browsing over two files in a row can
            # have results resolve out of order
            self.submitTask(ImageView.loadPath, ent.local_path, self.onPreviewEntryLoadComplete)

    def onPreviewEntryLoadComplete(self, image, e):

        self.pane_favorites.view_image.setImage(image)

    def submitTask(self, fn, arg, cbk):

        self.task_queue.submit(_exec_task, fn, arg, cbk)

    def submitBatch(self, fn, arglist, cbk):

        args = [(fn, arg, cbk) for arg in arglist]
        self.task_queue.submit_batch(_exec_task, args)

    def onTaskFinished(self, tid, retval, e, time):

        cbk, result, e = retval
        if e:
            trace("task %s: %s" % (tid, e))
        cbk(result, e)

    def resizeEvent(self, event):

        visible = self.width() > 450
        isVisible = self.pane_favorites.isVisible()

        if visible != isVisible:
            self.pane_favorites.setVisible(visible)

def setDarkTheme(app):

    palette = QPalette()

    white = QColor(215, 215, 215)
    text = white

    black = QColor(15, 15, 15)
    invertText = black

    highlight = QColor(100, 100, 220)
    window = QColor(55, 49, 49)
    base = QColor(30, 35, 40)
    altbase = QColor(45, 50, 60)


    palette.setColor(QPalette.Window, window)
    palette.setColor(QPalette.WindowText, text)
    palette.setColor(QPalette.Base, base)
    palette.setColor(QPalette.AlternateBase, altbase)
    palette.setColor(QPalette.ToolTipBase, text)
    palette.setColor(QPalette.ToolTipText, text)
    # palette.setColor(QPalette.PlaceholderText, white) Qt 5.12
    palette.setColor(QPalette.Text, text)
    palette.setColor(QPalette.Button, window)
    palette.setColor(QPalette.ButtonText, text)
    palette.setColor(QPalette.BrightText, text)

    palette.setColor(QPalette.Active,  QPalette.Highlight, highlight)
    palette.setColor(QPalette.Inactive,QPalette.Highlight, invertText)
    palette.setColor(QPalette.Disabled,QPalette.Highlight, invertText)
    palette.setColor(QPalette.Active,  QPalette.HighlightedText, invertText)
    palette.setColor(QPalette.Inactive,QPalette.HighlightedText, text)
    palette.setColor(QPalette.Disabled,QPalette.HighlightedText, text)
    app.setPalette(palette)

    #font = app.font()
    #font.setPointSize(10)
    #app.setFont(font)

    return

def main():

    print("%.3f : main" % (time.time()))
    if sys.stderr is None or sys.stdout is None:
        class dummy_writer(object):
            def write(self, *args, **kwargs):
                pass
        sys.stderr = dummy_writer()
        sys.stdout = dummy_writer()

    cfg_path = os.path.join(cfg_base, "yue-sync", "settings.yml")

    procinfo = os.path.join(cfg_base, "yue-sync", ".pid")

    # load the config, or create a new one if it does not exist
    save = not os.path.exists(cfg_path)
    cfg = SyncConfig(cfg_path)
    if save:
        cfg.save()

    print("%.3f : argparse" % (time.time()))

    parser = argparse.ArgumentParser(
        description='',
        epilog='')

    parser.add_argument("--pwd", type=str, default=None,
        help='open a file')

    # some platforms send this as an option
    parser.add_argument("-p", type=str, default='', nargs=1,
        help='open a file')

    group_ex = parser.add_mutually_exclusive_group()

    group_ex.add_argument("-n", '--new', action='store_true',
        help='open a file')

    group_ex.add_argument("-e", dest='edit', type=str, default=None, nargs=1,
        help='open a file')

    group_ex.add_argument('--cfg', dest='cfg', action='store_true',
        help='open configuration')

    if cfg.diff_action.get('action', None):
        group_ex.add_argument("-d", dest='diff', type=str, default=None, nargs=2,
            help='open a file')

    parser.add_argument("paths", type=str, default=None, nargs='*',
        help='open a file')

    print("%.3f : parse args" % (time.time()))

    args = parser.parse_args()

    if args.edit:
        ent = sync.FileEnt(None, args.edit[0], None, None, None)
        openAction(self.ctxt.fs, cfg.open_actions, os.getcwd(), ent)
        return

    if args.cfg:
        app = QApplication(sys.argv)
        window = PreferencesDialog()
        window.show()
        sys.exit(app.exec_())

    if args.diff:
        trace(args)
        return

    print("%.3f : rpc init" % (time.time()))

    if not args.new and os.path.exists(procinfo):
        paths = []
        if args.pwd:
            os.chdir(args.pwd)

        for path in args.paths:
            # expand vars using THIS shell env, pass to the open window
            path = os.path.expanduser(path)
            path = os.path.expandvars(path)
            paths.append(os.path.abspath(path))
        trace(paths)
        msg  = RpcOpenTabMessage(paths)
        try:
            RpcMessage.send('0.0.0.0', 20123, RpcMessage.encode(msg))
            return
        except OSError as e:
            trace(e)
            pass
        except ConnectionRefusedError as e:
            trace(e)
            # assume window closed and open a new one
            pass

    print("%.3f : rpc init end" % (time.time()))

    if args.new:
        # clear this variable, this process does not have a pid file
        procinfo = None

    for bucket in cfg.buckets:

        s3fs = BotoFileSystemImpl(
            bucket['endpoint'],
            bucket['region'],
            bucket['access_key'],
            bucket['secret_key']
        )

        scheme = BotoFileSystemImpl.scheme
        if 'scheme' in bucket:
            scheme = bucket['scheme']
            s3fs.scheme = scheme

        trace(scheme, bucket)
        FileSystem.register(scheme, s3fs)

    print("%.3f : application" % (time.time()))

    app = QApplication(sys.argv)
    app.setApplicationName("Yue-Sync")
    trace(QStyleFactory.keys())
    app.setStyle("Fusion")
    # app.setStyle("windowsvista")
    # setDarkTheme(app)

    QIcon.setThemeName("tango")

    app.setQuitOnLastWindowClosed(True)
    app_icon = QIcon(':/img/icon.png')
    app.setWindowIcon(app_icon)

    if not PYQT_V6:
        QGuiApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    installExceptionHook()

    print("%.3f : main window" % (time.time()))

    window = SyncMainWindow(cfg, procinfo=procinfo)
    window.showWindow()

    trace("startup time: %f" % (time.time() - ts_start))

    app.aboutToQuit.connect(window.onAboutToQuit)

    if procinfo is not None:
        with open(procinfo, "w") as wf:
            wf.write("%s\n" % os.getpid())

    if args.paths:
        if len(args.paths) % 2 == 1:
            args.paths.append(".")

        for i in range(0, len(args.paths), 2):
            window.addTab(args.paths[i], args.paths[i])

    else:

        window.newTab()

    sys.exit(app.exec_())

def wmain():
    try:
        main()
    except BaseException as e:
        # log application startup errors

        error_log_path = os.path.join(cfg_base, 'yue-sync', 'error.log')
        print(error_log_path)
        print(e)
        with open(error_log_path, "w") as wf:
            wf.write("\n\n")
            wf.write(" ".join(sys.argv))
            wf.write("\n\n")
            wf.write(os.getcwd())
            wf.write("\n\n")
            lines = traceback.format_exception(*sys.exc_info())
            for line in lines:
                wf.write(line)
            wf.write('%s' % e)

        sys.exit(1)
    sys.exit(0)

if __name__ == '__main__':
    errf.write("main\n");
    errf.flush()
    wmain()


