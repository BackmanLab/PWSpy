import os

from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout, QLineEdit, QPushButton, QFileDialog
from PyQt5 import (QtCore, QtGui)
from pwspy.apps import resources
from pwspy.apps.ExtraReflectanceCreator.ERWorkFlow import ERWorkFlow


class MainWindow(QMainWindow):
    def __init__(self):
        QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
        self.workflow = ERWorkFlow()
        super().__init__()
        self.setWindowTitle("Extra Reflectance Creator")
        widg = QWidget()
        layout = QGridLayout()
        self.directory = os.path.expanduser('~')
        self.directoryEdit = QLineEdit(self.directory, self)
        self.directoryBrowseButton = QPushButton(QtGui.QIcon(os.path.join(resources, 'folder.png')), '')
        self.directoryBrowseButton.released.connect(self.browseFile)
        self.compareDatesButton = QPushButton("Compare Dates")
        self.plotButton = QPushButton("Plot Corrections")
        self.plotButton.released.connect(lambda: self.workflow.plot(False))
        layout.addWidget(self.directoryEdit, 0, 0, 1, 4)
        layout.addWidget(self.directoryBrowseButton, 0, 4, 1, 1)
        layout.addWidget(self.compareDatesButton, 1, 0, 1, 1)
        layout.addWidget(self.plotButton, 1, 1, 1, 1)
        widg.setLayout(layout)
        self.setCentralWidget(widg)
        self.buttons = [self.compareDatesButton, self.plotButton]
        for b in self.buttons:
            b.setEnabled(False)
        self.show()

    def browseFile(self):
        _ = QFileDialog.getExistingDirectory(self, 'Working Directory', self.directory)
        if _ != '':
            self.directory = _
            self.directoryEdit.setText(self.directory)
            self.workflow.loadDirectory(self.directory)
            for b in self.buttons:
                b.setEnabled(True)
        else:
            for b in self.buttons:
                b.setEnabled(False)

class ERApp(QApplication):
    def __init__(self, args):
        super().__init__(args)
        self.window = MainWindow()


def isIpython():
    try:
        return __IPYTHON__
    except:
        return False

if __name__ == '__main__':
    import sys

    # This prevents errors from happening silently.
    sys.excepthook_backup = sys.excepthook
    def exception_hook(exctype, value, traceback):
        print(exctype, value, traceback)
        sys.excepthook_backup(exctype, value, traceback)
        sys.exit(1)
    sys.excepthook = exception_hook

    if isIpython():
        app = ERApp(sys.argv)
    else:
        print("Not Ipython")
        app = ERApp(sys.argv)
        sys.exit(app.exec_())