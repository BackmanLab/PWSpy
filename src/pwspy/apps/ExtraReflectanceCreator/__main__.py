import os

from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout, QLineEdit, QPushButton, QFileDialog, \
    QDialog, QCheckBox, QVBoxLayout, QComboBox, QLabel, QListWidget, QListWidgetItem
from PyQt5 import (QtCore, QtGui)
from pwspy.apps import resources
from pwspy.apps.ExtraReflectanceCreator.ERWorkFlow import ERWorkFlow
from typing import Dict, List
import matplotlib.pyplot as plt
from glob import glob
import pandas as pd


class MainWindow(QMainWindow):
    def __init__(self, fileStruct: Dict[str, pd.DataFrame]):
        QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
        self.fileStruct = fileStruct
        self.cubes = None
        self.workflow = ERWorkFlow()
        super().__init__()
        self.setWindowTitle("Extra Reflectance Creator")
        widg = QWidget()
        layout = QGridLayout()
        self.listWidg = QListWidget(self)
        for k, v in fileStruct.items():
            self.listWidg.addItem(k)
        self.listWidg.currentItemChanged.connect(self.selectionChanged)
        self.selListWidg = QListWidget(self)
        self.selListWidg.itemChanged.connect(self.invalidateCubes)
        self.binningCombo = QComboBox()
        self.binningCombo.addItems(['Auto', '1x1', '2x2', '3x3'])
        self.compareDatesButton = QPushButton("Compare Dates")
        self.compareDatesButton.released.connect(self.compareDates)
        self.plotButton = QPushButton("Plot Details")
        self.plotButton.released.connect(self.plot)
        self.saveButton = QPushButton("Save Selected Date")
        self.plotButton.released.connect(self.workflow.save)
        row = 0
        layout.addWidget(self.listWidg, row, 0, 4, 4)
        layout.addWidget(self.selListWidg, row, 4, 4, 4)
        row += 4
        layout.addWidget(self.compareDatesButton, row, 0, 1, 1)
        layout.addWidget(self.plotButton, row, 1, 1, 1)
        layout.addWidget(QLabel("Binning"), row, 4, 1, 1)
        layout.addWidget(self.binningCombo, row, 5, 1, 1)
        layout.addWidget(self.saveButton, row, 6, 1, 1)
        widg.setLayout(layout)
        self.setCentralWidget(widg)
        self.buttons = [self.compareDatesButton, self.plotButton, self.saveButton]
        for b in self.buttons:
            b.setEnabled(False)
        self.show()

    def selectionChanged(self, item: QListWidgetItem, oldItem: QListWidgetItem):
        self.df = self.fileStruct[item.text()]
        self.invalidateCubes()
        self.selListWidg.clear()
        for sett in set(self.df['setting']):
            _ = QListWidgetItem(sett)
            _.setFlags(_.flags() | QtCore.Qt.ItemIsUserCheckable)
            _.setCheckState(QtCore.Qt.Unchecked)
            self.selListWidg.addItem(_)

    def invalidateCubes(self):
        self.cubes = None

    def plot(self):
        if self.cubes is None:
            dateItems = [self.selListWidg.item(i) for i in range(self.selListWidg.count())]
            checkedSettings = [i.text() for i in dateItems if i.checkState()]
            self.cubes = self.workflow.loadCubes(self.df, checkedSettings)
        self.workflow.plot(self.cubes)

    def compareDates(self):
        if self.cubes is None:
            dateItems = [self.selListWidg.item(i) for i in range(self.selListWidg.count())]
            checkedSettings = [i.text() for i in dateItems if i.checkState()]
            self.cubes = self.workflow.loadCubes(self.df, checkedSettings)
        self.workflow.compareDates(self.cubes)

    def save(self):
        cubes = self.workflow.loadCubes(self.df, [self.selListWidg.selectedItems()[0].text()])
        self.workflow.save(cubes)

    def getBinning(self) -> int:
        num = self.binningCombo.currentIndex()
        ret = num if num != 0 else None
        return ret

class ERApp(QApplication):
    def __init__(self, args):
        super().__init__(args)
        plt.interactive(True)
        wDir = QFileDialog.getExistingDirectory(caption='Select Working Directory')
        fileStruct = self.validateWorkingDir(wDir)
        self.window = MainWindow(fileStruct)

    def validateWorkingDir(self, workingDir: str) -> Dict[str, pd.DataFrame]:
        folders = [i for i in glob(os.path.join(workingDir, '*')) if os.path.isdir(i)]
        settings = [os.path.split(i)[-1] for i in folders]
        fileStruct = {}
        for f, s in zip(folders, settings):
            fileStruct[s] = ERWorkFlow.scanDirectory(f)
        return fileStruct

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