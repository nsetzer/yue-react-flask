
import os,sys
import traceback
import time

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

class ExceptionDialog(QDialog):
    """docstring for ExceptionDialog"""
    def __init__(self, title, message, trace, parent=None, icon_kind=None):
        super(ExceptionDialog, self).__init__(parent)

        self.setWindowTitle(title)

        self.vbox=QVBoxLayout(self)
        self.vbox.setContentsMargins(16,8,16,8)

        self.style = QApplication.style();
        self.grid = QGridLayout()

        i=0
        self.lbl_msg = QLabel(message,self)
        self.lbl_msg.setWordWrap(True);
        self.lbl_msg.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Minimum);
        self.grid.addWidget(self.lbl_msg,i,1,1,4)
        i += 1

        self.txt_trace = QPlainTextEdit(self)
        self.txt_trace.setReadOnly(True);
        self.txt_trace.setPlainText(trace)
        self.grid.addWidget(self.txt_trace,i,1,2,4)
        i += 2

        self.btn_accept = QPushButton("Ok")
        self.btn_accept.clicked.connect(self.accept)
        self.grid.addWidget(self.btn_accept,i,4)
        i+=1

        # ----
        if icon_kind is None:
            icon_kind = QStyle.SP_MessageBoxCritical

        icon = self.style.standardIcon(icon_kind, None, self);
        self.pix_icon = icon.pixmap(64,64)
        self.lbl_icon = QLabel(self)
        self.lbl_icon.setPixmap(self.pix_icon)
        self.grid.addWidget(self.lbl_icon,0,0,i,1)

        self.vbox.addLayout(self.grid)


# global dictionary which counts the number of times a specific
# exception type has been thrown. stop showing a message dialog
# for exceptions that have been thrown multiple times.
gExceptionMessages= dict()
gMessageTimeout = time.time()
def handle_exception(exc_type, exc_value, exc_traceback):

    global gExceptionMessages
    global gMessageTimeout

    # reset the counters if not unhandled exceptions
    # have been caught in a while
    t  = time.time()
    if t - gMessageTimeout > 60:
        gExceptionMessages= dict()
    gMessageTimeout = t

    if exc_type not in gExceptionMessages:
        gExceptionMessages[exc_type] = 0;

    lines = ""
    for line in traceback.format_exception(exc_type,exc_value,exc_traceback):
        print(line)
        lines += line + "\n"

    if gExceptionMessages[exc_type] < 5:
        ExceptionDialog("Unhandled Exception", str(exc_value), lines).exec_()
    gExceptionMessages[exc_type] += 1

    # if we get too many messages (a loop has failed)
    # abort the application after showing one last message
    # this is a serious failure
    if gExceptionMessages[exc_type] > 100:
        ExceptionDialog("Aborting Application", str(exc_value), lines).exec_()
        sys.exit(1)

def installExceptionHook():
    sys.excepthook = handle_exception