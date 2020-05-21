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

from PyQt5.QtWidgets import QDialog, QWidget, QTextEdit, QGridLayout, QLabel, QPushButton


class IndexInfoForm(QDialog):
    """This dialog is used to collect a description about the circumstances surrounding the collection of data for an Extra Reflectance calibration.
    This description is ultimately saved to an index which is acts as a sort of database for all of the calibrations."""
    def __init__(self, name, idTag, parent: QWidget = None):
        super().__init__(parent=parent)
        self.description = None
        self.setModal(False)
        self.setWindowTitle(name)
        self.descriptionEdit = QTextEdit()
        self.okButton = QPushButton('OK!')
        self.okButton.released.connect(self.accept)
        layout = QGridLayout()
        layout.addWidget(QLabel("Description:", parent=self), 0, 0, 1, 1)
        layout.addWidget(self.descriptionEdit, 1, 0, 4, 4)
        layout.addWidget(QLabel(f"Name: {name}", self), 5, 0, 1, 1)
        layout.addWidget(QLabel(f"idTag: {idTag}", self), 5, 1, 1, 1)
        layout.addWidget(self.okButton, 5, 3, 1, 1)
        self.setLayout(layout)

    def accept(self) -> None:
        self.description = self.descriptionEdit.toPlainText()
        super().accept()
