#! cd ../.. && python3 -m yueserver.tools.syncui

import os
import sys
import time
import math
import logging

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yueserver.dao.filesys.filesys import FileSystem
from yueserver.qtcommon.TableView import (
    TableError, TableModel, TableView, RowValueRole, ImageDelegate,
    SortProxyModel, RowSortValueRole
)
from yueserver.qtcommon.exceptions import installExceptionHook

from yueserver.tools import sync2

def openNative( url ):

    if os.name == "nt":
        os.startfile(url);
    elif sys.platform == "darwin":
        os.system("open %s"%url);
    else:
        # could also use kde-open, gnome-open etc
        # TODO: implement code that tries each one until one works
        #subprocess.call(["xdg-open",filepath])
        sys.stderr.write("open unsupported on %s"%os.name)

def isSubPath(dir_path, file_path):
    return os.path.abspath(file_path).startswith(os.path.abspath(dir_path)+os.sep)

byte_labels = ['B','KB','MB','GB']
def format_bytes(b):
    kb=1024
    for label in byte_labels:
        if b < kb:
            if label == "B":
                return "%d %s"%(b,label)
            if label == "KB":
                if b < 10:
                    return "%.2f %s"%(b,label)
                else:
                    return "%d %s"%(b,label)
            else:
                return "%.2f %s"%(b,label)
        b /= kb
    return "%d%s"%(b,byte_labels[-1])

def format_mode_part(mode):
    s = ""
    s += "r" if 0x4&mode else "-"
    s += "w" if 0x2&mode else "-"
    s += "x" if 0x1&mode else "-"
    return s

def format_mode(mode):
    """ format unix permissions as string
    e.g. octal 0o755 to rwxr-xr-x
    """
    if isinstance(mode,int):
        u = format_mode_part(mode >> 6) # user
        g = format_mode_part(mode >> 3) # group
        o = format_mode_part(mode)      # other
        return u+g+o
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
        print("loaded via check")
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

    def pushChildDirectory(self, dirname):

        directory = os.path.join(self._location, dirname)
        self.load(directory)
        self._location_history.append(directory)

    def pushParentDirectory(self):
        directory, _ = os.path.split(self._location)
        self.load(directory)
        self._location_history.append(directory)

    def popDirectory(self):

        for idx, item in enumerate(reversed(self._location_history)):
            print(idx, item)

        if len(self._location_history) <= 1:
            return

        directory = self._location_history[-2]
        self.load(directory)
        self._location_history = self._location_history[:-1]

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
            print(str(e))
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

            ctxt.current_local_base = userdata['current_local_base']
            ctxt.current_remote_base = userdata['current_remote_base']

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

class Pane(QWidget):
    """docstring for Pane"""
    def __init__(self, parent):
        super(Pane, self).__init__(parent)
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(0,0,0,0)

    def addWidget(self,widget):
        self.vbox.addWidget(widget)

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

        if len(selection) == 1:
            ent = selection[0][0]
            menu = self.addMenu("Open")
            act = menu.addAction("Native", lambda: self._action_open_native(ent))
            act = menu.addAction("as Image")
            act = menu.addAction("as Video")
            act = menu.addAction("as PDF")

        act = self.addAction("Open Current Directory",
            lambda: openNative(self.ctxt.currentLocation()))

        self.addSeparator()

        if self.ctxt.hasActiveContext():

            menu = self.addMenu("Sync")
            act = menu.addAction("Push")
            act = menu.addAction("Pull")
            act = menu.addAction("Sync")
            self.addSeparator()


        act = self.addAction("Refresh", lambda : self.ctxt.reload())

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

class FileTableView(TableView):

    locationChanged = pyqtSignal(str, int, int)  # dir, dcount, fcount

    def __init__(self, ctxt, parent=None):
        super(FileTableView, self).__init__(parent)

        self.ctxt = ctxt

        self.setWordWrap(False)

        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

        model = self.baseModel()

        idx = model.addColumn(2,"icon",editable=False)
        self.setColumnWidth(idx, 500)
        self.setDelegate(idx, ImageDelegate(self))
        model.getColumn(idx).setDisplayName("")
        model.getColumn(idx).setSortTransform(lambda data, row: os.path.splitext(data[row][3])[-1])

        idx = model.addColumn(1,"state",editable=False)

        idx = model.addColumn(3,"filename",editable=False)
        model.getColumn(idx).setShortName("Name")
        model.getColumn(idx).setDisplayName("File Name")

        idx = model.addTransformColumn(4,"local_size", self._fmt_size)
        model.getColumn(idx).setDefaultTextAlignment(Qt.AlignRight|Qt.AlignVCenter)
        model.getColumn(idx).setSortTransform(lambda data, row: data[row][4])

        idx = model.addTransformColumn(5,"remote_size", self._fmt_size)
        model.getColumn(idx).setDefaultTextAlignment(Qt.AlignRight|Qt.AlignVCenter)
        model.getColumn(idx).setSortTransform(lambda data, row: data[row][5])

        idx = model.addTransformColumn(6,"local_permission", self._fmt_octal)
        model.getColumn(idx).setDefaultTextAlignment(Qt.AlignRight|Qt.AlignVCenter)
        model.getColumn(idx).setSortTransform(lambda data, row: data[row][6])

        idx = model.addTransformColumn(7,"remote_permission", self._fmt_octal)
        model.getColumn(idx).setDefaultTextAlignment(Qt.AlignRight|Qt.AlignVCenter)
        model.getColumn(idx).setSortTransform(lambda data, row: data[row][7])

        idx = model.addTransformColumn(10,"local_mtime", self._fmt_datetime)
        model.getColumn(idx).setDefaultTextAlignment(Qt.AlignRight|Qt.AlignVCenter)
        model.getColumn(idx).setSortTransform(lambda data, row: data[row][10])

        idx = model.addTransformColumn(11,"remote_mtime", self._fmt_datetime)
        model.getColumn(idx).setDefaultTextAlignment(Qt.AlignRight|Qt.AlignVCenter)
        model.getColumn(idx).setSortTransform(lambda data, row: data[row][11])

        idx = model.addTransformColumn(0,"remote_path", self._fmt_remote_path)

        model.addColumn(8,"remote_public",editable=False)
        model.addColumn(9,"remote_encryption",editable=False)

        model.addForegroundRule("fg1", self._foregroundRule)
        model.addBackgroundRule("fg2", self._backgroundRule)

        self.setVerticalHeaderVisible(False)

        #model.setColumnShortName(0,"")
        self.setColumnsMovable(True)

        self.setSortingEnabled(True)

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

        # set column widths after the the initial show

        idx = self.baseModel().getColumnIndexByName("icon")
        self.setColumnWidth(idx, 32)

        idx = self.baseModel().getColumnIndexByName("filename")
        self.setColumnWidth(idx, 200)

        idx = self.baseModel().getColumnIndexByName("local_size")
        self.setColumnWidth(idx, 75)

        idx = self.baseModel().getColumnIndexByName("remote_size")
        self.setColumnWidth(idx, 75)

        idx = self.baseModel().getColumnIndexByName("local_mtime")
        self.setColumnWidth(idx, 125)

        idx = self.baseModel().getColumnIndexByName("remote_mtime")
        self.setColumnWidth(idx, 125)

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
        dt = data[row][key]
        if dt > 0:
            return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(dt))
        return ""

    def onLocationChanged(self, directory):

        data = []
        # todo change record to FileEnt..
        fcount = 0
        dcount = 0
        for ent in self.ctxt.contents():

            if isinstance(ent, sync2.FileEnt):

                df = {'size': 0, "permission": 0, "mtime": 0, "version": 0,
                      "public": 0, "encryption": 0}
                lf = ent.lf or df
                rf = ent.rf or df
                af = ent.af or df

                item = [
                    ent,
                    ent.state(),
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
                ]
                data.append(item)
                fcount += 1
            elif isinstance(ent, sync2.DirEnt):

                item = [
                    ent,
                    ent.state(),
                    self.ctxt.getIcon(QFileIconProvider.Folder),
                    ent.name(),
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                ]
                data.append(item)
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

        contextMenu.exec_( event.globalPos() )

    def onMouseReleaseMiddle(self, event):
        pass

    def onHeaderClicked(self, idx):
        pass

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
        state = row[1].split(":")[0]

        if isinstance(ent, sync2.DirEnt):

            return QColor(32, 32, 200)

    def _backgroundRule(self, index, col):

        row = index.data(RowValueRole)
        ent = row[0]
        state = row[1]

        if not self.ctxt.hasActiveContext():
            return

        if state == sync2.FileState.SAME:
            return None
        elif state == sync2.FileState.PUSH:
            return QColor(32, 200, 32, 32)

        elif state == sync2.FileState.PULL:
            return QColor(32, 200, 32, 32)

        elif state == sync2.FileState.CONFLICT_MODIFIED:
            return QColor(200, 200, 32, 32)

        elif state == sync2.FileState.CONFLICT_CREATED:
            return QColor(200, 200, 32, 32)

        elif state == sync2.FileState.CONFLICT_VERSION:
            return QColor(200, 200, 32, 32)

        elif state == sync2.FileState.DELETE_BOTH:
            return QColor(200, 32, 32, 32)

        elif state == sync2.FileState.DELETE_REMOTE:
            return QColor(200, 32, 32, 32)

        elif state == sync2.FileState.DELETE_LOCAL:
            return QColor(200, 32, 32, 32)

        if state == sync2.FileState.ERROR:
            return QColor(255, 0, 0, 32)

        return None

class LocationTableView(TableView):
    """docstring for FileTableView"""
    def __init__(self, parent=None):
        super(LocationTableView, self).__init__(parent)
        model = self.baseModel()
        model.addColumn(0,"location",editable=False)

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
        self.btn_back.setIcon(self.style().standardIcon(QStyle.SP_ArrowBack))
        self.btn_back.setAutoRaise(True)

        self.btn_up = QToolButton(self)
        self.btn_up.setIcon(self.style().standardIcon(QStyle.SP_ArrowUp))
        self.btn_up.setAutoRaise(True)

        self.btn_open = QToolButton(self)
        self.btn_open.setIcon(self.style().standardIcon(QStyle.SP_ArrowForward))
        self.btn_open.setAutoRaise(True)

        self.hbox1.addWidget(self.btn_back)
        self.hbox1.addWidget(self.btn_up)
        self.hbox1.addWidget(self.edit_location)
        self.hbox1.addWidget(self.btn_open)

        self.vbox.addLayout(self.hbox1)

        self.btn_fetch = QPushButton("Fetch", self)
        self.btn_sync = QPushButton("Sync", self)
        self.btn_push = QPushButton("Push", self)
        self.btn_pull = QPushButton("Pull", self)
        self.hbox2.addWidget(self.btn_fetch)
        self.hbox2.addWidget(self.btn_sync)
        self.hbox2.addWidget(self.btn_push)
        self.hbox2.addWidget(self.btn_pull)
        self.hbox2.addStretch(1)

        self.vbox.addLayout(self.hbox2)

        self.btn_back.clicked.connect(self.onBackButtonPressed)
        self.btn_up.clicked.connect(self.onUpButtonPressed)
        self.btn_open.clicked.connect(self.onOpenButtonPressed)
        self.btn_fetch.clicked.connect(self.onFetchButtonPressed)
        self.btn_sync.clicked.connect(self.onSyncButtonPressed)
        self.btn_push.clicked.connect(self.onPushButtonPressed)
        self.btn_pull.clicked.connect(self.onPullButtonPressed)
        self.edit_location.returnPressed.connect(self.onOpenButtonPressed)
        self.ctxt.locationChanged.connect(self.onLocationChanged)

    def onBackButtonPressed(self):
        self.ctxt.popDirectory()

    def onUpButtonPressed(self):
        self.ctxt.pushParentDirectory()

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

    def onSyncButtonPressed(self):

        ent = self._getEnt()
        #result = sync2._check(self.ctxt.activeContext(), ent.remote_base, ent.local_base)
        #paths = result.dirs + [sync2.DirEnt(None, f.remote_path, f.local_path) for f  in result.files]
        push = True
        pull = True
        force = False
        recursive = False

        dialog = SyncProgressDialog(self.ctxt)
        dialog.initiateSync([ent], push, pull, force, recursive)
        dialog.exec_()
        self.ctxt.reload()

    def onPushButtonPressed(self):

        ent = self._getEnt()
        push = True
        pull = False
        force = False
        recursive = False

        dialog = SyncProgressDialog(self.ctxt)
        dialog.initiateSync([ent], push, pull, force, recursive)
        dialog.exec_()
        self.ctxt.reload()

    def onPullButtonPressed(self):

        ent = self._getEnt()
        push = False
        pull = True
        force = False
        recursive = False

        dialog = SyncProgressDialog(self.ctxt)
        dialog.initiateSync([ent], push, pull, force, recursive)
        dialog.exec_()
        self.ctxt.reload()

    def onLocationChanged(self, directory):

        active = self.ctxt.hasActiveContext()
        self.btn_fetch.setEnabled(active)
        self.btn_sync.setEnabled(active)
        self.btn_push.setEnabled(active)
        self.btn_pull.setEnabled(active)

        self.edit_location.setText(directory)

class FetchProgressThread(QThread):

    processingFile = pyqtSignal(str)  # path
    fileStatus = pyqtSignal(object)  # list of status result

    def __init__(self, ctxt, parent=None):
        super(FetchProgressThread, self).__init__(parent)

        self.ctxt = ctxt

        self.alive = True

        self._tlimit_1 = 0
        self._tlimit_2 = 0
        self._results = []

    def run(self):

        # construct a new sync context for this thread
        ctxt = self.ctxt.activeContext().clone()

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

class SyncProgressThread(QThread):

    processingFile = pyqtSignal(str)  # path
    fileStatus = pyqtSignal(object)  # list of status result

    def __init__(self, ctxt, paths, push, pull, force, recursive, parent=None):
        super(SyncProgressThread, self).__init__(parent)

        self.ctxt = ctxt
        self.paths = paths
        self.push = push
        self.pull = pull
        self.force = force
        self.recursive = recursive

        self.alive = True

        self._tlimit_1 = 0
        self._tlimit_2 = 0
        self._results = []

    def run(self):

        ctxt = self.ctxt.activeContext().clone()

        #iterable = _dummy_sync_iter(
        #    ctxt, self.paths,
        #    self.push, self.pull, self.force, self.recursive
        #)

        iterable = sync2._sync_impl_iter(
            ctxt, self.paths,
            self.push, self.pull, self.force, self.recursive
        )

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

        self.btn_temp = QPushButton("Temp", self)
        self.btn_exit = QPushButton("Cancel", self)

        self.hbox = QHBoxLayout()
        self.hbox.addStretch(1)
        self.hbox.addWidget(self.btn_temp)
        self.hbox.addWidget(self.btn_exit)

        self.vbox.addWidget(self.lbl_action)
        self.vbox.addWidget(self.lbl_status)
        self.vbox.addWidget(self.txt_status)
        self.vbox.addLayout(self.hbox)

        self.btn_temp.clicked.connect(self.onTempPressed)
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

        self.thread.processingFile.connect(lambda path: self.lbl_status.setText(path))
        self.thread.fileStatus.connect(lambda paths: self.txt_status.append('\n'.join(paths)))
        self.thread.finished.connect(self.onThreadFinished)

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

    def onTempPressed(self):

        self.txt_status.append("hello")

    def exec_(self):

        self.thread.start()
        super().exec_()

    def show(self):
        self.thread.start()
        super().show()

class SyncMainWindow(QMainWindow):
    """docstring for MainWindow"""
    def __init__(self, ctxt):
        super(SyncMainWindow, self).__init__()

        self.ctxt = ctxt

        self.initMenuBar()
        self.initStatusBar()

        self.table_file = FileTableView(self.ctxt, self)
        self.table_location = LocationTableView(self)

        self.view_location = LocationView(self.ctxt, self)

        self.pane_location = Pane(self)
        self.pane_location.addWidget(self.table_location)
        self.pane_file = Pane(self)
        self.pane_file.addWidget(self.view_location)
        self.pane_file.addWidget(self.table_file)

        self.splitter = QSplitter(self)
        self.splitter.addWidget(self.pane_location)
        self.splitter.addWidget(self.pane_file)

        self.setCentralWidget(self.splitter)

        self.table_file.locationChanged.connect(self.onTableLocationChanged)
        self.table_file.selectionChangedEvent.connect(self.onTableSelectionChanged)

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
        dw = int(sw*.6)
        dh = int(sh*.6)
        dx = sw//2 - dw//2
        dy = sh//2 - dh//2
        # use stored values if they exist
        cw = 0#s.getDefault("window_width",dw)
        ch = 0#s.getDefault("window_height",dh)
        cx = -1#s.getDefault("window_x",dx)
        cy = -1#s.getDefault("window_y",dy)
        # the application should start wholly on the screen
        # otherwise, default its position to the center of the screen
        if cx < 0 or cx+cw>sw:
            cx = dx
            cw = dw
        if cy < 0 or cy+ch>sh:
            cy = dy
            ch = dh
        if cw <= 0:
            cw = dw
        if ch <= 0:
            ch = dh
        self.resize(cw,ch)
        self.move(cx,cy)
        self.show()

        # somewhat arbitrary
        # set the width of the quick access view to something
        # reasonable
        lw = 200
        if cw > lw*2:
            self.splitter.setSizes([lw,cw-lw])

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

def main():

    app = QApplication(sys.argv)
    app.setApplicationName("Yue-Sync")

    app.setQuitOnLastWindowClosed(True)
    #app_icon = QIcon(':/img/icon.png')
    #app.setWindowIcon(app_icon)

    QGuiApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    installExceptionHook()

    ctxt = SyncUiContext()

    window = SyncMainWindow(ctxt)
    window.showWindow()

    ctxt.pushDirectory(os.getcwd())

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()