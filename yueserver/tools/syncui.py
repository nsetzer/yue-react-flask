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
from yueserver.tools import sync2

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

    def contents(self):
        return self._dir_contents

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

class FileTableView(TableView):
    def __init__(self, ctxt, parent=None):
        super(FileTableView, self).__init__(parent)

        self.ctxt = ctxt

        self.setWordWrap(False)

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
        self.setNewData(data)

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
        pass

    def onMouseReleaseMiddle(self, event):
        pass

    def onHeaderClicked(self, idx):
        pass

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
        self.hbox = QHBoxLayout()

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

        self.hbox.addWidget(self.btn_back)
        self.hbox.addWidget(self.btn_up)
        self.hbox.addWidget(self.edit_location)
        self.hbox.addWidget(self.btn_open)

        self.vbox.addLayout(self.hbox)

        self.btn_back.clicked.connect(self.onBackButtonPressed)
        self.btn_up.clicked.connect(self.onUpButtonPressed)
        self.btn_open.clicked.connect(self.onOpenButtonPressed)
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

    def onLocationChanged(self, directory):

        self.edit_location.setText(directory)

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

    def initMenuBar(self):

        menubar = self.menuBar()

        self.file_menu = menubar.addMenu("File")
        self.file_menu.addSeparator()
        self.file_menu.addAction("Exit")

    def initStatusBar(self):

        statusbar = self.statusBar()
        self.sbar_lbl_status1 = QLabel()

        statusbar.addWidget(self.sbar_lbl_status1)

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

def main():

    app = QApplication(sys.argv)

    QGuiApplication.setAttribute(Qt.AA_UseHighDpiPixmaps);

    ctxt = SyncUiContext()

    window = SyncMainWindow(ctxt);
    window.showWindow()

    ctxt.pushDirectory(os.getcwd())

    app.exec_()

if __name__ == '__main__':
    main()