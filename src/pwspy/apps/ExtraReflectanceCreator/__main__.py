import os
import traceback

from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout, QLineEdit, QPushButton, QFileDialog, \
    QDialog, QCheckBox, QVBoxLayout, QComboBox, QLabel, QListWidget, QListWidgetItem
from PyQt5 import (QtCore, QtGui)
from pwspy.apps import resources
from pwspy.apps.ExtraReflectanceCreator.ERWorkFlow import ERWorkFlow
from typing import Dict, List, Any
import matplotlib.pyplot as plt
from glob import glob
import pandas as pd


class MainWindow(QMainWindow):
    def __init__(self, workFlow: ERWorkFlow):
        QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
        self.workflow = workFlow
        super().__init__()
        self.setWindowTitle("Extra Reflectance Creator")
        widg = QWidget()
        layout = QGridLayout()
        self.listWidg = QListWidget(self)
        for k, v in self.workflow.fileStruct.items():
            self.listWidg.addItem(k)
        self.listWidg.currentItemChanged.connect(self.selectionChanged)
        self.selListWidg = QListWidget(self)
        self.selListWidg.itemChanged.connect(self.workflow.invalidateCubes)
        self.binningCombo = QComboBox()
        self.binningCombo.addItems(['Auto', '1x1', '2x2', '3x3'])
        self.binningCombo.currentIndexChanged.connect(self.workflow.invalidateCubes)
        self.compareDatesButton = QPushButton("Compare Dates")
        self.compareDatesButton.released.connect(self.compareDates)
        self.plotButton = QPushButton("Plot Details")
        self.plotButton.released.connect(self.plot)
        self.saveButton = QPushButton("Save Checked Dates")
        self.saveButton.released.connect(self.save)
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
        self.show()

    def selectionChanged(self, item: QListWidgetItem, oldItem: QListWidgetItem):
        self.workflow.selectionChanged(item.text())
        self.selListWidg.clear()
        for sett in set(self.workflow.df['setting']):
            _ = QListWidgetItem(sett)
            _.setFlags(_.flags() | QtCore.Qt.ItemIsUserCheckable)
            _.setCheckState(QtCore.Qt.Unchecked)
            self.selListWidg.addItem(_)

    @property
    def binning(self):
        num = self.binningCombo.currentIndex()
        return num if num != 0 else None

    @property
    def checkedSettings(self):
        dateItems = [self.selListWidg.item(i) for i in range(self.selListWidg.count())]
        return [i.text() for i in dateItems if i.checkState()]

    def loadIfNeeded(self):
        if self.workflow.cubes is None:
            self.workflow.loadCubes(self.checkedSettings, self.binning)

    def plot(self):
        try:
            self.setEnabled(False)
            self.loadIfNeeded()
            self.workflow.plot()
        except:
            traceback.print_exc()
        finally:
            self.setEnabled(True)

    def compareDates(self):
        try:
            self.setEnabled(False)
            self.loadIfNeeded()
            self.animations = self.workflow.compareDates()
        except:
            traceback.print_exc()
        finally:
            self.setEnabled(True)

    def save(self):
        try:
            self.setEnabled(False)
            self.loadIfNeeded()
            self.workflow.save(saveDir, saveName)
        except:
            traceback.print_exc()
        finally:
            self.setEnabled(True)

    # def setEnabled(self, en: bool):
    #     [i.setEnabled(en) for i in [self.binningCombo, self.saveButton, self.compareDatesButton, self.plotButton]]

class ERApp(QApplication):
    def __init__(self, args):
        super().__init__(args)
        plt.interactive(True)
        wDir = QFileDialog.getExistingDirectory(caption='Select Working Directory')
        self.workflow = ERWorkFlow()
        self.workflow.generateFileStruct(wDir)
        self.window = MainWindow(self.workflow)


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