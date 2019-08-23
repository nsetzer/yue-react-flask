

import os
import sys

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

# todo:
# 1. try to use TableModel directly,
#    possibly with a flag to change data
# 2. new model, table data (name, iconA, iconB)
class GridModel(QAbstractItemModel):
    def __init__(self, parent=None):
        super(GridModel, self).__init__(parent)
        self.griddata = [(1, 2),] * 25

        self.iconProvider = QFileIconProvider()

    def index(self, row, column, parent):
        if (0 <= row < self.rowCount()and 0 <= column < self.columnCount()):
            return self.createIndex(row, column, None)
        return QModelIndex()

    def parent(self, child):
        return QModelIndex()

    def rowCount(self, parent=None):
        return len(self.griddata)

    def columnCount(self, parent=None):
        return 2

    def data(self, index, role):

        if not index.isValid():
            return QVariant()

        if role == Qt.DisplayRole:
            return "Item %d/%d" % (index.row(), index.column())
        if role == Qt.DecorationRole:
            return self.iconProvider.icon(QFileIconProvider.File);

class GridView(QListView):

    def __init__(self, parent=None):
        super(GridView, self).__init__(parent)

        self._baseModel = GridModel(self)
        self.setModel(self._baseModel)

        self.setViewMode(QListView.IconMode)
        self.setUniformItemSizes(True)
        self.setResizeMode(QListView.Adjust)
        self.setGridSize(QSize(80, 80))

class _DemoMainWindow(QMainWindow):

    def __init__(self):
        super(_DemoMainWindow, self).__init__()

        self.view = GridView(self)
        print(self.view.model())

        self.centralWidget = QWidget(self)
        self.vbox = QVBoxLayout(self.centralWidget)
        self.vbox.addWidget(self.view)
        self.setCentralWidget(self.centralWidget)


def main():

    app = QApplication(sys.argv)

    window = _DemoMainWindow()
    window.show()

    app.exec_()


if __name__ == '__main__':
    main()
