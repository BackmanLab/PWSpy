import traceback
from datetime import datetime

from PyQt5 import QtCore
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QGridLayout, QListWidget, QComboBox, QPushButton, \
    QLabel, QListWidgetItem, QDoubleSpinBox

from pwspy.apps.sharedWidgets.extraReflectionManager import ERManager

class MainWindow(QMainWindow):
    def __init__(self, manager: ERManager):
        super().__init__()
        self.explorerWindow = manager.createManagerWindow(self)
        self.setWindowTitle("Extra Reflectance Creator")
        widg = QWidget()
        layout = QGridLayout()
        self.listWidg = QListWidget(self)
        self.selListWidg = QListWidget(self)
        self.binningCombo = QComboBox()
        self.binningCombo.addItems(['Auto', '1x1', '2x2', '3x3'])
        self.compareDatesButton = QPushButton("Compare Dates")
        self.plotButton = QPushButton("Plot Details")
        self.saveButton = QPushButton("Save Checked Dates")
        self.deleteFigsButton = QPushButton("Close Figures")
        self.viewFilesButton = QPushButton("View Files")
        self.viewFilesButton.released.connect(self.viewFiles)
        self.numericalAperture = QDoubleSpinBox()
        self.numericalAperture.setRange(0, 2)
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



    @property
    def binning(self):
        num = self.binningCombo.currentIndex()
        return num if num != 0 else None

    @property
    def checkedSettings(self):
        dateItems = [self.selListWidg.item(i) for i in range(self.selListWidg.count())]
        return [i.text() for i in dateItems if i.checkState()]

    def setEnabled(self, en: bool):
        [i.setEnabled(en) for i in [self.binningCombo, self.saveButton, self.compareDatesButton, self.plotButton]]

    def viewFiles(self):
        self.explorerWindow.show()