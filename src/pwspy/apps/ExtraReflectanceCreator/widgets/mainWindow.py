import traceback
from datetime import datetime

from PyQt5 import QtCore
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QGridLayout, QListWidget, QComboBox, QPushButton, \
    QLabel, QListWidgetItem

from pwspy.apps.ExtraReflectanceCreator.ERWorkFlow import ERWorkFlow
from pwspy.apps.sharedWidgets.extraReflectionManager import ERManager
from pwspy.moduleConsts import dateTimeFormat


class MainWindow(QMainWindow):
    def __init__(self, workFlow: ERWorkFlow, manager: ERManager):
        QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
        super().__init__()
        self.workflow = workFlow
        self.explorerWindow = manager.createManagerWindow(self)
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
        self.compareDatesButton.released.connect(self._cb(self.workflow.compareDates))
        self.plotButton = QPushButton("Plot Details")
        self.plotButton.released.connect(self._cb(self.workflow.plot))
        self.saveButton = QPushButton("Save Checked Dates")
        self.saveButton.released.connect(self._cb(self.workflow.save))
        self.deleteFigsButton = QPushButton("Delete Figs")
        self.deleteFigsButton.released.connect(self._cb(self.workflow.deleteFigures))
        self.viewFilesButton = QPushButton("View Files")
        self.viewFilesButton.released.connect(self.viewFiles)
        row = 0
        layout.addWidget(self.listWidg, row, 0, 4, 4)
        layout.addWidget(self.selListWidg, row, 4, 4, 4)
        row += 4
        layout.addWidget(self.compareDatesButton, row, 0, 1, 1)
        layout.addWidget(self.plotButton, row, 1, 1, 1)
        layout.addWidget(self.deleteFigsButton, row, 2, 1, 1)
        layout.addWidget(QLabel("Binning"), row, 4, 1, 1)
        layout.addWidget(self.binningCombo, row, 5, 1, 1)
        layout.addWidget(self.saveButton, row, 6, 1, 1)
        row += 1
        layout.addWidget(self.viewFilesButton, row, 0, 1, 1)
        widg.setLayout(layout)
        self.setCentralWidget(widg)
        self.buttons = [self.compareDatesButton, self.plotButton, self.saveButton]
        self.show()

    def selectionChanged(self, item: QListWidgetItem, oldItem: QListWidgetItem):
        self.workflow.directoryChanged(item.text())
        self.selListWidg.clear()
        settings = set(self.workflow.df['setting'])
        _, settings = zip(*sorted(zip([datetime.strptime(sett, "%m_%d_%Y") for sett in settings], settings)))
        for sett in settings:
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

    def _cb(self, func):
        """Return a wrapped function with extra gui stuff."""
        def newfunc():
            """Toggle button enabled state. load new data if selection has changed. run the callback."""
            try:
                self.setEnabled(False)
                self.loadIfNeeded()
                func()
            except:
                traceback.print_exc()
            finally:
                self.setEnabled(True)
        return newfunc

    def setEnabled(self, en: bool):
        [i.setEnabled(en) for i in [self.binningCombo, self.saveButton, self.compareDatesButton, self.plotButton]]

    def viewFiles(self):
        self.explorerWindow.show()