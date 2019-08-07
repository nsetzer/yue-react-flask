#! cd ../.. && python3 -m yueserver.tools.syncui

# remove
# move
# cut/copy/paste
# create directory
# create empty file
# drag and drop mime types
# directory load robustness
#   gracefully handle errors during load()
#   empty string as root directory on windows, show available drives
# 'open as' behavior
# s3 file paths
# recursive status needs to set a dirty bit on directories
#   cleared when recursive sync

import os
import sys
import time
import math
import logging
import posixpath

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yueserver.dao.filesys.filesys import FileSystem
from yueserver.qtcommon.TableView import (
    TableError, TableModel, TableView, RowValueRole, ImageDelegate,
    SortProxyModel, RowSortValueRole, ListView, EditItemDelegate
)
from yueserver.qtcommon.exceptions import installExceptionHook
from yueserver.qtcommon import resource
from yueserver.framework.config import BaseConfig, yload, ydump

from yueserver.tools import sync2

def openNative(url):

    if os.name == "nt":
        os.startfile(url)
    elif sys.platform == "darwin":
        os.system("open %s" % url)
    else:
        # could also use kde-open, gnome-open etc
        # TODO: implement code that tries each one until one works
        # subprocess.call(["xdg-open",filepath])
        sys.stderr.write("open unsupported on %s" % os.name)

def isSubPath(dir_path, file_path):
    return os.path.abspath(file_path).startswith(os.path.abspath(dir_path) + os.sep)

def getFileType(path):
    _, name = os.path.split(path)

    if name.startswith("."):
        return "DOT FILE"

    if '.' not in name:
        return "FILE"

    name, ext = os.path.splitext(name)

    if not ext:
        return "FILE"

    return ext.lstrip(".").upper()

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

        yield sync2.FileEnt(dent.remote_base, dent.local_base, None, None, None)
        yield sync2.SyncResult(dent, sync2.FileState.ERROR, dent.remote_base)

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

    def save(self):

        obj = {
            "favorites": self.favorites,
            "state": self.state
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

class SyncUiContext(QObject):

    # 3 signals to capture the start of a directory change,
    # then periodic updates as files become available
    # then a final signal to indicate the process is complete
    locationChanging = pyqtSignal()
    locationUpdate = pyqtSignal(str)  # directory
    locationChanged = pyqtSignal(str)  # directory

    loadContextSuccess = pyqtSignal(str)  # directory
    loadContextError = pyqtSignal(str, str)  # directory, reason

    contextOpened = pyqtSignal(str)  # cfgdir

    def __init__(self):
        super(SyncUiContext, self).__init__()

        self.fs = FileSystem()

        self._location = ""
        self._location_history = []
        self._location_pop_history = []
        self._dir_contents = []
        self._syncContext = {}
        self._activeContext = None

        self._icon_provider = QFileIconProvider()
        self._icon_ext = {}

        self._paste_entries = None
        self._paste_action = 0

    def load(self, directory):

        self.locationChanging.emit()

        QApplication.processEvents()

        try:
            ctxt = self._load_get_context(directory)

            if ctxt is not None:
                content = self._load_context(ctxt, directory)
            else:
                content = self._load_default(directory)

            # useful for color testing
            # for state in sync2.FileState.states():
            #    content.append(sync2.DirEnt(state, state, state, state))

            self._active_context = ctxt
            self._dir_contents = content
            self._location = directory
            self.locationChanged.emit(directory)
        except Exception as e:
            print("error changing directory")
            logging.exception(str(e))

    def _load_get_context(self, directory):
        for local_base, ctxt in self._syncContext.items():
            if isSubPath(local_base, directory):
                return ctxt
        else:
            return self.loadSyncContext(directory)
        return None

    def _load_context(self, ctxt, directory):
        abspath, relpath = ctxt.normPath(directory)
        result = sync2._check(ctxt, relpath, abspath)

        _dir_contents = result.dirs + result.files
        return _dir_contents

    def _load_default(self, directory):

        _dir_contents = []
        for name in os.listdir(directory):
            fullpath = os.path.join(directory, name)

            try:
                try:
                    record = self.fs.file_info(fullpath)
                except OSError as e:
                    ent = sync2.DirEnt(name, None, fullpath)
                    _dir_contents.append(ent)
                    continue

                if not record.isDir:

                    af = {
                        "version": record.version,
                        "size": record.size,
                        "mtime": record.mtime,
                        "permission": record.permission,
                    }

                    ent = sync2.FileEnt(None, fullpath, None, None, af)
                    ent._state = sync2.FileState.SAME
                    _dir_contents.append(ent)
                else:
                    ent = sync2.DirEnt(name, None, fullpath)
                    _dir_contents.append(ent)

            except FileNotFoundError:
                pass
        return _dir_contents

    def reload(self):
        self.load(self._location)

    def pushDirectory(self, directory):

        self.load(directory)
        self._location_history.append(directory)
        self._location_pop_history = []

    def pushChildDirectory(self, dirname):

        directory = os.path.join(self._location, dirname)

        # TODO: test access

        # note buttons are enabled based on if there is history
        # but a failed load should not effect state
        self._location_history.append(directory)
        self._location_pop_history = []

        self.load(directory)

    def pushParentDirectory(self):
        directory, _ = os.path.split(self._location)

        # TODO: test access

        # note buttons are enabled based on if there is history
        # but a failed load should not effect state
        self._location_history.append(directory)
        self._location_pop_history = []

        self.load(directory)

    def popDirectory(self):

        if len(self._location_history) <= 1:
            return

        # TODO: test access

        # note buttons are enabled based on if there is history
        # but a failed load should not effect state
        directory = self._location_history[-2]
        self._location_pop_history.append(self._location_history.pop())

        self.load(directory)

    def unpopDirectory(self):

        if len(self._location_pop_history) < 1:
            return

        directory = self._location_pop_history.pop(0)
        self._location_history.append(directory)
        self.load(directory)

    def hasBackHistory(self):
        return len(self._location_history) > 0

    def hasForwardHistory(self):
        return len(self._location_pop_history) > 0

    def hasActiveContext(self):
        return self._active_context is not None

    def activeContext(self):
        return self._active_context

    def contents(self):
        return self._dir_contents

    def currentLocation(self):
        return self._location

    def loadSyncContext(self, directory):

        # this duplicates the logic from get_ctxt
        try:
            userdata = sync2.get_cfg(directory)

        except sync2.SyncException as e:
            return None

        try:
            db_path = os.path.join(
                userdata['local_base'], ".yue", "database.sqlite")

            db = sync2.db_connect("sqlite:///" + db_path)

            client = sync2.connect(userdata['hostname'],
                userdata['username'], userdata['password'])

            storageDao = sync2.LocalStorageDao(db, db.tables)

            ctxt = sync2.SyncContext(client, storageDao, self.fs,
                userdata['root'], userdata['remote_base'], userdata['local_base'])

            # replace the get password implementation
            ctxt.getPassword = self.getEncryptionPassword

            ctxt.current_local_base = userdata['current_local_base']
            ctxt.current_remote_base = userdata['current_remote_base']
            ctxt.hostname = userdata['hostname']

        except sync2.SyncException as e:
            self.loadContextError.emit(directory, str(e))
            print(str(e))
            return None

        except Exception as e:
            self.loadContextError.emit(directory, str(e))
            print(str(e))
            return None

        else:

            local_base = userdata['local_base']
            self._syncContext[local_base] = ctxt
            self.contextOpened.emit(local_base)

            return ctxt

    def getIcon(self, kind):
        """
        https://doc.qt.io/qt-5/qfileiconprovider.html


        """
        if kind in self._icon_ext:
            return self._icon_ext[kind]

        icon = self._icon_provider.icon(kind)
        image = icon.pixmap(QSize(32, 32)).toImage()
        self._icon_ext[kind] = image
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
            print("error loading image for ", state)
        return image

    def _getFileStateIcon(self, state):

        if state == sync2.FileState.SAME:
            # return self.getImage(":img/fs_same.png")
            return None

        elif state == sync2.FileState.PUSH:
            return self.getImage(":/img/fs_push.png")

        elif state == sync2.FileState.PULL:
            return self.getImage(":/img/fs_pull.png")

        elif state == sync2.FileState.CONFLICT_MODIFIED:
            return self.getImage(":/img/fs_conflict.png")

        elif state == sync2.FileState.CONFLICT_CREATED:
            return self.getImage(":/img/fs_conflict.png")

        elif state == sync2.FileState.CONFLICT_VERSION:
            return self.getImage(":/img/fs_conflict.png")

        elif state == sync2.FileState.CONFLICT_TYPE:
            return self.getImage(":/img/fs_conflict.png")

        elif state == sync2.FileState.DELETE_BOTH:
            return self.getImage(":/img/fs_delete.png")

        elif state == sync2.FileState.DELETE_REMOTE:
            return self.getImage(":/img/fs_delete.png")

        elif state == sync2.FileState.DELETE_LOCAL:
            return self.getImage(":/img/fs_delete_remote.png")

        # state == sync2.FileState.ERROR:
        return self.getImage(":/img/fs_delete_error.png")

    def getFileIcon(self, path):

        _, ext = os.path.splitext(path)
        if ext and ext in self._icon_ext:
            return self._icon_ext[ext]

        info = QFileInfo(path)
        icon = self._icon_provider.icon(info)
        image = icon.pixmap(QSize(32, 32)).toImage()
        self._icon_ext[ext] = image
        return image

    def setCutData(self, entries):
        self._paste_entries = entries
        self._paste_action = 1

    def setCopyData(self, entries):
        self._paste_entries = entries
        self._paste_action = 2

    def pasteData(self):
        return (self._paste_action, self._paste_entries)

    def clearPasteData(self):
        self._paste_entries = None
        self._paste_action = 0

    def getEncryptionPassword(self, kind):

        prompt = "Enter %s password:" % kind
        dialog = PasswordDialog(prompt)
        if dialog.exec_() == QDialog.Accepted:
            return dialog.getPassword()

        return None

    def renameEntry(self, ent, name):

        if isinstance(ent, sync2.DirEnt):
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

        print("***", local_path, "=>", new_local_path)

        if local_path == new_local_path:
            return None

        os.rename(local_path, new_local_path)

        if remote_path:
            fpath, fname = posixpath.split(remote_path)
            new_remote_path = posixpath.join(fpath, name)
        else:
            new_remote_path = remote_path

        print("***", remote_path, "=>", new_remote_path)

        if isinstance(ent, sync2.DirEnt):
            new_ent = sync2.DirEnt(name, new_remote_path, new_local_path)

        elif not self.hasActiveContext():
            new_ent = sync2.FileEnt(None, new_local_path, None, None, af)
            new_ent._state = sync2.FileState.SAME

        else:
            new_ent = sync2._check_file(
                self.activeContext(), remote_path, local_path)

        return new_ent

class Pane(QWidget):
    """docstring for Pane"""

    def __init__(self, parent):
        super(Pane, self).__init__(parent)
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(0, 0, 0, 0)

    def addWidget(self, widget):
        self.vbox.addWidget(widget)

class ImageView(QLabel):

    def __init__(self, parent=None):
        super(ImageView, self).__init__(parent)

        self.dialog = None

        self.image = None
        self.pixmap = None

        self.setFixedHeight(128)
        self.setHidden(True)

        self.image_extensions = [".png", ".jpg"]

        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)

    def setPath(self, path):

        if path is None:
            self.setHidden(True)
            return

        try:
            _, ext = os.path.splitext(path)
            if ext.lower() in self.image_extensions:
                image = QImage(path)
                self.setImage(image)
                return
        except Exception as e:
            print("failed to set image: %s" % e)
        self.setHidden(True)

    def setImage(self, image):
        self.image = image
        if image.width() > self.width() or \
           image.height() > self.height():
            self.pixmap = QPixmap.fromImage(image).scaled(
                self.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation)
        else:
            self.pixmap = QPixmap.fromImage(image)
        super().setPixmap(self.pixmap)
        self.setHidden(False)

class FileContentSortProxyModel(SortProxyModel):
    """
    A sort proxy model that is aware of the file content

    directories are allways sorted before files

    Note: the proxy model could be extended to support filtering
        remote/local/synced files
    """

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
        dir = isinstance(ent, sync2.DirEnt)

        if order == Qt.AscendingOrder:
            dir = not dir

        return (dir, val, ent.name())

class FileContextMenu(QMenu):
    def __init__(self, ctxt, selection, parent=None):
        super(FileContextMenu, self).__init__(parent)

        self.ctxt = ctxt

        ents = [row[0] for row in selection]

        if len(selection) == 1:
            ent = selection[0][0]
            menu = self.addMenu("Open")
            act = menu.addAction("Native", lambda: self._action_open_native(ent))
            act = menu.addAction("as Text")
            act = menu.addAction("as Image")
            act = menu.addAction("as Video")
            act = menu.addAction("as PDF")

        act = self.addAction("Open Current Directory",
            lambda: openNative(self.ctxt.currentLocation()))

        self.addSeparator()

        if self.ctxt.hasActiveContext():

            menu = self.addMenu("Sync")
            act = menu.addAction("Sync", lambda: self._action_sync(ents))
            act = menu.addAction("Push", lambda: self._action_push(ents))
            act = menu.addAction("Pull", lambda: self._action_pull(ents))

            if len(selection) == 1:
                act = self.addAction("Info", lambda: self._action_info(ents[0]))

            self.addSeparator()

        ico = self.style().standardIcon(QStyle.SP_BrowserReload)
        act = self.addAction(ico, "Refresh", lambda: self.ctxt.reload())

        act = self.addAction("Cut")
        act = self.addAction("Copy")
        act = self.addAction("Paste")

        self.addSeparator()

        if self.ctxt.hasActiveContext():
            menu = self.addMenu("Delete")
            act = menu.addAction("Delete Local")
            act = menu.addAction("Delete Remote")
        else:
            act = self.addAction("Delete")

    def _action_template(self):
        pass

    def _action_open_native(self, ent):

        if isinstance(ent, sync2.DirEnt):
            openNative(ent.local_base)
        else:
            openNative(ent.local_path)

    def _action_sync_impl(self, ents, push, pull):

        # convert mix of FileEnt and DirEnt into just DirEnt

        paths = []
        for ent in ents:
            if isinstance(ent, sync2.DirEnt):
                paths.append(ent)
            else:
                paths.append(sync2.DirEnt(None, ent.remote_path, ent.local_path))

        optdialog = SyncOptionsDialog(self)
        if optdialog.exec_() == QDialog.Accepted:
            opts = optdialog.options()
            dialog = SyncProgressDialog(self.ctxt)
            dialog.initiateSync(paths, push, pull, **opts)
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
        hostname = self.ctxt.activeContext().hostname
        dialog.setEntry(ent, hostname)
        dialog.exec_()

class FileTableView(TableView):

    locationChanged = pyqtSignal(str, int, int)  # dir, dcount, fcount

    triggerSave = pyqtSignal()
    triggerRestore = pyqtSignal()

    def __init__(self, ctxt, parent=None):
        super(FileTableView, self).__init__(parent)

        self.ctxt = ctxt

        self.setWordWrap(False)

        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setVerticalHeaderVisible(False)
        self.setSortingEnabled(True)
        self.setColumnsMovable(True)
        self.setColumnHeaderClickable(True)
        self.setEditTriggers(QAbstractItemView.SelectedClicked)
        # self.setEditTriggers(QAbstractItemView.NoEditTriggers)

        model = self.baseModel()

        idx = model.addColumn(2, "icon", editable=False)
        self.setDelegate(idx, ImageDelegate(self))
        model.getColumn(idx).setDisplayName("")
        model.getColumn(idx).setSortTransform(lambda data, row: os.path.splitext(data[row][3])[-1])

        idx = model.addColumn(1, "state", editable=False)
        self.setDelegate(idx, ImageDelegate(self))
        model.getColumn(idx).setSortTransform(lambda data, row: data[row][-2])

        idx = model.addColumn(3, "filename", editable=True)
        delegate = EditItemDelegate(self)
        delegate.editRow.connect(self.editRow)
        self.setDelegate(idx, delegate)

        model.getColumn(idx).setShortName("Name")
        model.getColumn(idx).setDisplayName("File Name")

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

        idx = model.addTransformColumn(7, "remote_permission", self._fmt_octal)
        self.setDelegate(idx, MonospaceDelegate(self))
        model.getColumn(idx).setDefaultTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        model.getColumn(idx).setSortTransform(lambda data, row: data[row][7])

        idx = model.addTransformColumn(10, "local_mtime", self._fmt_datetime)
        self.setDelegate(idx, MonospaceDelegate(self))
        model.getColumn(idx).setDefaultTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        model.getColumn(idx).setSortTransform(lambda data, row: data[row][10])

        idx = model.addTransformColumn(11, "remote_mtime", self._fmt_datetime)
        self.setDelegate(idx, MonospaceDelegate(self))
        model.getColumn(idx).setDefaultTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        model.getColumn(idx).setSortTransform(lambda data, row: data[row][11])

        idx = model.addTransformColumn(0, "remote_path", self._fmt_remote_path)

        model.addColumn(8, "remote_public", editable=False)
        model.addColumn(9, "remote_encryption", editable=False)

        model.addColumn(12, "type", editable=False)

        model.addForegroundRule("fg1", self._foregroundRule)
        model.addBackgroundRule("fg2", self._backgroundRule)

        self.ctxt.locationChanging.connect(self.onLocationChanging)
        self.ctxt.locationChanged.connect(self.onLocationChanged)

        self.selectionChangedEvent.connect(self.onSelectionChanged)

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

        print("view setVisible", b)

    def resetColumns(self):

        self._setHiddenColumns([])
        self._setColumnOrder(list(range(self.columnCount())))

        self.horizontalHeader().setSectionResizeMode(0)
        idx = self.baseModel().getColumnIndexByName("icon")
        self.setColumnWidth(idx, 40)

        idx = self.baseModel().getColumnIndexByName("state")
        self.setColumnWidth(idx, 40)

        idx = self.baseModel().getColumnIndexByName("filename")
        self.setColumnWidth(idx, 200)

        idx = self.baseModel().getColumnIndexByName("local_size")
        self.setColumnWidth(idx, 75)

        idx = self.baseModel().getColumnIndexByName("remote_size")
        self.setColumnWidth(idx, 75)

        idx = self.baseModel().getColumnIndexByName("local_permission")
        self.setColumnWidth(idx, 125)

        idx = self.baseModel().getColumnIndexByName("remote_permission")
        self.setColumnWidth(idx, 125)

        idx = self.baseModel().getColumnIndexByName("local_mtime")
        self.setColumnWidth(idx, 175)

        idx = self.baseModel().getColumnIndexByName("remote_mtime")
        self.setColumnWidth(idx, 175)

        idx = self.baseModel().getColumnIndexByName("remote_path")
        self.setColumnWidth(idx, 100)

        idx = self.baseModel().getColumnIndexByName("remote_public")
        self.setColumnWidth(idx, 100)

        idx = self.baseModel().getColumnIndexByName("remote_encryption")
        self.setColumnWidth(idx, 100)

        idx = self.baseModel().getColumnIndexByName("type")
        self.setColumnWidth(idx, 100)

        print("setting column widths")

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
        if isinstance(ent, sync2.DirEnt):
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

    def _itemFromEntry(self, ent):

        if isinstance(ent, sync2.FileEnt):

            df = {'size': 0, "permission": 0, "mtime": 0, "version": 0,
                  "public": "", "encryption": ""}

            lf = ent.lf or df
            rf = ent.rf or df
            af = ent.af or df

            item = [
                ent,
                self.ctxt.getFileStateIcon(ent.state()),
                self.ctxt.getFileIcon(ent.local_path),
                ent.name(),
                af['size'],
                rf['size'],
                af['permission'],
                rf['permission'],
                rf['public'],
                rf['encryption'],
                af['mtime'],
                rf['mtime'],
                getFileType(ent.name()),
                ent.state()
            ]

        elif isinstance(ent, sync2.DirEnt):

            item = [
                ent,
                None,
                self.ctxt.getIcon(QFileIconProvider.Folder),
                ent.name(),
                0,
                0,
                0,
                0,
                "",
                "",
                0,
                0,
                "",
                ent.state()
            ]

        return item

    def onLocationChanged(self, directory):

        self.setEnabled(True)

        data = []
        # todo change record to FileEnt..
        fcount = 0
        dcount = 0
        for ent in self.ctxt.contents():
            item = self._itemFromEntry(ent)
            data.append(item)
            if isinstance(ent, sync2.FileEnt):
                fcount += 1
            elif isinstance(ent, sync2.DirEnt):
                dcount += 1
        self.setNewData(data)

        self.locationChanged.emit(directory, dcount, fcount)

    def onMouseDoubleClick(self, index):

        row = index.data(RowValueRole)
        ent = row[0]

        if isinstance(ent, sync2.DirEnt):
            self.ctxt.pushChildDirectory(ent.name())
        else:
            print(ent.lf)
            print(ent.rf)
            print(ent.af)

    def onMouseReleaseRight(self, event):

        rows = self.getSelection()

        contextMenu = FileContextMenu(self.ctxt, rows, self)

        contextMenu.exec_(event.globalPos())

    def onMouseReleaseMiddle(self, event):

        # TODO: experiment with inserting rows
        #       and editing data
        # create an editor close signal which contains a model index
        #   and an edit hint
        # may need a custom close editor which is given the hint
        #
        # the item delegate detects tab/backtab and closes the editor
        # with the correct hint, closeEditor can then open a new edior
        # - view.commitData()
        # - model.setData()

        rows = self.selectionModel().selectedRows()
        if len(rows) != 1:
            return

        row = rows[0].row()

        col = self.baseModel().getColumnIndexByName("filename")
        self.scrollToRow(row)
        index = self.model().index(row, col)

        ent = sync2.DirEnt("sample-%d" % self.rowCount(), "", "")
        item = self._itemFromEntry(ent)
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

        print("insert item", ent.name())

        #self.baseModel().tabledata.insert(0, item)
        #self.baseModel().insertRow(0)
        #self.edit(index)
        #self.setCurrentIndex(index)
        #self._edit_index = index

    def onMouseReleaseBack(self, event):

        self.ctxt.popDirectory()

    def onMouseReleaseForward(self, event):

        self.ctxt.unpopDirectory()

    def onHeaderClicked(self, idx):
        print(idx)

    def closeEditor(self, editor, hint):

        # QAbstractItemDelegate.NoHint
        # QAbstractItemDelegate.EditNextItem
        # QAbstractItemDelegate.EditPreviousItem
        # QAbstractItemDelegate.SubmitModelCache
        # QAbstractItemDelegate.RevertModelCache
        print("close", editor, hint)

        super().closeEditor(editor, hint)

    def editRow(self, row, col):
        index = self.model().index(row, col)
        self.setCurrentIndex(index)
        self.edit(index)

    def onCommitValidateData(self, index, value):
        """
        intercept the edit data request
        to modify an entry and replace the entire row
        """
        return False
        row = index.data(RowValueRole)
        ent = row[0]

        idx = self.baseModel().getColumnIndexByName("filename")
        print(index.column(), idx)
        if index.column() != idx:
            return False

        try:
            # TODO: renaming could result in inserting one value
            #       in addition to replacing one row
            new_ent = self.ctxt.renameEntry(ent, value)

            if new_ent is None:
                return False
            item = self._itemFromEntry(new_ent)
            self.replaceRow(index.row(), item)

        except Exception as e:
            print(e)
            return False

        return False

    def onSelectionChanged(self):
        pass

        # push
        # pull
        # sync
        # copy
        # cut
        # paste
        # remove_local
        # remove_remote

    def _foregroundRule(self, index, col):

        row = index.data(RowValueRole)
        ent = row[0]
        state = row[-2].split(":")[0]

        if isinstance(ent, sync2.DirEnt):

            return QColor(32, 32, 200)

    def _backgroundRule(self, index, col):

        row = index.data(RowValueRole)
        ent = row[0]
        state = row[-2].split(":")[0]

        if not self.ctxt.hasActiveContext():
            return

        if state == sync2.FileState.SAME:
            return None

        elif state == sync2.FileState.PUSH:
            return QColor(32, 200, 32, 32)

        elif state == sync2.FileState.PULL:
            return QColor(32, 32, 200, 32)

        elif state == sync2.FileState.CONFLICT_MODIFIED:
            return QColor(255, 170, 0, 32)

        elif state == sync2.FileState.CONFLICT_CREATED:
            return QColor(255, 170, 0, 32)

        elif state == sync2.FileState.CONFLICT_VERSION:
            return QColor(255, 170, 0, 32)

        elif state == sync2.FileState.CONFLICT_TYPE:
            return QColor(255, 170, 0, 32)

        elif state == sync2.FileState.DELETE_BOTH:
            return QColor(255, 50, 0, 32)

        elif state == sync2.FileState.DELETE_REMOTE:
            return QColor(255, 50, 0, 32)

        elif state == sync2.FileState.DELETE_LOCAL:
            return QColor(255, 50, 0, 32)

        if state == sync2.FileState.ERROR:
            return QColor(255, 0, 0, 64)

        return None

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

    pushDirectory = pyqtSignal(str)
    toggleHiddenSection = pyqtSignal(str)

    def __init__(self, parent=None):
        super(FavoritesListView, self).__init__(parent)

        self.setLastColumnExpanding(True)

        self.setWordWrap(False)
        self.setVerticalHeaderVisible(False)
        self.setHorizontalHeaderVisible(False)

        idx = self.baseModel().addColumn(0, "icon")
        self.setDelegate(idx, ImageDelegate(self))
        idx = self.baseModel().addColumn(1, "favorites")
        self.setDelegate(idx, FavoritesDelegate(self))

        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

    def setVisible(self, b):
        super().setVisible(b)

        idx = self.baseModel().getColumnIndexByName("icon")
        self.setColumnWidth(idx, 32)

    def onMouseDoubleClick(self, index):
        data = index.data(RowValueRole)
        path = data[2]
        if path is not None:
            path = os.path.expanduser(path)
            self.pushDirectory.emit(path)
        else:
            self.toggleHiddenSection.emit(data[1])

    def onMouseReleaseRight(self, event):
        pass

    def onMouseReleaseMiddle(self, event):
        pass

    def onHeaderClicked(self, idx):
        pass

class LocationView(QWidget):
    """docstring for LocationView"""

    def __init__(self, ctxt, parent=None):
        super(LocationView, self).__init__(parent)

        self.ctxt = ctxt
        self.vbox = QVBoxLayout(self)
        self.hbox1 = QHBoxLayout()
        self.hbox2 = QHBoxLayout()

        # https://joekuan.wordpress.com/2015/09/23/list-of-qt-icons/
        self.edit_location = QLineEdit(self)

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

        self.hbox1.addWidget(self.btn_back)
        self.hbox1.addWidget(self.btn_forward)
        self.hbox1.addWidget(self.btn_up)
        self.hbox1.addWidget(self.btn_refresh)
        self.hbox1.addWidget(self.edit_location)
        self.hbox1.addWidget(self.btn_open)

        self.vbox.addLayout(self.hbox1)

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
        self.edit_location.returnPressed.connect(self.onOpenButtonPressed)
        self.ctxt.locationChanging.connect(self.onLocationChanging)
        self.ctxt.locationChanged.connect(self.onLocationChanged)

    def onBackButtonPressed(self):
        self.ctxt.popDirectory()

    def onForwardButtonPressed(self):
        self.ctxt.unpopDirectory()

    def onUpButtonPressed(self):
        self.ctxt.pushParentDirectory()

    def onRefreshButtonPressed(self):
        self.ctxt.reload()

    def onOpenButtonPressed(self):
        directory = self.edit_location.text().strip()
        if os.path.exists(directory):
            self.ctxt.pushDirectory(directory)

    def _getEnt(self):
        path = self.ctxt.currentLocation()
        abspath, relpath = self.ctxt.activeContext().normPath(path)
        ent = sync2.DirEnt(abspath.split()[-1], relpath, abspath)
        return ent

    def onFetchButtonPressed(self):

        dialog = SyncProgressDialog(self.ctxt)
        dialog.initiateFetch()
        dialog.exec_()
        self.ctxt.reload()

    def _onSyncButtonPressedImpl(self, push, pull):

        dent = self._getEnt()

        optdialog = SyncOptionsDialog(self)
        if optdialog.exec_() == QDialog.Accepted:
            opts = optdialog.options()
            dialog = SyncProgressDialog(self.ctxt)
            dialog.initiateSync([dent], push, pull, **opts)
            dialog.exec_()
            self.ctxt.reload()

    def onSyncButtonPressed(self):
        self._onSyncButtonPressedImpl(True, True)

    def onPushButtonPressed(self):
        self._onSyncButtonPressedImpl(True, False)

    def onPullButtonPressed(self):
        self._onSyncButtonPressedImpl(False, True)

    def onLocationChanging(self):

        self.setEnabled(False)

    def onLocationChanged(self, directory):

        self.setEnabled(True)

        self.btn_forward.setEnabled(self.ctxt.hasForwardHistory())
        self.btn_back.setEnabled(self.ctxt.hasBackHistory())

        active = self.ctxt.hasActiveContext()
        self.btn_fetch.setEnabled(active)
        self.btn_sync.setEnabled(active)
        self.btn_push.setEnabled(active)
        self.btn_pull.setEnabled(active)

        self.edit_location.setText(directory)

class ProgressThread(QThread):

    processingFile = pyqtSignal(str)  # path
    fileStatus = pyqtSignal(object)  # list of status result
    getEncryptionPassword = pyqtSignal(str)

    def __init__(self, parent=None):
        super(ProgressThread, self).__init__(parent)

        self.alive = True

        self._tlimit_1 = 0
        self._tlimit_2 = 0
        self._results = []

        self._password = None
        self._lk_password = QMutex()
        self._cv_password = QWaitCondition()

    def getEncryptionPasswordWaiter(self, kind):
        """
        emit a signal to open a password dialog on the main thread
        then wait for the dialog to close and the password to be set
        return the password

        this blocks the calling thread while the ui is operated
        """
        self._password = None
        self.getEncryptionPassword.emit(kind)

        self._lk_password.lock()
        try:
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

    def sendUpdate(self, path):

        now = time.time()

        if self._tlimit_1 + .5 < now:
            self._tlimit_1 = now

            self.processingFile.emit(path)

    def sendStatus(self, status):

        self._results.append(status)

        now = time.time()

        if self._tlimit_2 + .5 < now:
            self._tlimit_2 = now

            self.fileStatus.emit(self._results)
            self._results = []

class FetchProgressThread(ProgressThread):

    def __init__(self, ctxt, parent=None):
        super(FetchProgressThread, self).__init__(parent)

        self.ctxt = ctxt

    def run(self):

        # construct a new sync context for this thread
        ctxt = self.ctxt.activeContext().clone()
        ctxt.getPassword = self.ctxt.getEncryptionPassword

        # create an iterable in this thread for processing the command

        # iterable = _dummy_fetch_iter(ctxt)
        iterable = sync2._fetch_iter(ctxt)

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
                print("stop iteration")
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



    def run(self):

        ctxt = self.ctxt.activeContext().clone()
        ctxt.getPassword = self.getEncryptionPasswordWaiter

        # iterable = _dummy_sync_iter(
        #    ctxt, self.paths,
        #    self.push, self.pull, self.force, self.recursive
        # )

        iterable = sync2._sync_impl_iter(
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

                sym = sync2.FileState.symbol(result.state)

                self.sendStatus("%s %s" % (sym, result.ent.remote_path))

                if result.message:
                    self.sendStatus(result.message.strip())

            except StopIteration as e:
                break

            except Exception as e:
                # TODO: reraise in main thread
                logging.exception(e)
                break

            if not self.alive:
                break

        self.fileStatus.emit(self._results)

        ctxt.close()

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

    def __init__(self, ctxt, parent=None):
        super(SyncProgressDialog, self).__init__(None)

        self.ctxt = ctxt

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

    def initiateFetch(self):

        if self._run_fetch or self._run_sync:
            return

        self._run_fetch = True

        self.lbl_action.setText("Fetching...")

        self.thread = FetchProgressThread(self.ctxt, self)

        self.thread.processingFile.connect(lambda path: self.lbl_status.setText(path))
        self.thread.fileStatus.connect(lambda paths: self.txt_status.append('\n'.join(paths)))
        self.thread.finished.connect(self.onThreadFinished)

    def initiateSync(self, paths, push, pull, force, recursive):

        if self._run_fetch or self._run_sync:
            return

        self._run_sync = (paths, push, pull, force, recursive)

        self.lbl_action.setText("Syncing...")

        self.thread = SyncProgressThread(self.ctxt,
            paths, push, pull, force, recursive, self)

        self.thread.getEncryptionPassword.connect(self.onGetEncryptionPassword)
        self.thread.processingFile.connect(lambda path: self.lbl_status.setText(path))
        self.thread.fileStatus.connect(lambda paths: self.txt_status.append('\n'.join(paths)))
        self.thread.finished.connect(self.onThreadFinished)

    def onGetEncryptionPassword(self, kind):

        password = None

        try:
            password = self.ctxt.getEncryptionPassword(kind)

        finally:
            # set the password, or None if the user canceled
            # wake up the thread that was waiting
            self.thread.setEncryptionPassword(password)

    def onThreadFinished(self):

        self.lbl_status.setText("Finished.")
        self.btn_exit.setText("Close")

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
        self.lbl_status_image.setFrameStyle(QFrame.Panel | QFrame.Raised)

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

        if state == sync2.FileState.SAME:
            return QPixmap(":/img/fs_same.png")
        elif state == sync2.FileState.PUSH:
            return QPixmap(":/img/fs_push.png")
        elif state == sync2.FileState.PULL:
            return QPixmap(":/img/fs_pull.png")
        elif state == sync2.FileState.CONFLICT_MODIFIED:
            return QPixmap(":/img/fs_conflict.png")
        elif state == sync2.FileState.CONFLICT_CREATED:
            return QPixmap(":/img/fs_conflict.png")
        elif state == sync2.FileState.CONFLICT_VERSION:
            return QPixmap(":/img/fs_conflict.png")
        elif state == sync2.FileState.CONFLICT_TYPE:
            return QPixmap(":/img/fs_conflict.png")
        elif state == sync2.FileState.DELETE_BOTH:
            return QPixmap(":/img/fs_delete.png")
        elif state == sync2.FileState.DELETE_REMOTE:
            return QPixmap(":/img/fs_delete.png")
        elif state == sync2.FileState.DELETE_LOCAL:
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

class FavoritesPane(Pane):
    """docstring for FavoritesPane"""

    def __init__(self, ctxt, cfg, parent=None):
        super(FavoritesPane, self).__init__(parent)

        self.ctxt = ctxt
        self.cfg = cfg

        self.table_favorites = FavoritesListView(self)
        self.view_image = ImageView(self)

        self.addWidget(self.table_favorites)
        self.addWidget(self.view_image)

        self._hidden_sections = set()

        self.onFavoritesChanged()

        self.table_favorites.pushDirectory.connect(
            lambda path: self.ctxt.pushDirectory(path))

        self.table_favorites.toggleHiddenSection.connect(
            self.onToggleHiddenSection)

    def previewEntry(self, ent):

        if isinstance(ent, sync2.FileEnt):
            self.view_image.setPath(ent.local_path)

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

            icon = QFileIconProvider.Folder
            if 'icon' in row and isinstance(row['icon'], str):
                if hasattr(QFileIconProvider, row['icon']):
                    icon = getattr(QFileIconProvider, row['icon'])

            icon = self.ctxt.getIcon(icon)
            data.append([icon, row['name'], row['path'], False])

        self.table_favorites.setNewData(data)

    def onToggleHiddenSection(self, section):

        if section in self._hidden_sections:
            self._hidden_sections.remove(section)
        else:
            self._hidden_sections.add(section)

        self.onFavoritesChanged()

class SyncMainWindow(QMainWindow):
    """docstring for MainWindow"""

    def __init__(self, ctxt, cfg):
        super(SyncMainWindow, self).__init__()

        self.ctxt = ctxt
        self.cfg = cfg

        self.initMenuBar()
        self.initStatusBar()

        self.table_file = FileTableView(self.ctxt, self)

        self.view_location = LocationView(self.ctxt, self)

        self.pane_favorites = FavoritesPane(ctxt, cfg, self)
        self.pane_file = Pane(self)
        self.pane_file.addWidget(self.view_location)
        self.pane_file.addWidget(self.table_file)

        self.splitter = QSplitter(self)
        self.splitter.addWidget(self.pane_favorites)
        self.splitter.addWidget(self.pane_file)

        self.setCentralWidget(self.splitter)

        self.table_file.locationChanged.connect(self.onTableLocationChanged)
        self.table_file.selectionChangedEvent.connect(self.onTableSelectionChanged)

        self.table_file.triggerSave.connect(self.onTriggerSave)
        self.table_file.triggerRestore.connect(self.onTriggerRestore)

    def initMenuBar(self):

        menubar = self.menuBar()

        self.file_menu = menubar.addMenu("File")
        self.file_menu.addSeparator()
        self.file_menu.addAction("Exit")

    def initStatusBar(self):

        statusbar = self.statusBar()
        self.sbar_lbl_dir_status1 = QLabel()
        self.sbar_lbl_dir_status2 = QLabel()

        statusbar.addWidget(self.sbar_lbl_dir_status1)
        statusbar.addWidget(self.sbar_lbl_dir_status2)

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

        # run this function immediately after the event loop starts
        QTimer.singleShot(0, self.resetTableView)

        print("end show")

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

        self.sbar_lbl_dir_status1.setText(" ".join(msg))

    def onTableSelectionChanged(self):

        msg = ""

        count = self.table_file.getSelectionCount()

        if count == 1:
            msg = "1 selected"
        elif count > 1:
            msg = "%d selected" % count

        self.sbar_lbl_dir_status2.setText(msg)

        if count == 1:
            ent = self.table_file.getSelection()[0][0]
            self.pane_favorites.previewEntry(ent)

    def showEvent(self, event):
        print("show event", event)

    def resetTableView(self):
        if not self.cfg.state:
            self.table_file.resetColumns()
        else:
            self.table_file.setColumnState(self.cfg.state)

    def onTriggerSave(self):

        self.cfg.state = self.table_file.getColumnState()
        self.cfg.save()

    def onTriggerRestore(self):

        self.table_file.setColumnState(self.cfg.state)

def main():

    if os.name == 'nt':
        cfg_base = os.path.join(os.getenv('APPDATA'))
    else:
        cfg_base = os.path.expanduser("~/.config")

    cfg_path = os.path.join(cfg_base, "yue-sync", "settings.yml")

    # load the config, or create a new one if it does not exist
    save = not os.path.exists(cfg_path)
    cfg = SyncConfig(cfg_path)
    if save:
        cfg.save()

    app = QApplication(sys.argv)
    app.setApplicationName("Yue-Sync")

    app.setQuitOnLastWindowClosed(True)
    app_icon = QIcon(':/img/icon.png')
    app.setWindowIcon(app_icon)

    QGuiApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    installExceptionHook()

    ctxt = SyncUiContext()

    window = SyncMainWindow(ctxt, cfg)
    window.showWindow()

    ctxt.pushDirectory(os.getcwd())


    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
