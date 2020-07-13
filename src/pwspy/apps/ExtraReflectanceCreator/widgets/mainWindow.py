# Copyright 2018-2020 Nick Anthony, Backman Biophotonics Lab, Northwestern University
#
# This file is part of PWSpy.
#
# PWSpy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PWSpy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PWSpy.  If not, see <https://www.gnu.org/licenses/>.


from PyQt5.QtWidgets import QMainWindow, QWidget, QGridLayout, QListWidget, QComboBox, QPushButton, \
    QLabel, QDoubleSpinBox, QCheckBox

from pwspy.apps.sharedWidgets.extraReflectionManager import ERManager


class MainWindow(QMainWindow):
    """This is the main window of the ERCreator app.
    Args:
        manager (ERmanager): The class which handles organization of the Extra reflectance database locally an online."""
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
        self.parallelCheckBox = QCheckBox("Parallel Process", self)
        self.parallelCheckBox.setToolTip("Uses significantly more ram but may be significantly faster")
        self.compareDatesButton = QPushButton("Compare Dates")
        self.plotButton = QPushButton("Plot Details")
        self.saveButton = QPushButton("Save Checked Dates")
        self.deleteFigsButton = QPushButton("Close Figures")
        self.viewFilesButton = QPushButton("View Files")
        self.viewFilesButton.released.connect(self.viewFiles)
        self.numericalAperture = QDoubleSpinBox()
        self.numericalAperture.setRange(0, 2)
        self.numericalAperture.setSingleStep(0.01)
        self.numericalAperture.setValue(0.52)
        row = 0
        layout.addWidget(self.listWidg, row, 0, 4, 4)
        layout.addWidget(self.selListWidg, row, 4, 4, 4)
        row += 4
        layout.addWidget(self.compareDatesButton, row, 0, 1, 1)
        layout.addWidget(self.plotButton, row, 1, 1, 1)
        layout.addWidget(self.deleteFigsButton, row, 2, 1, 1)
        layout.addWidget(QLabel("Binning"), row, 4, 1, 1)
        layout.addWidget(self.binningCombo, row, 5, 1, 1)
        layout.addWidget(self.parallelCheckBox, row, 6, 1, 1)
        row += 1
        layout.addWidget(self.saveButton, row, 0, 1, 1)
        layout.addWidget(self.viewFilesButton, row, 1, 1, 1)
        layout.addWidget(QLabel("NA"), row, 4, 1, 1)
        layout.addWidget(self.numericalAperture, row, 5, 1, 1)
        widg.setLayout(layout)
        self.setCentralWidget(widg)
        self.buttons = [self.compareDatesButton, self.plotButton, self.saveButton]
        self.show()

    @property
    def binning(self) -> int:
        num = self.binningCombo.currentIndex()
        return num if num != 0 else None

    @property
    def parallelProcessing(self) -> bool:
        return self.parallelCheckBox.isChecked()

    @property
    def checkedSettings(self):
        dateItems = [self.selListWidg.item(i) for i in range(self.selListWidg.count())]
        return [i.text() for i in dateItems if i.checkState()]

    def setEnabled(self, en: bool):
        [i.setEnabled(en) for i in [self.binningCombo, self.saveButton, self.compareDatesButton, self.plotButton]]

    def viewFiles(self):
        self.explorerWindow.show()