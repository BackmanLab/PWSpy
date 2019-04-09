import os

from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout, QLineEdit, QPushButton, QFileDialog, \
    QDialog, QCheckBox, QVBoxLayout, QComboBox, QLabel
from PyQt5 import (QtCore, QtGui)
from pwspy.apps import resources
from pwspy.apps.ExtraReflectanceCreator.ERWorkFlow import ERWorkFlow
from typing import List
import matplotlib.pyplot as plt

class ParamsDialog(QDialog):
    def __init__(self, parent, settings: List[str]):
        super().__init__(parent)
        self.setModal(True)
        layout = QVBoxLayout()
        self.checks = [QCheckBox(sett) for sett in settings]
        self.binningCombo = QComboBox()
        self.binningCombo.addItems(['Auto', '1x1', '2x2', '3x3'])
        self.acceptButton = QPushButton("Accept")
        self.acceptButton.released.connect(self.accept)

        layout.addWidget(QLabel("Settings"))
        for check in self.checks:
            layout.addWidget(check)
        layout.addWidget(QLabel("Binning"))
        layout.addWidget(self.binningCombo)
        layout.addWidget(self.acceptButton)
        self.setLayout(layout)
        self.show()

    def getBinning(self) -> int:
        num = self.binningCombo.currentIndex()
        ret = num if num != 0 else None
        return ret

    def getSettings(self) -> List[str]:
        return [check.text() for check in self.checks if check.checkState() != 0]

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
        self.compareDatesButton.released.connect(self.workflow.compareDates)
        self.plotButton = QPushButton("Plot Corrections")
        self.plotButton.released.connect(lambda: self.workflow.plot(False))
        self.saveButton = QPushButton("Save")
        self.plotButton.released.connect(self.workflow.save)
        row = 0
        layout.addWidget(self.directoryEdit, row, 0, 1, 4)
        layout.addWidget(self.directoryBrowseButton, row, 4, 1, 1)
        row += 1
        layout.addWidget(self.compareDatesButton, row, 0, 1, 1)
        layout.addWidget(self.plotButton, row, 1, 1, 1)
        layout.addWidget(self.saveButton, row, 2, 1, 1)
        widg.setLayout(layout)
        self.setCentralWidget(widg)
        self.buttons = [self.compareDatesButton, self.plotButton, self.saveButton]
        for b in self.buttons:
            b.setEnabled(False)
        self.show()

    def browseFile(self):
        _ = QFileDialog.getExistingDirectory(self, 'Working Directory', self.directory)
        for b in self.buttons:
            b.setEnabled(False)
        if _ != '':
            self.directory = _
            self.directoryEdit.setText(self.directory)
            settings = self.workflow.getDirectorySettings(self.directory)
            a = ParamsDialog(self, settings)
            a.exec()
            if a.result() == QDialog.Accepted:
                self.workflow.loadDirectory(self.directory, a.getSettings(), a.getBinning())
                for b in self.buttons:
                    b.setEnabled(True)


class ERApp(QApplication):
    def __init__(self, args):
        super().__init__(args)
        plt.interactive(True)
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