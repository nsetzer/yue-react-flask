
import sys
import math
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

# for testing
import string
import random
# http://pyqt.sourceforge.net/Docs/PyQt4/qt.html#ItemDataRole-enum

RowValueRole = Qt.UserRole + 1000
RowValueIndexRole = Qt.UserRole + 1001
RowSortValueRole = Qt.UserRole + 1002

class TableError(Exception):
    pass

class StyledItemDelegate(QStyledItemDelegate):

    def paintInit(self,painter,option,index):
        style = QApplication.style()
        #if (option.state & QStyle.State_Selected):
            # Whitee pen while selection
        pen =painter.pen()
        brush = painter.brush()

        if (option.state & QStyle.State_Selected):
            #pen = index.data(Qt.ForegroundRole)
            #if pen is not None:
            #    painter.setPen(pen)
            #else:
            painter.setPen(Qt.white)
            painter.setBrush(option.palette.highlightedText())
        else:
            #painter.setPen(QPen(option.palette.color(QPalette.Foreground), 0));
            # set the pen to a custom color, or reset the pen to default
            pen   = index.data(Qt.ForegroundRole)
            if pen is not None:
                painter.setPen(pen)
            else:
                painter.setPen(QPen(option.palette.color(QPalette.Foreground), 0))
            # draw the background color
            brush = index.data(Qt.BackgroundRole)
            if brush is not None:
                painter.fillRect(option.rect, brush)

        # This call will take care to draw, dashed line while selecting
        style.drawControl(QStyle.CE_ItemViewItem, option, painter, option.widget)
        #else:

        #painter.setPen(QPen(option.palette.color(QPalette.Foreground), 0));
        #brush = index.data(Qt.ForegroundRole)
        #if brush is not None:
        #    painter.setBrush(brush);
        #painter.setPen(pen)
        #painter.setBrush(brush)
        return

class ComboBoxTextDelegate(StyledItemDelegate):

    def __init__(self,parent,slItems):
        super(ComboBoxTextDelegate, self).__init__(parent)

        self.slItems = slItems


    def createEditor(self,parent,option,index):
        combo = QComboBox(parent)
        for item in self.slItems:
            combo.addItem(item)
        return combo

    def setEditorData(self,editor,index):
        x = str(index.data())
        editor.setCurrentText(x)

    def setModelData(self,editor,model,index):
        print(editor.currentText())
        model.setData(index,editor.currentText())

class DualTextDelegate(StyledItemDelegate):
    """
    display text on the right and left side of a column cell
    left text is taken from the data model for the given column
    right text it generated using a transform function
        this function is given an index object

    """
    def __init__(self,rTransform,parent):
        """
        rTransform : lambda index -> QVariant
        """
        super(DualTextDelegate, self).__init__(parent)
        self.flagsL = Qt.AlignVCenter|Qt.AlignLeft
        self.flagsR = Qt.AlignVCenter|Qt.AlignRight
        self.rTransform = rTransform

    def paint(self,painter,option,index):

        textL = str(index.data(Qt.DisplayRole))
        textR = str(self.rTransform(index))

        self.paintInit(painter,option,index)

        painter.drawText(option.rect,self.flagsR,textR)


        fm = QFontMetrics(painter.font())
        w = fm.width(textR)
        # prevent left text from overlapping right text
        clipRect = option.rect
        clipRect.setWidth(max(0,clipRect.width()-w))
        painter.drawText(option.rect,self.flagsL,textL)

class ImageDelegate(StyledItemDelegate):
    """
    display text on the right and left side of a column cell
    left text is taken from the data model for the given column
    right text it generated using a transform function
        this function is given an index object

    """
    def __init__(self,parent):
        super(ImageDelegate, self).__init__(parent)

        self.trasformMode = Qt.SmoothTransformation # FastTransformation

    def paintImageCentered(self,painter,rect,image):

        rect = QRect(rect)
        size = QSize(rect.width(), rect.height())

        # shrink the image if we need to
        if image.width() > rect.width()  or image.height() > rect.height():
            #Qt.IgnoreAspectRatio, Qt.KeepAspectRatio, Qt.KeepAspectRatioByExpanding
            aspect = Qt.KeepAspectRatio
            mode = Qt.SmoothTransformation
            image = image.scaled(size,aspect,self.trasformMode)

        # center horizontally
        if image.width() < rect.width():
            dw = rect.width() - image.width()
            rect.setX(rect.x()+dw//2)
            rect.setWidth(image.width())

        # center vertically
        if image.height() < rect.height():
            dh = rect.height() - image.height()
            rect.setY(rect.y()+dh//2)
            rect.setHeight(image.height())

        painter.drawImage(rect,image)

    def paint(self,painter,option,index):

        self.paintInit(painter,option,index)

        image = index.data(Qt.DisplayRole)

        if image is None:
            return

        if not isinstance(image,(QImage,)):
            painter.drawText(option.rect,0,"Error:"+str(image))
            return

        self.paintImageCentered(painter,option.rect,image)

class StarRating(QObject):
    """ handles rendering the editable stars """

    ModeEdit = 1
    ModeDisplay = 2

    scaleFactor = 20

    def __init__(self,parent=None):
        super(StarRating,self).__init__(parent)

        self.num_stars = 0
        self.max_stars = 5

        rotation=.33
        points=[]
        for i in reversed(list(range(0,11))):
            # if you want the star centered at a point,
            # remove the +1 from the points
            w = 2*(i+rotation)*math.pi/10
            r = (i%2+1)/2 # every other point has max or min radius set
            points.append( (1.0+r*math.sin(w), 1.0+r*math.cos(w) ) )

        self.points = points
        print(["%.1f,%.1f"%p for p in points])
        self.polyStar = QPolygonF([ QPointF(*x) for x in points ])

        path = QPainterPath(self.scaleFactor*QPointF(*self.points[0]))
        for p in self.points[1:]:
            path.lineTo( self.scaleFactor*QPointF(*p) )
        self.pathStar = path

        points = [(1.0,0.5),(1.75,1.0),(1.0,1.5),(0.25,1.0),]
        self.pointsDiamond = points

    def setValue(self,value):
        self.num_stars = value

    def value(self):
        return self.num_stars

    def sizeHint(self):
        return self.scaleFactor * QSize(self.max_stars,1)

    def paint(self,painter,rect,palette,mode):

        painter.save()

        painter.setRenderHint(QPainter.Antialiasing, True)
        #painter.setPen(Qt.NoPen)

        pen = QPen(QColor(0,128,128))
        pen.setWidth(1)
        painter.setPen(pen)
        #painter.setBrush(QColor(0,0,255))
        if mode == StarRating.ModeEdit:
            painter.setBrush(palette.highlight())
        else:
            painter.setBrush(palette.color(QPalette.Foreground))

        scaleFactorY = rect.height() * 0.8 / 2
        scaleFactorX = (rect.width() / 5) * 0.8 / 2
        scaleFactor = min(scaleFactorX,scaleFactorY)
        xOffset = (rect.width() - 2*5*scaleFactor) / 2
        yOffset = (rect.height() - 2*scaleFactor) / 2
        painter.translate(rect.x(),rect.y())
        painter.translate(xOffset,yOffset)

        path = QPainterPath(scaleFactor*QPointF(*self.points[0]))
        for p in self.points[1:]:
            path.lineTo( scaleFactor*QPointF(*p) )
        pathStar = path

        path = QPainterPath(scaleFactor*QPointF(*self.pointsDiamond[0]))
        for p in self.pointsDiamond[1:]:
            path.lineTo( scaleFactor*QPointF(*p) )
        pathDiamong = path

        for i in range(self.max_stars):
            if i < self.num_stars:
                painter.fillPath(pathStar,painter.brush())
            else:
                painter.fillPath(pathDiamong,painter.brush())
            painter.translate(2*scaleFactor,0.0)

        painter.restore()

class StarEdit(QWidget):
    """ an edit widget for editing stars """
    # emit editingFinished();

    editingFinished = pyqtSignal()

    def __init__(self,parent=None):
        super(StarEdit,self).__init__(parent)
        self._value = 0
        self.starrating = StarRating(self)

        self.setMouseTracking(True)
        self.setAutoFillBackground(True)

    def setValue(self,value):
        self._value = value

    def value(self):
        return self._value

    def sizeHint(self):
        return self.starrating.sizeHint()

    def paintEvent(self,event):
        painter = QPainter(self)
        self.starrating.paint(painter,self.rect(),self.palette(),StarRating.ModeDisplay)

    def mouseMoveEvent(self,event):

        print(event.x())

    def mouseReleaseEvent(self,event):
        self.editingFinished.emit()

    def starAtPosition(self,x):
        return 0

class StarDelegate(StyledItemDelegate):

    def __init__(self,parent=None):
        super(StarDelegate,self).__init__(parent)

        self.starrating = StarRating(self)

    def sizeHint(self):
        return self.starrating.sizeHint()

    def paint(self,painter,option,index):

        self.starrating.setValue(index.data())
        self.starrating.paint(painter,option.rect,option.palette,StarRating.ModeDisplay)

    def createEditor(self,parent,option,index):
        edit = StarEdit(parent)
        return edit

    def setEditorData(self,editor,index):
        editor.setValue(int(index.data()))

    def setModelData(self,editor,model,index):
        v = editor.value()
        model.setData(index,v)

class TableColumn(QObject):
    def __init__(self, model,key,name,editable=False):
        # parent should be the model
        super(TableColumn, self).__init__(model)

        self._key = key
        self._name = name
        self.__cached_name = None
        self.__cached_name_length = 0
        self._shortName = ""
        self._editable = editable
        self._text_alignment = Qt.AlignLeft|Qt.AlignVCenter

        self._sort_transform = None

        self._display_name = None

    def key(self):
        return self._key

    def name(self):
        return self._name

    def displayName(self,width=0):



        if self._name != self.__cached_name:
            # TODO need to come up with a better way to handle margins
            self.__cached_name_length = QFontMetrics(QApplication.font()).width("   "+self._name+"   d")
            self.__cached_name = self._name
        x = self.__cached_name_length
        if 0 < width < x and self._shortName:
            return self._shortName

        if self._display_name is not None:
            return self._display_name

        return self._name

    def setName(self,name):
        self._name = name

    def setShortName(self,name):
        self._shortName = name

    def isEditable(self):
        return self._editable

    def data(self,tabledata,row):
        _data = tabledata[row]
        if isinstance(_data, dict) and self._key not in _data:
            return None
        return _data[self._key]

    def setData(self,tabledata,row,value):
        tabledata[row][self._key] = value
        return True

    def select(self,rowdata):
        return rowdata[self._key]

    def setDefaultTextAlignment(self, alignment):
        self._text_alignment = alignment

    def textAlignment(self, index):
        return self._text_alignment

    def setSortTransform(self, transform):

        self._sort_transform = transform

    def sortValue(self, tabledata, row):
        if self._sort_transform is not None:
            return self._sort_transform(tabledata, row)
        return self.data(tabledata, row)

    def setDisplayName(self, name):
        self._display_name = name

class TableListColumn(TableColumn):
    """
    a keyless TableColumn for displaying List Data
    """
    def __init__(self, model,name,editable=False):
        # parent should be the model
        super(TableListColumn, self).__init__(model,None,name,editable=editable)

    def data(self,tabledata,row):
        return tabledata[row]

    def select(self,rowdata):
        return rowdata

class TransformTableColumn(TableColumn):
    def __init__(self, model,key,name,fTransform,rTransform=None):
        """
        fTransform : fn(tabledata,row,key) -> QVariant
        rTransform : fn(QVariant) -> QVariant

        forward transform can be used to format the data in the cell
        reverse transform is used to set the data for a cell given
            input from a user

        todo: forward/backward transformation for editng
        """
        editable = rTransform is not None
        super(TransformTableColumn, self).__init__(model,key,name,editable=editable)
        self.fTransform = fTransform
        self.rTransform = rTransform

    def data(self, tabledata, row):
        return self.fTransform(tabledata, row, self._key)

    def setData(self,tabledata,row,value):
        try:
            tabledata[row][self._key] = self.rTransform(tabledata, row, self._key, value)
        except Exception as e:
            print(type(tabledata))
            print(type(tabledata[row]))
            print("error setting transform result")
            print(e)
            return False
        return True

class TransformRule(QObject):
    """docstring for TransformRule

        A transform rule returns a value given the
        result of some function on the data

        name: unique identifier for this rule
        transform : fn(index,col) -> QVariant
            index: QModelIndex
            col  : TableColumn

    """
    def __init__(self, parent, name, transform):
        super(TransformRule, self).__init__(parent)
        self.transform = transform
        self.name = name

    def apply(self,index,col):
        return self.transform(index,col)

class TableModel(QAbstractTableModel):

    def __init__(self, parent):
        super(TableModel, self).__init__(parent)

        self.tabledata = []

        self._columns = []

        self._forgroundRules = []
        self._backgroundRules = []

    def rowCount(self, index):
        return len(self.tabledata)

    def columnCount(self, index):
        return len(self._columns)

    def columnIndex(self,key):
        """ returns the index for a column, using the key as a look up
        not a 1-to-1 mapping,not invertible, can't be implemented"""
        raise NotImplementedError()

    def data(self, index, role):
        i = index.row()
        j = index.column()
        col = self._columns[j]

        if role == Qt.DisplayRole or role == Qt.EditRole:
            return col.data(self.tabledata, i)
        elif role == Qt.TextAlignmentRole:
            return col.textAlignment(index)
        elif role == RowValueIndexRole:
            return i
        elif role == RowValueRole:
            return self.tabledata[i]
        elif role == RowSortValueRole:
            return col.sortValue(self.tabledata, i)
        elif role == Qt.ForegroundRole:
            for rule in self._forgroundRules:
                result = rule.apply(index,col)
                if result is not None:
                    return result
        elif role == Qt.BackgroundRole:
            for rule in self._backgroundRules:
                result = rule.apply(index,col)
                if result is not None:
                    return result
        return None

    def setData(self,index,value,role=Qt.EditRole):
        if role != Qt.EditRole:
            return False

        if index.row() > len(self.tabledata) or index.row() < 0:
            return False

        i = index.row()
        j = index.column()
        c = self._columns[j]
        k = c.key()

        success = self.setModelData(i, c, value)
        if success:
            self.dataChanged.emit(index,index,[role,])
        return success

    def headerData(self,section,orientation,role):

        view = self.parent()

        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self._columns[section].displayName(view.columnWidth(section))
            else:
                return section + 1

    def flags(self,index):
        if not index.isValid():
            return 0

        i = index.row()
        j = index.column()
        c = self._columns[j]
        k = c.key()

        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if c.isEditable():
            flags = flags|Qt.ItemIsEditable

        return flags

    #-----------------------------------------------------------------------
    # Unimplemented
    # these methods could be implemented depending on the model
    # however the default use-case does not generalize to removing data

    def removeColumn(self, idx, parent=QModelIndex()):
        raise TableError("not implemented")
    def removeColumns(self, idx, count, parent=QModelIndex()):
        raise TableError("not implemented")
    def removeRow(self, idx, parent=QModelIndex()):
        raise TableError("not implemented")
    def removeRows(self, idx, count, parent=QModelIndex()):
        raise TableError("not implemented")

    #-----------------------------------------------------------------------
    # helper functions

    def setModelData(self,rowidx,col,value):
        """ reimplement to enable editing data

        rowidx : index of the row to modify (integer)
        col    : column instance (TableColumn)
        """
        # unclear if this should update the model, or if it should return
        # true and have the caller update the model. depends on usecase
        # with some real examples
        return col.setData(self.tabledata,rowidx,value)

    def setNewData(self,tabledata):

        self.beginResetModel()
        self.tabledata = tabledata
        self.endResetModel()

    def forceReset(self):
        """force all cells to be repainted"""
        tl = self.index(0,0)
        br = self.index(self.rowCount(tl)-1,self.columnCount(tl)-1)
        self.dataChanged.emit(tl,br,[Qt.DisplayRole,Qt.ForegroundRole,Qt.BackgroundRole])

    def getData(self):
        """ returns the underlying data source for this model """
        return self.tabledata

    def getColumn(self, idx):
        return self._columns[idx]
    def getColumnIndexByName(self, name):
        for idx, col in enumerate(self._columns):
            if col._name == name:
                return idx
        raise KeyError(name)

    def addColumn(self,key,name,editable=False):
        """ returns the index of the new column """
        col = TableColumn(self,key,name,editable=editable)
        self._columns.append(col)
        return len(self._columns) - 1

    def addTableColumn(self,col):
        """ returns the index of the new column """
        self._columns.append(col)
        return len(self._columns) - 1

    def addTransformColumn(self,key,name,fTransform,rTransform=None):
        """ returns the index of the new column
        fTransform : fn(tabledata, row, key) -> QVariant
        rTransform : fn(QVariant) -> QVariant
        """
        col = TransformTableColumn(self, key, name, fTransform, rTransform)
        self._columns.append(col)
        return len(self._columns) - 1

    def addForegroundRule(self,name,transform):
        """
        name: the name of the rule
                (unused, could be used to remove)
        transform: the transform function
        """
        self._forgroundRules.append(TransformRule(self,name,transform))

    def addBackgroundRule(self,name,transform):
        """
        name: the name of the rule
                (unused, could be used to remove)
        transform: the transform function
        """
        self._backgroundRules.append(TransformRule(self,name,transform))

    def getColumn(self,j):
        return self._columns[j]

    def setColumnShortName(self,idx,name):
        self.getColumn(idx).setShortName(name)

class SortProxyModel(QSortFilterProxyModel):
    def sort(self, column, order = Qt.AscendingOrder):
        """reimplement to disable sorting for specific columns

        DescendingOrder, AscendingOrder
        column: integer column index
        order : the sorting direction

        an example reimplementation would invert sort order for
        specific columns, based on a boolean embedded in TableColumn
        """
        super().sort(column, order)

class AbstractTableView(QTableView):

    MouseDoubleClick = pyqtSignal(QModelIndex)
    MouseReleaseRight = pyqtSignal(QMouseEvent)
    MouseReleaseMiddle = pyqtSignal(QMouseEvent)
    selectionChangedEvent = pyqtSignal()
    rowChanged = pyqtSignal(int)  # index of the row that changed

    def __init__(self, parent):
        super(AbstractTableView, self).__init__(parent)

        self._baseModel = None
        # SelectItems, SelectRows, SelectColumns
        # SingleSelection, ContiguousSelection, ExtendedSelection, MultiSelection, NoSelection
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setAlternatingRowColors(True)
        # TabFocus ClickFocus StrongFocus WheelFocus NoFocus
        #self.setFocusPolicy(Qt.ClickFocus );

        #  ScrollPerItem, ScrollPerPixel
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)

        self.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)

        self.MouseDoubleClick.connect(self.onMouseDoubleClick)
        self.MouseReleaseRight.connect(self.onMouseReleaseRight)
        self.MouseReleaseMiddle.connect(self.onMouseReleaseMiddle)
        self.horizontalHeader().sectionClicked.connect(self.onHeaderClicked)

    def selectionChanged(self, *args):
        super().selectionChanged(*args)
        self.selectionChangedEvent.emit()

    def mouseDoubleClickEvent(self,event):
        index = self.indexAt(event.pos())
        col = self.baseModel().getColumn(index.column())
        if not col.isEditable():
            self.MouseDoubleClick.emit(index)
        else:
            super(AbstractTableView, self).mouseDoubleClickEvent(event)

    def mousePressEvent(self,event):
        #index = self.indexAt(event.pos())
        #print(index.row(),index.column())
        if event.button() != Qt.LeftButton:
            return

        super(AbstractTableView, self).mousePressEvent(event)

    def mouseReleaseEvent(self,event):
        if event.button() == Qt.RightButton:
            self.MouseReleaseRight.emit(event)
            return
        if event.button() == Qt.MiddleButton:
            self.MouseReleaseMiddle.emit(event)
            return
        super(AbstractTableView, self).mouseReleaseEvent(event)

    def keyPressEvent(self,event):
        super(AbstractTableView, self).keyPressEvent(event)

    def keyReleaseEvent(self,event):
        super(AbstractTableView, self).keyReleaseEvent(event)

    #-----------------------------------------------------------------------
    # public slots

    def onMouseDoubleClick(self,index):
        """
        mouse event for double click.
        emitted when the user double clicks on a cell that is not editable.
        """
        print("AbstractTableView:  Double Click event")

    def onMouseReleaseRight(self,event):
        """
        activated when the user right clicks somewhere in the table
        """
        #index = self.indexAt(event.pos())
        #print(index.row(),index.column())
        print("AbstractTableView:  Release Right event")

    def onMouseReleaseMiddle(self,event):
        """
        activated when the user middle clicks somewhere in the table
        """
        #index = self.indexAt(event.pos())
        #print(index.row(),index.column())
        print("AbstractTableView: Release Middle event")

    def onHeaderClicked(self,idx):
        """
        activated when the user clicks a header
        """
        print("AbstractTableView: Header Clicked %d"%idx)

    #-----------------------------------------------------------------------
    # helper functions

    def getState(self):
        """ return a representation of the current state """
        headerState = self.horizontalHeader().saveState()
        return (headerState,)

    def setState(self, state):
        """ restore state given the representation """
        headerState = state[0]
        self.horizontalHeader().restoreState(headerState)

    def setModel(self,model):
        self._baseModel = model # save a reference to the non-proxy model
        super(AbstractTableView,self).setModel(model)
        model.dataChanged.connect(self.onDataChanged)

    def baseModel(self):
        return self._baseModel

    def setNewData(self,data):
        self.baseModel().setNewData(data)

        # todo: revist this, may not always change
        self.selectionChangedEvent.emit()

    def data(self, row_index):
        """ get row data at index, used in conjunction with transforms """
        # note: this uncovers an interesting implementation bug with
        # the layered proxy models. background transforms paint
        # using the base model, which can be confusing...
        return self.baseModel().data(
            self.baseModel().index(row_index, 0), RowValueRole)

    def forceReset(self):
        self.baseModel().forceReset()

    def getData(self):
        return self.baseModel().getData()

    def rowCount(self):
        return self.baseModel().rowCount(None)

    def columnCount(self):
        return self.baseModel().columnCount(None)

    def setAlternatingRowColors(self,bEnable):
        super(AbstractTableView,self).setAlternatingRowColors(bEnable)

    def getSortProxyModel(self):
        """
        returns a new instance of SortProxyModel, used for
        sorting the baseModel()
        """
        model = SortProxyModel(self)
        model.setSourceModel(self.baseModel())
        return model

    def setSortingEnabled(self,bEnabled):
        """ set a proxy model to enable sorting
            Reimplement getSortProxyModel to have more control over
            how sorting is performed
        """
        if bEnabled:
            super(AbstractTableView,self).setModel( self.getSortProxyModel() )
        else:
            super(AbstractTableView, self).setModel(self.baseModel())
        super().setSortingEnabled(bEnabled)

    def setHorizontalHeaderVisible(self,bVisible):
        self.horizontalHeader().setVisible(bVisible)

    def setVerticalHeaderVisible(self,bVisible):
        self.verticalHeader().setVisible(bVisible)

    #def setStretchLastSection(self,bStretch):
    #    self.horizontalHeader().setStretchLastSection(bStretch)


    def setDelegate(self,colidx,delegate):
        if self._baseModel is None:
            raise TableError("No Model Set")
        self.setItemDelegateForColumn(colidx, delegate)

    #--------------------------------------------------------------------------
    # row operations

    def setRowHeight(self,iSize):
        self.verticalHeader().setDefaultSectionSize(iSize)

    #--------------------------------------------------------------------------
    # column operations

    def setColumnsMovable(self,bMove):
        self.horizontalHeader().setSectionsMovable(bMove)

    def setColumnHeaderClickable(self,bClickable):
        self.horizontalHeader().setSectionsClickable(bClickable)

    def setColumnSortIndicatorShown(self,bVisible):
        self.horizontalHeader().setSortIndicatorShown(bVisible)

    def setColumnSortIndicator(self,idx,order=Qt.AscendingOrder):
        """
        idx : tjhe column index
        order: the qt Sort order, one of:
            Qt.AscendingOrder
            Qt.DescendingOrder
        """
        self.horizontalHeader().setSortIndicator(idx,order)

    def setColumnName(self,idx,name):
        self.baseModel().getColumn(idx).setName(name)

    def setColumnHidden(self,idx,bHidden):
        self.horizontalHeader().setSectionHidden(idx,bHidden)

    def scrollToRow(self,row,column=0,hint=QAbstractItemView.PositionAtCenter):
        index=self.model.index(row,column)
        super(AbstractTableView,self).scrollTo(index,hint)

    def resizeColumnToContents(self, index):
        super(AbstractTableView,self).resizeColumnToContents(index)

    def setColumnWidth(self, index, width):
        super(AbstractTableView,self).setColumnWidth(index,width)

    def setLastColumnExpanding(self,bExpand):
        self.horizontalHeader().setStretchLastSection(bExpand)

    #--------------------------------------------------------------------------
    # selection model

    def hasSelection(self):
        model = self.selectionModel()
        return model.hasSelection()

    def getSelectedRows(self):
        """ return indices of selected rows
            valid only if select by rows is enabled
        """
        if self.selectionBehavior() != QAbstractItemView.SelectRows:
            raise TableError("Selection Behavior does not support selecting rows.")
        row_indices = self.selectionModel().selectedRows()
        model = self.model()
        return [model.data(index, RowValueIndexRole) for index in row_indices]

    def getSelectionCount(self):
        return len(self.selectionModel().selectedRows())

    def getSelection(self):

        row_indices = self.selectionModel().selectedRows()

        model = self.model()
        # the column model has a custom role, RowValueRole
        # which is used to return the unmodified row data
        return [model.data(index, RowValueRole) for index in row_indices]

    def setSelectedRows(self,rows):
        """
        rows : list or iterable of integer indices.

        set the given set or rows to be selected.

        the current selection mode must support multi select, or
        non-contiguous selection depending on the contents of rows
        for the requested selection to take place.
        """
        if self.selectionBehavior() != QAbstractItemView.SelectRows:
            raise TableError("Selection Behavior does not support selecting rows.")
        flags = QItemSelectionModel.Select|QItemSelectionModel.Rows
        model = self.selectionModel()
        for row in rows:
            model.select(self.model().index(row,0),flags)
        #self.setSelectionModel(model)

    def getSelectedColumns(self):
        """ return indices of selected columns
            valid only if select by columns is enabled
        """
        if self.selectionBehavior() != QAbstractItemView.SelectColumns:
            raise TableError("Selection Behavior does not support selecting columns.")
        model = self.selectionModel()
        return [i.column() for i in model.selectedColumns()]

    def onDataChanged(self, topLeft, bottomRight, roles):

        row_start = topLeft.row()
        row_end = bottomRight.row()
        col_start = topLeft.column()
        col_end = bottomRight.column()
        print(topLeft.row(), topLeft.column(),
            bottomRight.row(), bottomRight.column(), roles)

        for row in range(row_start, row_end+1):
            self.rowChanged.emit(row)

class TableView(AbstractTableView):
    """

    A TableView displays 2-dimensional data.

    setNewData accepts a list-of-items. items must be indexable.
        e.g. list-of-lists, list-of-tuples, or list-of-dicts
    """
    def __init__(self, parent):
        super(TableView, self).__init__(parent)
        self.setModel(TableModel(self))

class ListView(AbstractTableView):
    """
    a ListView is a TableView with a single column

    this is a convenience class to handle a common case

    setNewData accepts a list of items to display
        e.g. a list-of-strings.
    This differs from a TableView, which would accept 2 dimensional data.
    """
    def __init__(self, parent):
        super(ListView, self).__init__(parent)
        self.setModel(TableModel(self))

        self.setLastColumnExpanding(True)
        self.baseModel().addTableColumn(TableListColumn(self.baseModel(),""))

    def setHeaderText(self,text):
        self.setColumnName(0,text)

class _DemoMainWindow(QMainWindow):
    """docstring for MainWindow"""
    def __init__(self):
        super(_DemoMainWindow, self).__init__()

        img = QImage(48,48,QImage.Format_RGB32)
        img.fill(qRgb(0,0,0))

        # Build a random table of data to display
        data =[]
        for i in range(50):
            data.append([random.randint(1,5),]+[ ''.join([ random.choice(string.ascii_lowercase) for i in range(random.randint(3,6))]) for i in range(3)])

        self.table = TableView(self)
        model = self.table.baseModel()
        model.addColumn(0,"long name",editable=True)
        model.addColumn(1,"two",editable=False)
        model.addColumn(2,"three",editable=True)
        model.addTransformColumn(None,"transform",lambda data,row,key : "test")
        model.addForegroundRule("1",lambda index,col : QColor(255,0,0) if index.row()==1 else None)
        model.addBackgroundRule("2",lambda index,col : QColor(204,204,255) if index.row()==2 else None)

        model.setColumnShortName(0,"sn")
        #d = DualTextDelegate(lambda index: str(index.column()), self)
        d = StarDelegate(self)
        self.table.setDelegate(0, d)
        #d = ComboBoxTextDelegate(self,["1","23","abc","six"])
        #self.table.setDelegate(1,d)
        #self.table.setRowHeight(20);
        #self.table.setRowHeight(20);

        self.table.setColumnsMovable(True)
        self.table.setNewData(data)

        self.list = ListView(self)
        self.list.setHeaderText("Woah")
        self.list.setNewData([0,1,2,3,4,5])

        #self.model = ListModel([0,2,3,4],self)
        #self.table = ListView(self.model,self)
        self.pbGenData = QPushButton(self)
        self.pbGenData.clicked.connect(self.randomData)

        self.centralWidget = QWidget(self)
        self.vbox = QVBoxLayout(self.centralWidget)
        self.vbox.addWidget(self.table)
        self.vbox.addWidget(self.list)
        self.vbox.addWidget(self.pbGenData)
        self.setCentralWidget(self.centralWidget)

    def randomData(self):

        print(self.table.selectedIndexes())
        print(len(self.table.selectedIndexes()))
        model = self.table.selectionModel()
        g = lambda index: (index.row(),index.column())
        print(model.hasSelection())
        print([g(i) for i in model.selectedRows()])

        cols = 5
        rows = 30000
        data = [ list(range(cols)) for i in range(rows) ]
        self.table.baseModel().setNewData(data)

def main():

    app = QApplication(sys.argv)

    window = _DemoMainWindow()
    window.show()

    app.exec_()

if __name__ == '__main__':
    main()